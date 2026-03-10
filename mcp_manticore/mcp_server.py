import atexit
import concurrent.futures
import json
import logging
import re
from typing import Any

import httpx
import manticoresearch
from dotenv import load_dotenv
from fastmcp import FastMCP
from fastmcp.exceptions import ToolError
from fastmcp.prompts import Prompt
from fastmcp.server.auth.providers.jwt import StaticTokenVerifier
from fastmcp.server.dependencies import get_context
from manticoresearch.api import utils_api
from starlette.requests import Request
from starlette.responses import PlainTextResponse

from mcp_manticore.docs_fetcher import (
    fetch_documentation,
    format_doc_list,
    list_documentation_files,
)
from mcp_manticore.manticore_prompt import MANTICORE_PROMPT
from mcp_manticore.mcp_env import TransportType, get_config, get_mcp_config

MCP_SERVER_NAME = "mcp-manticore"
CLIENT_CONFIG_OVERRIDES_KEY = "manticore_client_config_overrides"

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(MCP_SERVER_NAME)

QUERY_EXECUTOR = concurrent.futures.ThreadPoolExecutor(max_workers=10)
atexit.register(lambda: QUERY_EXECUTOR.shutdown(wait=True))

load_dotenv()

# Configure authentication for HTTP/SSE transports
auth_provider = None
mcp_config = get_mcp_config()
http_transports = [TransportType.HTTP.value, TransportType.SSE.value]

if mcp_config.server_transport in http_transports:
    if mcp_config.auth_disabled:
        logger.warning("WARNING: MCP SERVER AUTHENTICATION IS DISABLED")
        logger.warning("Only use this for local development/testing.")
        logger.warning("DO NOT expose to networks.")
    elif mcp_config.auth_token:
        auth_provider = StaticTokenVerifier(
            tokens={mcp_config.auth_token: {"client_id": "mcp-client", "scopes": []}},
            required_scopes=[],
        )
        logger.info("Authentication enabled for HTTP/SSE transport")
    else:
        # No token configured and auth not disabled
        raise ValueError(
            "Authentication token required for HTTP/SSE transports. "
            "Set MANTICORE_MCP_AUTH_TOKEN environment variable or set "
            "MANTICORE_MCP_AUTH_DISABLED=true (for development only)."
        )

mcp = FastMCP(name=MCP_SERVER_NAME, auth=auth_provider)


@mcp.custom_route("/health", methods=["GET"])
async def health_check(request: Request) -> PlainTextResponse:
    """Health check endpoint for monitoring server status.

    Returns OK if the server is running and can connect to Manticore Search.
    """
    if auth_provider is not None:
        auth_header = request.headers.get("Authorization")
        if not auth_header or not auth_header.startswith("Bearer "):
            return PlainTextResponse("Unauthorized", status_code=401)

        token = auth_header[7:]
        access_token = await auth_provider.verify_token(token)
        if access_token is None:
            return PlainTextResponse("Unauthorized", status_code=401)

    try:
        # Try to create a client connection to verify Manticore connectivity
        client = create_manticore_client()
        # Execute a simple query to verify connection
        client.utils.sql("SHOW TABLES")
        return PlainTextResponse("OK - Connected to Manticore Search")
    except Exception as e:
        # Return 503 Service Unavailable if we can't connect to Manticore
        return PlainTextResponse(
            f"ERROR - Cannot connect to Manticore Search: {str(e)}", status_code=503
        )


def create_manticore_client():
    """Create and return a Manticore Search client instance.

    Returns:
        Manticore Search UtilsApi client configured with connection settings
    """
    config = get_config()
    client_config = config.get_client_config()

    # Apply session-specific config overrides if available
    try:
        ctx = get_context()
        session_config_overrides = ctx.get_state(CLIENT_CONFIG_OVERRIDES_KEY)
        if session_config_overrides and not isinstance(session_config_overrides, dict):
            logger.warning(
                f"{CLIENT_CONFIG_OVERRIDES_KEY} must be a dict, "
                f"got {type(session_config_overrides).__name__}. Ignoring."
            )
        elif session_config_overrides:
            logger.debug(
                "Applying session-specific Manticore client config "
                f"overrides: {list(session_config_overrides.keys())}"
            )
            client_config.update(session_config_overrides)
    except RuntimeError:
        # If we're outside a request context, just proceed with the default config
        pass

    logger.info(
        f"Creating Manticore Search client connection to "
        f"{client_config['host']}:{client_config['port']}"
    )

    try:
        # Create configuration for manticoresearch client
        configuration = manticoresearch.Configuration(
            host=f"http://{client_config['host']}:{client_config['port']}"
        )

        # Add authentication if provided
        if client_config.get("username") and client_config.get("password"):
            configuration.username = client_config["username"]
            configuration.password = client_config["password"]

        # Create API client
        api_client = manticoresearch.ApiClient(configuration)
        utils_api_instance = utils_api.UtilsApi(api_client)

        logger.info("Successfully connected to Manticore Search")
        return utils_api_instance
    except Exception as e:
        logger.error(f"Failed to connect to Manticore Search: {str(e)}")
        raise


def _validate_query_access(query: str):
    """Validate query for write and destructive operations based on configuration.

    Raises:
        ToolError: If write access is disabled and write operations are attempted,
            or if MANTICORE_ALLOW_DROP is not set for DROP/TRUNCATE operations.

    This implements a two-level safety check:
    1. If MANTICORE_ALLOW_WRITE_ACCESS=false (default), block all write operations
    2. If MANTICORE_ALLOW_WRITE_ACCESS=true, still require MANTICORE_ALLOW_DROP=true
       for DROP/TRUNCATE operations
    """
    config = get_config()

    # Pattern matching for write operations
    # Manticore supports: INSERT, REPLACE, UPDATE, DELETE
    write_pattern = r"\b(INSERT\s+INTO|REPLACE\s+INTO|UPDATE|DELETE\s+FROM?)\b"
    is_write = re.search(write_pattern, query, re.IGNORECASE)

    # Pattern matching for destructive operations
    # Manticore supports: DROP TABLE, DROP INDEX, TRUNCATE TABLE
    destructive_pattern = r"\b(DROP\s+(TABLE|INDEX)|TRUNCATE\s+TABLE?)\b"
    is_destructive = re.search(destructive_pattern, query, re.IGNORECASE)

    # If no write operations, allow it (read-only)
    if not is_write and not is_destructive:
        return

    # Block all write operations if write access is disabled
    if not config.allow_write_access:
        raise ToolError(
            "Write operations (INSERT, REPLACE, UPDATE, DELETE, DROP, TRUNCATE) require "
            "MANTICORE_ALLOW_WRITE_ACCESS=true. "
            "This is a safety feature to prevent accidental data modification."
        )

    # Writes are enabled, but DROP/TRUNCATE require explicit permission
    if is_destructive and not config.allow_drop:
        raise ToolError(
            "Destructive operations (DROP TABLE, DROP INDEX, TRUNCATE) are not allowed. "
            "Set MANTICORE_ALLOW_DROP=true to enable these operations. "
            "This is a safety feature to prevent accidental data deletion."
        )


def execute_query(query: str):
    """Execute a SQL query against Manticore Search.

    Args:
        query: The SQL query to execute

    Returns:
        dict: Query results with columns and rows
    """
    client = create_manticore_client()
    try:
        # Validate query for destructive operations
        _validate_query_access(query)

        # Execute the SQL query using the utils API
        # The sql() method returns SqlResponse which can be:
        # - List[Dict[str, Any]] for queries like SHOW TABLES
        # - SqlObjResponse for SELECT queries with hits structure
        result = client.sql(query)

        # Handle SqlResponse - it has an actual_instance attribute
        if hasattr(result, "actual_instance"):
            actual = result.actual_instance
        else:
            actual = result

        # Parse the result based on type
        if isinstance(actual, list):
            # List of dictionaries (e.g., SHOW TABLES result)
            if len(actual) > 0 and isinstance(actual[0], dict):
                # Each row is a dictionary
                column_names = list(actual[0].keys())
                rows = [list(row.values()) for row in actual]
                return {"columns": column_names, "rows": rows, "total": len(rows)}
            return {"columns": [], "rows": [], "total": 0}

        elif hasattr(actual, "hits"):
            # SqlObjResponse with hits structure (SELECT queries)
            hits = actual.hits
            if isinstance(hits, dict):
                hits_list = hits.get("hits", [])
                total = hits.get("total", 0)

                if hits_list and len(hits_list) > 0:
                    # Extract column names from the first hit's _source
                    first_hit = hits_list[0]
                    if "_source" in first_hit:
                        column_names = list(first_hit["_source"].keys())
                        rows = [list(hit.get("_source", {}).values()) for hit in hits_list]
                        return {"columns": column_names, "rows": rows, "total": total}

            return {"columns": [], "rows": [], "total": 0}

        return {"columns": [], "rows": [], "total": 0}
    except ToolError:
        raise
    except Exception as err:
        logger.error(f"Error executing query: {err}")
        raise ToolError(f"Query execution failed: {str(err)}") from err


@mcp.tool()
def run_query(query: str) -> dict[str, Any]:
    """Execute a SQL query against Manticore Search.

    Queries run in read-only mode by default. Set MANTICORE_ALLOW_WRITE_ACCESS=true
    to allow DDL and DML statements when your Manticore server permits them.

    Args:
        query: The SQL query to execute (e.g., "SELECT * FROM my_index LIMIT 10")

    Returns:
        A dictionary containing:
        - columns: List of column names
        - rows: List of row values
        - total: Total number of results
    """
    logger.info(f"Executing query: {query}")
    try:
        future = QUERY_EXECUTOR.submit(execute_query, query)
        try:
            timeout_secs = get_config().query_timeout
            result = future.result(timeout=timeout_secs)
            return result
        except concurrent.futures.TimeoutError:
            logger.warning(f"Query timed out after {timeout_secs} seconds: {query}")
            future.cancel()
            raise ToolError(f"Query timed out after {timeout_secs} seconds") from None
    except ToolError:
        raise
    except Exception as e:
        logger.error(f"Unexpected error in run_query: {str(e)}")
        raise RuntimeError(f"Unexpected error during query execution: {str(e)}") from e


@mcp.tool()
def list_tables() -> str:
    """List available tables/indexes in Manticore Search.

    Returns:
        JSON string containing list of table names and their types
    """
    logger.info("Listing all tables")
    client = create_manticore_client()

    try:
        result = client.sql("SHOW TABLES")

        # Handle SqlResponse
        if hasattr(result, "actual_instance"):
            actual = result.actual_instance
        else:
            actual = result

        # Parse the result
        if isinstance(actual, list):
            # SHOW TABLES returns a list of dictionaries
            return json.dumps(actual, indent=2)

        return json.dumps([])
    except Exception as e:
        logger.error(f"Error listing tables: {str(e)}")
        raise ToolError(f"Failed to list tables: {str(e)}") from e


@mcp.tool()
def describe_table(table_name: str) -> dict[str, Any]:
    """Get the schema of a specific table/index in Manticore Search.

    Args:
        table_name: The name of the table/index to describe

    Returns:
        A dictionary containing column information including:
        - columns: List of column names and types
    """
    logger.info(f"Describing table: {table_name}")
    client = create_manticore_client()

    try:
        result = client.sql(f"DESCRIBE {table_name}")

        # Handle SqlResponse
        if hasattr(result, "actual_instance"):
            actual = result.actual_instance
        else:
            actual = result

        # Parse the result
        if isinstance(actual, list):
            # DESCRIBE returns a list of dictionaries with column info
            return {"columns": actual}

        return {"columns": []}
    except Exception as e:
        logger.error(f"Error describing table {table_name}: {str(e)}")
        raise ToolError(f"Failed to describe table {table_name}: {str(e)}") from e


@mcp.tool()
async def list_documentation(search: str | None = None, use_regex: bool = False) -> str:
    """List all available documentation files from Manticore Search manual.

    Fetches file list from GitHub API (cached after first call).
    Use this tool to discover available documentation before using get_documentation.

    Args:
        search: Optional search term to filter files (e.g., "knn", "full-text", "cluster")
        use_regex: If True, treat search as regex pattern (default: False)
            - When False: simple substring match (case-insensitive)
            - When True: regex pattern match (case-insensitive)

    Returns:
        List of available documentation files, grouped by category

    Examples:
        # List all documentation
        list_documentation()

        # Simple substring search (default)
        list_documentation(search="knn")

        # Regex search - find KNN or vector docs
        list_documentation(search="knn|vector", use_regex=True)

        # Regex search - find all files in Searching directory
        list_documentation(search="^Searching/", use_regex=True)

        # Regex search - find files ending with specific pattern
        list_documentation(search="index.*\\.md$", use_regex=True)
    """
    logger.info(f"Listing documentation files, search={search}, use_regex={use_regex}")

    try:
        files = await list_documentation_files()

        if search:
            if use_regex:
                # Filter by regex pattern
                try:
                    pattern = re.compile(search, re.IGNORECASE)
                    files = [f for f in files if pattern.search(f)]
                except re.error as e:
                    raise ToolError(
                        f"Invalid regex pattern '{search}': {str(e)}. "
                        "Use simple search or fix the regex pattern."
                    ) from e
            else:
                # Filter by substring (case-insensitive)
                search_lower = search.lower()
                files = [f for f in files if search_lower in f.lower()]

        return format_doc_list(files)
    except httpx.HTTPError as e:
        logger.error(f"Failed to list documentation: {str(e)}")
        raise ToolError(f"Failed to fetch documentation list from GitHub: {str(e)}") from e


@mcp.tool()
async def get_documentation(
    file_path: str, content: str | None = None, before: int = 0, after: int = 0
) -> str:
    """Fetch documentation from Manticore Search manual.

    Use list_documentation() first to discover available files.

    Args:
        file_path: Path to documentation file (e.g., "Searching/KNN.md")
        content: Optional search term to filter content (returns only matching sections)
        before: Number of lines before match to include (default: 0)
        after: Number of lines after match to include (default: 0)

    Returns:
        Documentation content as markdown text

    Examples:
        get_documentation(
            "Searching/Full_text_matching/Operators.md",
            content="MATCH", before=2, after=2
        )

        get_documentation("Creating_a_table/Data_types.md")
    """
    logger.info(
        f"Fetching documentation: {file_path}, content={content}, before={before}, after={after}"
    )

    try:
        result = await fetch_documentation(file_path, content, before, after)
        return result
    except ValueError as e:
        logger.error(f"Invalid documentation path: {file_path}")
        raise ToolError(str(e)) from e
    except httpx.HTTPError as e:
        logger.error(f"Failed to fetch documentation: {str(e)}")
        raise ToolError(f"Failed to fetch documentation from GitHub: {str(e)}") from e


def manticore_initial_prompt() -> str:
    """Prompt for Manticore Search operations."""
    return MANTICORE_PROMPT


# Register the prompt
manticore_prompt = Prompt.from_function(
    manticore_initial_prompt,
    name="manticore_initial_prompt",
    description="Prompt for Manticore Search operations",
)
mcp.add_prompt(manticore_prompt)
logger.info("Manticore Search prompt registered")
