import logging
import json
from typing import Optional, List, Dict, Any
import concurrent.futures
import atexit

import manticoresearch
from manticoresearch.api import utils_api
from dotenv import load_dotenv
from fastmcp import FastMCP
from fastmcp.prompts import Prompt
from fastmcp.exceptions import ToolError
from fastmcp.server.dependencies import get_context
from starlette.requests import Request
from starlette.responses import PlainTextResponse

from mcp_manticore.mcp_env import get_config, get_mcp_config, TransportType
from mcp_manticore.manticore_prompt import MANTICORE_PROMPT
from fastmcp.server.auth.providers.jwt import StaticTokenVerifier


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
        result = client.utils.sql("SHOW TABLES")
        return PlainTextResponse("OK - Connected to Manticore Search")
    except Exception as e:
        # Return 503 Service Unavailable if we can't connect to Manticore
        return PlainTextResponse(f"ERROR - Cannot connect to Manticore Search: {str(e)}", status_code=503)


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
            logger.warning(f"{CLIENT_CONFIG_OVERRIDES_KEY} must be a dict, got {type(session_config_overrides).__name__}. Ignoring.")
        elif session_config_overrides:
            logger.debug(f"Applying session-specific Manticore client config overrides: {list(session_config_overrides.keys())}")
            client_config.update(session_config_overrides)
    except RuntimeError:
        # If we're outside a request context, just proceed with the default config
        pass

    logger.info(
        f"Creating Manticore Search client connection to {client_config['host']}:{client_config['port']}"
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


def execute_query(query: str):
    """Execute a SQL query against Manticore Search.
    
    Args:
        query: The SQL query to execute
        
    Returns:
        dict: Query results with columns and rows
    """
    client = create_manticore_client()
    try:
        # Execute the SQL query using the utils API
        # The sql() method returns SqlResponse which can be:
        # - List[Dict[str, Any]] for queries like SHOW TABLES
        # - SqlObjResponse for SELECT queries with hits structure
        result = client.sql(query)
        
        # Handle SqlResponse - it has an actual_instance attribute
        if hasattr(result, 'actual_instance'):
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
        
        elif hasattr(actual, 'hits'):
            # SqlObjResponse with hits structure (SELECT queries)
            hits = actual.hits
            if isinstance(hits, dict):
                hits_list = hits.get('hits', [])
                total = hits.get('total', 0)
                
                if hits_list and len(hits_list) > 0:
                    # Extract column names from the first hit's _source
                    first_hit = hits_list[0]
                    if '_source' in first_hit:
                        column_names = list(first_hit['_source'].keys())
                        rows = [list(hit.get('_source', {}).values()) for hit in hits_list]
                        return {"columns": column_names, "rows": rows, "total": total}
            
            return {"columns": [], "rows": [], "total": 0}
        
        return {"columns": [], "rows": [], "total": 0}
    except ToolError:
        raise
    except Exception as err:
        logger.error(f"Error executing query: {err}")
        raise ToolError(f"Query execution failed: {str(err)}")


@mcp.tool()
def run_query(query: str) -> Dict[str, Any]:
    """Execute a SQL query against Manticore Search.

    Use this tool to run SELECT, SHOW, DESCRIBE, and other SQL queries.
    The query is executed in read-only mode by default.

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
            timeout_secs = get_mcp_config().query_timeout
            result = future.result(timeout=timeout_secs)
            return result
        except concurrent.futures.TimeoutError:
            logger.warning(f"Query timed out after {timeout_secs} seconds: {query}")
            future.cancel()
            raise ToolError(f"Query timed out after {timeout_secs} seconds")
    except ToolError:
        raise
    except Exception as e:
        logger.error(f"Unexpected error in run_query: {str(e)}")
        raise RuntimeError(f"Unexpected error during query execution: {str(e)}")


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
        if hasattr(result, 'actual_instance'):
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
        raise ToolError(f"Failed to list tables: {str(e)}")


@mcp.tool()
def describe_table(table_name: str) -> Dict[str, Any]:
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
        if hasattr(result, 'actual_instance'):
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
        raise ToolError(f"Failed to describe table {table_name}: {str(e)}")


def manticore_initial_prompt() -> str:
    """This prompt helps users understand how to interact and perform common operations in Manticore Search"""
    return MANTICORE_PROMPT


# Register the prompt
manticore_prompt = Prompt.from_function(
    manticore_initial_prompt,
    name="manticore_initial_prompt",
    description="This prompt helps users understand how to interact and perform common operations in Manticore Search",
)
mcp.add_prompt(manticore_prompt)
logger.info("Manticore Search prompt registered")