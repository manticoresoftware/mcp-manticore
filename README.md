# Manticore Search MCP Server

[![PyPI - Version](https://img.shields.io/pypi/v/mcp-manticore)](https://pypi.org/project/mcp-manticore)

An MCP server for Manticore Search.

## Features

### Tools

* `run_query` - Execute SQL queries (SELECT, SHOW, DESCRIBE, etc.)
* `list_tables` - List all tables/indexes
* `describe_table` - Get table schema
* `list_documentation` - List available documentation files from GitHub (discover before fetching)
* `get_documentation` - Fetch specific documentation file from Manticore Search manual

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


### Write Access Control

Safety features to prevent accidental data modification:

- `MANTICORE_ALLOW_WRITE_ACCESS` - Enable write operations (default: `false`)
  - When `false`: All write operations are blocked (INSERT, REPLACE, UPDATE, DELETE, DROP, TRUNCATE)
  - When `true`: Write operations are allowed, but destructive operations still require explicit permission
- `MANTICORE_ALLOW_DROP` - Enable destructive operations (default: `false`)
  - When `false`: DROP TABLE, DROP INDEX, TRUNCATE are blocked
  - When `true`: Destructive operations are allowed (requires `MANTICORE_ALLOW_WRITE_ACCESS=true`)

**Safety Pattern:**
1. Read-only by default (both flags `false`)
2. Enable writes: `MANTICORE_ALLOW_WRITE_ACCESS=true`
3. Enable destructive ops: Both `MANTICORE_ALLOW_WRITE_ACCESS=true` AND `MANTICORE_ALLOW_DROP=true`

### MCP Server

- `MANTICORE_MCP_SERVER_TRANSPORT` - Transport type: `stdio`, `http`, `sse` (default: `stdio`)
- `MANTICORE_MCP_BIND_HOST` - Bind host for HTTP/SSE (default: `127.0.0.1`)
- `MANTICORE_MCP_BIND_PORT` - Bind port for HTTP/SSE (default: `8000`)
- `MANTICORE_MCP_AUTH_TOKEN` - Auth token for HTTP/SSE (optional)
- `MANTICORE_MCP_AUTH_DISABLED` - Disable auth (default: `false`)

### GitHub API (Optional)

- `GITHUB_TOKEN` - GitHub personal access token (optional, increases rate limit from 60 to 5000 requests/hour)
  - Without token: 60 requests/hour per IP
  - With token: 5000 requests/hour
  - Used for fetching documentation from Manticore Search manual

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

**With write access enabled:**

```json
{
  "mcpServers": {
    "manticore": {
      "command": "mcp-manticore",
      "env": {
        "MANTICORE_HOST": "localhost",
        "MANTICORE_PORT": "9308",
        "MANTICORE_ALLOW_WRITE_ACCESS": "true"
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
git clone https://github.com/manticoresoftware/mcp-manticore.git
cd mcp-manticore
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
- `mcp_manticore/docs_fetcher.py` - Documentation fetcher
- `mcp_manticore/main.py` - Entry point

## License

Apache-2.0