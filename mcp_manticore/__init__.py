import os

from .mcp_server import (
    create_manticore_client,
    list_tables,
    run_query,
    describe_table,
    get_documentation,
    manticore_initial_prompt,
)

if os.getenv("MCP_MANTICORE_TRUSTSTORE_DISABLE", None) != "1":
    try:
        import truststore
        truststore.inject_into_ssl()
    except Exception:
        pass

__all__ = [
    "list_tables",
    "run_query",
    "describe_table",
    "get_documentation",
    "create_manticore_client",
    "manticore_initial_prompt",
]