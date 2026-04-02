# Manticore Search MCP Server

[![PyPI - Version](https://img.shields.io/pypi/v/mcp-manticore)](https://pypi.org/project/mcp-manticore)
[![uv](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/astral-sh/uv/main/assets/badge/v0.json)](https://github.com/astral-sh/uv)

MCP server for Manticore Search — enables AI assistants to query and manage Manticore Search databases directly.

## Quick Start

### Installation

```bash
# Option 1: Install with uv (recommended, requires PyPI release)
uvx mcp-manticore

# Option 2: Install with pip
pip install mcp-manticore

# Option 3: Run from source (for local development)
uvx --from . mcp-manticore
# Or: uv run mcp-manticore
```

> **Note**: 
> - `uvx` runs the package directly without installation. First-time run may take a moment to download dependencies.
> - The package must be published to PyPI for `uvx mcp-manticore` to work.
> - For local development or testing unreleased versions, use `uvx --from . mcp-manticore`

---

## What It Does

### Tools

| Tool | Description |
|------|-------------|
| `run_query` | Execute SQL queries (SELECT, SHOW, DESCRIBE, etc.) |
| `list_tables` | List all tables and indexes |
| `describe_table` | Get table schema |
| `list_documentation` | List available documentation files |
| `get_documentation` | Fetch specific documentation from Manticore manual |

### Prompts

- `manticore_initial_prompt` — Built-in prompt teaching LLMs about Manticore Search features (full-text operators, KNN vector search, fuzzy search, etc.)

### Health Check

HTTP endpoint at `/health` for monitoring connectivity.

---

## Configuration

### Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `MANTICORE_HOST` | `localhost` | Manticore server host |
| `MANTICORE_PORT` | `9308` | HTTP API port |
| `MANTICORE_USER` | — | Username (optional) |
| `MANTICORE_PASSWORD` | — | Password (optional) |
| `MANTICORE_CONNECT_TIMEOUT` | `30` | Connection timeout (seconds) |
| `MANTICORE_QUERY_TIMEOUT` | `30` | Query timeout (seconds) |
| `MANTICORE_ALLOW_WRITE_ACCESS` | `false` | Enable write operations (INSERT, UPDATE, DELETE) |
| `MANTICORE_ALLOW_DROP` | `false` | Enable destructive operations (DROP, TRUNCATE) |
| `GITHUB_TOKEN` | — | GitHub token for higher API rate limit |

#### Safety

By default, all write operations are blocked. To enable:

```bash
# Enable writes (INSERT, UPDATE, DELETE)
export MANTICORE_ALLOW_WRITE_ACCESS=true

# Enable destructive operations (DROP, TRUNCATE)
export MANTICORE_ALLOW_DROP=true
```

---

## Connect to Your AI Assistant

<details>
<summary><strong>Claude Code</strong></summary>

Open terminal and run:

```bash
claude mcp add manticore -- uvx mcp-manticore
```

Or with environment variables:

```bash
claude mcp add manticore -- uvx mcp-manticore -- \
  MANTICORE_HOST=localhost \
  MANTICORE_PORT=9308
```

For full configuration, edit `~/.claude/mcp_settings.json`:

```json
{
  "mcpServers": {
    "manticore": {
      "command": "uvx",
      "args": ["mcp-manticore"],
      "env": {
        "MANTICORE_HOST": "localhost",
        "MANTICORE_PORT": "9308"
      }
    }
  }
}
```

Restart Claude Code or type `/mcp restart` to apply changes.

</details>

<details>
<summary><strong>Cursor</strong></summary>

**Method 1: Via Settings UI**
1. Open Cursor → Settings → Tools & MCP
2. Click "Add MCP Server"
3. Enter name: `manticore`
4. Command: `uvx mcp-manticore`

**Method 2: Via Config File**

Global config (`~/.cursor/mcp.json`):

```json
{
  "mcpServers": {
    "manticore": {
      "command": "uvx",
      "args": ["mcp-manticore"],
      "env": {
        "MANTICORE_HOST": "localhost",
        "MANTICORE_PORT": "9308"
      }
    }
  }
}
```

Project config (`.cursor/mcp.json` in your project):

```json
{
  "mcpServers": {
    "manticore": {
      "command": "uvx",
      "args": ["mcp-manticore"]
    }
  }
}
```

</details>

<details>
<summary><strong>Windsurf</strong></summary>

**Method 1: Via Cascade UI**
1. Open Windsurf → Cascade panel
2. Click the MCPs icon (🔨) in the top-right
3. Click "Add Server"
4. Enter: `uvx mcp-manticore`

**Method 2: Via Config File**

Edit `~/.codeium/windsurf/mcp_config.json`:

```json
{
  "mcpServers": {
    "manticore": {
      "command": "uvx",
      "args": ["mcp-manticore"],
      "env": {
        "MANTICORE_HOST": "localhost",
        "MANTICORE_PORT": "9308"
      }
    }
  }
}
```

Or open directly in Windsurf: `Cmd/Ctrl + Shift + P` → "MCP Configuration Panel"

</details>

<details>
<summary><strong>OpenAI Codex</strong></summary>

Run in terminal:

```bash
codex mcp add manticore -- uvx mcp-manticore
```

With environment variables:

```bash
codex mcp add manticore \
  --env MANTICORE_HOST=localhost \
  --env MANTICORE_PORT=9308 \
  -- uvx mcp-manticore
```

Or edit `~/.codex/config.toml` directly:

```toml
[mcp_servers.manticore]
command = "uvx"
args = ["mcp-manticore"]
env = { MANTICORE_HOST = "localhost", MANTICORE_PORT = "9308" }
```

</details>

<details>
<summary><strong>Gemini CLI</strong></summary>

Edit `~/.gemini/settings.json`:

```json
{
  "mcpServers": {
    "manticore": {
      "command": "uvx",
      "args": ["mcp-manticore"],
      "env": {
        "MANTICORE_HOST": "localhost",
        "MANTICORE_PORT": "9308"
      }
    }
  }
}
```

</details>

<details>
<summary><strong>VS Code (GitHub Copilot)</strong></summary>

Create `.vscode/mcp.json` in your workspace:

```json
{
  "servers": {
    "manticore": {
      "type": "stdio",
      "command": "uvx",
      "args": ["mcp-manticore"],
      "env": {
        "MANTICORE_HOST": "localhost",
        "MANTICORE_PORT": "9308"
      }
    }
  }
}
```

</details>

<details>
<summary><strong>Cline</strong></summary>

1. Open Cline panel in VS Code
2. Click the MCP Servers icon
3. Click "Configure" → "Add Server"
4. Select "Command (stdio)" and enter:
   - Name: `manticore`
   - Command: `uvx mcp-manticore`

Or edit the MCP settings file directly (accessible via the MCP Servers icon → "Edit Config"):

```json
{
  "mcpServers": {
    "manticore": {
      "command": "uvx",
      "args": ["mcp-manticore"],
      "env": {
        "MANTICORE_HOST": "localhost",
        "MANTICORE_PORT": "9308"
      }
    }
  }
}
```

</details>

<details>
<summary><strong>Roo Code</strong></summary>

1. Open Roo Code panel in VS Code
2. Click the MCP Servers icon → "Edit MCP Settings"
3. Add the server configuration

Or create `.roo/mcp.json` in your project root:

```json
{
  "mcpServers": {
    "manticore": {
      "command": "uvx",
      "args": ["mcp-manticore"],
      "env": {
        "MANTICORE_HOST": "localhost",
        "MANTICORE_PORT": "9308"
      }
    }
  }
}
```

</details>

<details>
<summary><strong>Claude Desktop (Legacy)</strong></summary>

Edit `~/Library/Application Support/Claude/claude_desktop_config.json` (macOS) or `%APPDATA%/Claude/claude_desktop_config.json` (Windows):

```json
{
  "mcpServers": {
    "manticore": {
      "command": "uvx",
      "args": ["mcp-manticore"],
      "env": {
        "MANTICORE_HOST": "localhost",
        "MANTICORE_PORT": "9308"
      }
    }
  }
}
```
</details>

---

## HTTP Transport (Remote MCP)

By default, MCP uses stdio (local). For remote access:

```bash
export MANTICORE_MCP_SERVER_TRANSPORT=http
export MANTICORE_MCP_BIND_PORT=8000
export MANTICORE_MCP_AUTH_TOKEN="your-secure-token"

uvx mcp-manticore
```

Connect via URL:

```json
{
  "mcpServers": {
    "manticore": {
      "url": "http://localhost:8000/mcp",
      "headers": {
        "Authorization": "Bearer your-secure-token"
      }
    }
  }
}
```

---

## Troubleshooting

### Install uv (required)

**macOS / Linux:**

```bash
# Via installer script (recommended)
curl -LsSf https://astral.sh/uv/install.sh | sh

# Or via Homebrew
brew install uv
```

**Windows:**

```powershell
# Via PowerShell
irm https://astral.sh/uv/install.ps1 | iex

# Or via winget
winget install astral-sh.uv
```

**Verify installation:**

```bash
uv --version
```

### MCP server not connecting

1. Verify Manticore is running: `curl http://localhost:9308/health`
2. Check environment variables are set correctly
3. For Claude Code: restart with `/mcp restart`

### Too many tools loaded

Some agents limit active MCP tools. Remove unused servers or use project-scoped configs.

---

## Development

```bash
# Clone and setup
git clone https://github.com/manticoresoftware/mcp-manticore.git
cd mcp-manticore

# Install dependencies
uv sync

# Run locally
uv run mcp-manticore

# Run with custom config
MANTICORE_HOST=remote-server MANTICORE_PORT=9308 uv run mcp-manticore

# Run tests
uv run pytest

# Build package
uv build

# Publish to PyPI
uv publish
```

### Architecture

| File | Purpose |
|------|---------|
| `mcp_manticore/mcp_env.py` | Configuration management |
| `mcp_manticore/mcp_server.py` | MCP server implementation |
| `mcp_manticore/manticore_prompt.py` | LLM guidance/prompts |
| `mcp_manticore/docs_fetcher.py` | GitHub docs fetcher |
| `mcp_manticore/main.py` | CLI entry point |

---

## License

[Apache-2.0](LICENSE)

<!-- Need to add this line for MCP registry publication -->
<!-- mcp-name: io.github.manticoresoftware/mcp-manticore -->

