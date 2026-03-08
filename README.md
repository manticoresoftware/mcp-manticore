# Manticore Search MCP Server

[![PyPI - Version](https://img.shields.io/pypi/v/mcp-manticore)](https://pypi.org/project/mcp-manticore)

An MCP server for Manticore Search.

## Features

### Tools

* `run_query` - Execute SQL queries (SELECT, SHOW, DESCRIBE, etc.)
* `list_tables` - List all tables/indexes
* `describe_table` - Get table schema

### Prompt

* `manticore_initial_prompt` - Built-in prompt teaching LLMs about Manticore Search features (full-text operators, KNN vector search, fuzzy search, etc.)

### Health Check

HTTP endpoint at `/health` for monitoring connectivity.

## Installation

```bash
pip install mcp-manticore
```

## Configuration

### Manticore Connection

- `MANTICORE_HOST` - Host (default: `localhost`)
- `MANTICORE_PORT` - HTTP API port (default: `9308`)
- `MANTICORE_USER` - Username (optional)
- `MANTICORE_PASSWORD` - Password (optional)
- `MANTICORE_CONNECT_TIMEOUT` - Connection timeout (default: `30`)
- `MANTICORE_QUERY_TIMEOUT` - Query timeout (default: `30`)

### MCP Server

- `MANTICORE_MCP_SERVER_TRANSPORT` - Transport type: `stdio`, `http`, `sse` (default: `stdio`)
- `MANTICORE_MCP_BIND_HOST` - Bind host for HTTP/SSE (default: `127.0.0.1`)
- `MANTICORE_MCP_BIND_PORT` - Bind port for HTTP/SSE (default: `8000`)
- `MANTICORE_MCP_AUTH_TOKEN` - Auth token for HTTP/SSE (optional)
- `MANTICORE_MCP_AUTH_DISABLED` - Disable auth (default: `false`)

## Usage

### Claude Desktop

```json
{
  "mcpServers": {
    "manticore": {
      "command": "mcp-manticore",
      "env": {
        "MANTICORE_HOST": "localhost",
        "MANTICORE_PORT": "9308"
      }
    }
  }
}
```

### HTTP Transport

```bash
MANTICORE_MCP_SERVER_TRANSPORT=http \
MANTICORE_MCP_BIND_PORT=8000 \
mcp-manticore
```

### Authentication (HTTP/SSE)

Generate token:
```bash
uuidgen
```

Configure:
```bash
export MANTICORE_MCP_AUTH_TOKEN="your-token"
```

For development:
```bash
export MANTICORE_MCP_AUTH_DISABLED=true
```

## Development

```bash
# Setup
git clone https://github.com/manticoresoftware/manticoresearch-mcp.git
cd manticoresearch-mcp
uv sync

# Run
uv run mcp-manticore

# Test
uv run pytest
```

## Architecture

- `mcp_manticore/mcp_env.py` - Configuration
- `mcp_manticore/mcp_server.py` - MCP server with tools and prompts
- `mcp_manticore/manticore_prompt.py` - LLM guidance
- `mcp_manticore/main.py` - Entry point

## License

Apache-2.0