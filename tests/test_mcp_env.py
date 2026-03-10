"""Tests for environment configuration."""

import os
from unittest.mock import patch

import pytest

from mcp_manticore.mcp_env import (
    ManticoreConfig,
    MCPServerConfig,
    TransportType,
    get_config,
    get_mcp_config,
)


class TestTransportType:
    """Tests for TransportType enum."""

    def test_transport_values(self):
        """Test that TransportType has correct values."""
        assert TransportType.STDIO.value == "stdio"
        assert TransportType.HTTP.value == "http"
        assert TransportType.SSE.value == "sse"

    def test_values_classmethod(self):
        """Test TransportType.values() returns all transport values."""
        values = TransportType.values()
        assert "stdio" in values
        assert "http" in values
        assert "sse" in values
        assert len(values) == 3


class TestManticoreConfig:
    """Tests for ManticoreConfig."""

    def test_default_values(self):
        """Test default configuration values."""
        config = ManticoreConfig()
        assert config.host == "localhost"
        assert config.port == 9308
        assert config.username is None
        assert config.password is None
        assert config.database is None
        assert config.connect_timeout == 30
        assert config.query_timeout == 30

    @patch.dict(
        os.environ,
        {
            "MANTICORE_HOST": "manticore.example.com",
            "MANTICORE_PORT": "9312",
            "MANTICORE_USER": "admin",
            "MANTICORE_PASSWORD": "secret",
            "MANTICORE_DATABASE": "myindex",
            "MANTICORE_CONNECT_TIMEOUT": "60",
            "MANTICORE_QUERY_TIMEOUT": "120",
        },
    )
    def test_environment_overrides(self):
        """Test that environment variables override defaults."""
        config = ManticoreConfig()
        assert config.host == "manticore.example.com"
        assert config.port == 9312
        assert config.username == "admin"
        assert config.password == "secret"
        assert config.database == "myindex"
        assert config.connect_timeout == 60
        assert config.query_timeout == 120

    def test_get_client_config_minimal(self):
        """Test get_client_config with minimal config."""
        config = ManticoreConfig()
        client_config = config.get_client_config()
        assert client_config == {"host": "localhost", "port": 9308}
        assert "username" not in client_config
        assert "password" not in client_config

    @patch.dict(
        os.environ,
        {"MANTICORE_USER": "admin", "MANTICORE_PASSWORD": "secret"},
    )
    def test_get_client_config_with_auth(self):
        """Test get_client_config includes auth when set."""
        config = ManticoreConfig()
        client_config = config.get_client_config()
        assert client_config["username"] == "admin"
        assert client_config["password"] == "secret"


class TestMCPServerConfig:
    """Tests for MCPServerConfig."""

    def test_default_values(self):
        """Test default MCP server configuration."""
        config = MCPServerConfig()
        assert config.server_transport == "stdio"
        assert config.bind_host == "127.0.0.1"
        assert config.bind_port == 8000
        assert config.auth_token is None
        assert config.auth_disabled is False

    @patch.dict(
        os.environ,
        {
            "MANTICORE_MCP_SERVER_TRANSPORT": "http",
            "MANTICORE_MCP_BIND_HOST": "0.0.0.0",
            "MANTICORE_MCP_BIND_PORT": "9000",
            "MANTICORE_MCP_AUTH_TOKEN": "mytoken123",
            "MANTICORE_MCP_AUTH_DISABLED": "true",
        },
    )
    def test_environment_overrides(self):
        """Test MCP server config environment overrides."""
        config = MCPServerConfig()
        assert config.server_transport == "http"
        assert config.bind_host == "0.0.0.0"
        assert config.bind_port == 9000
        assert config.auth_token == "mytoken123"
        assert config.auth_disabled is True

    @patch.dict(os.environ, {"MANTICORE_MCP_SERVER_TRANSPORT": "invalid"})
    def test_invalid_transport_raises_error(self):
        """Test that invalid transport raises ValueError."""
        config = MCPServerConfig()
        with pytest.raises(ValueError, match="Invalid transport"):
            _ = config.server_transport

    @patch.dict(os.environ, {"MANTICORE_MCP_SERVER_TRANSPORT": "HTTP"})
    def test_transport_case_insensitive(self):
        """Test that transport is case-insensitive."""
        config = MCPServerConfig()
        assert config.server_transport == "http"


class TestSingletonPattern:
    """Tests for singleton pattern."""

    def test_get_config_singleton(self):
        """Test that get_config returns singleton instance."""
        # Reset singleton
        import mcp_manticore.mcp_env as env_module

        env_module._CONFIG_INSTANCE = None

        config1 = get_config()
        config2 = get_config()
        assert config1 is config2

    def test_get_mcp_config_singleton(self):
        """Test that get_mcp_config returns singleton instance."""
        # Reset singleton
        import mcp_manticore.mcp_env as env_module

        env_module._MCP_CONFIG_INSTANCE = None

        config1 = get_mcp_config()
        config2 = get_mcp_config()
        assert config1 is config2
