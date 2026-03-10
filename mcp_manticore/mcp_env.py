"""Environment configuration for the MCP Manticore Search server.

This module handles all environment variable configuration with sensible defaults
and type conversion.
"""

import os
from dataclasses import dataclass
from enum import Enum


class TransportType(str, Enum):
    """Supported MCP server transport types."""

    STDIO = "stdio"
    HTTP = "http"
    SSE = "sse"

    @classmethod
    def values(cls) -> list[str]:
        """Get all valid transport values."""
        return [transport.value for transport in cls]


@dataclass
class ManticoreConfig:
    """Configuration for Manticore Search connection settings.

    This class handles all environment variable configuration with sensible defaults
    and type conversion. It provides typed methods for accessing each configuration value.

    Required environment variables:
        MANTICORE_HOST: The hostname of the Manticore Search server (default: localhost)
        MANTICORE_PORT: The port number (default: 9308 for HTTP API)

    Optional environment variables (with defaults):
        MANTICORE_USER: The username for authentication (default: None)
        MANTICORE_PASSWORD: The password for authentication (default: None)
        MANTICORE_DATABASE: Default database/index to use (default: None)
        MANTICORE_CONNECT_TIMEOUT: Connection timeout in seconds (default: 30)
        MANTICORE_QUERY_TIMEOUT: Query timeout in seconds (default: 30)
    """

    @property
    def host(self) -> str:
        """Get the Manticore Search host.

        Default: localhost
        """
        return os.getenv("MANTICORE_HOST", "localhost")

    @property
    def port(self) -> int:
        """Get the Manticore Search port.

        Default: 9308 (HTTP API port)
        """
        return int(os.getenv("MANTICORE_PORT", "9308"))

    @property
    def username(self) -> str | None:
        """Get the Manticore username (optional)."""
        return os.getenv("MANTICORE_USER")

    @property
    def password(self) -> str | None:
        """Get the Manticore password (optional)."""
        return os.getenv("MANTICORE_PASSWORD")

    @property
    def database(self) -> str | None:
        """Get the default database/index name if set."""
        return os.getenv("MANTICORE_DATABASE")

    @property
    def connect_timeout(self) -> int:
        """Get the connection timeout in seconds.

        Default: 30
        """
        return int(os.getenv("MANTICORE_CONNECT_TIMEOUT", "30"))

    @property
    def query_timeout(self) -> int:
        """Get the query timeout in seconds.

        Default: 30
        """
        return int(os.getenv("MANTICORE_QUERY_TIMEOUT", "30"))

    def get_client_config(self) -> dict:
        """Get the configuration dictionary for manticoresearch client.

        Returns:
            dict: Configuration ready to be passed to manticoresearch client
        """
        config = {
            "host": self.host,
            "port": self.port,
        }

        # Add optional username/password if set
        if self.username:
            config["username"] = self.username
        if self.password:
            config["password"] = self.password

        return config


# Global instance placeholder for the singleton pattern
_CONFIG_INSTANCE = None


def get_config():
    """
    Gets the singleton instance of ManticoreConfig.
    Instantiates it on the first call.
    """
    global _CONFIG_INSTANCE
    if _CONFIG_INSTANCE is None:
        _CONFIG_INSTANCE = ManticoreConfig()
    return _CONFIG_INSTANCE


@dataclass
class MCPServerConfig:
    """Configuration for MCP server-level settings.

    These settings control the server transport and tool behavior.

    Optional environment variables (with defaults):
        MANTICORE_MCP_SERVER_TRANSPORT: "stdio", "http", or "sse" (default: stdio)
        MANTICORE_MCP_BIND_HOST: Bind host for HTTP/SSE (default: 127.0.0.1)
        MANTICORE_MCP_BIND_PORT: Bind port for HTTP/SSE (default: 8000)
        MANTICORE_MCP_AUTH_TOKEN: Authentication token for HTTP/SSE transports (optional)
        MANTICORE_MCP_AUTH_DISABLED: Disable authentication (default: false, use
            only for development)
    """

    @property
    def server_transport(self) -> str:
        transport = os.getenv("MANTICORE_MCP_SERVER_TRANSPORT", TransportType.STDIO.value).lower()
        if transport not in TransportType.values():
            valid_options = ", ".join(f'"{t}"' for t in TransportType.values())
            raise ValueError(f"Invalid transport '{transport}'. Valid options: {valid_options}")
        return transport

    @property
    def bind_host(self) -> str:
        return os.getenv("MANTICORE_MCP_BIND_HOST", "127.0.0.1")

    @property
    def bind_port(self) -> int:
        return int(os.getenv("MANTICORE_MCP_BIND_PORT", "8000"))

    @property
    def auth_token(self) -> str | None:
        """Get the authentication token for HTTP/SSE transports."""
        return os.getenv("MANTICORE_MCP_AUTH_TOKEN", None)

    @property
    def auth_disabled(self) -> bool:
        """Get whether authentication is disabled."""
        return os.getenv("MANTICORE_MCP_AUTH_DISABLED", "false").lower() == "true"


_MCP_CONFIG_INSTANCE = None


def get_mcp_config() -> MCPServerConfig:
    """Gets the singleton instance of MCPServerConfig."""
    global _MCP_CONFIG_INSTANCE
    if _MCP_CONFIG_INSTANCE is None:
        _MCP_CONFIG_INSTANCE = MCPServerConfig()
    return _MCP_CONFIG_INSTANCE
