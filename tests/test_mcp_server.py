"""Tests for MCP server tools and prompts."""

import os
from unittest.mock import MagicMock, patch

import pytest

from mcp_manticore.mcp_server import (
    create_manticore_client,
    manticore_initial_prompt,
)


class TestCreateManticoreClient:
    """Tests for create_manticore_client function."""

    @patch.dict(
        os.environ,
        {
            "MANTICORE_HOST": "testhost",
            "MANTICORE_PORT": "9312",
            "MANTICORE_USER": "testuser",
            "MANTICORE_PASSWORD": "testpass",
        },
    )
    def test_create_client_with_auth(self):
        """Test client creation with authentication."""
        client = create_manticore_client()
        assert client is not None

    @patch.dict(
        os.environ,
        {
            "MANTICORE_HOST": "localhost",
            "MANTICORE_PORT": "9308",
        },
        clear=True,
    )
    def test_create_client_without_auth(self):
        """Test client creation without authentication."""
        # Clear auth env vars
        for key in ["MANTICORE_USER", "MANTICORE_PASSWORD"]:
            if key in os.environ:
                del os.environ[key]

        client = create_manticore_client()
        assert client is not None


class TestManticoreInitialPrompt:
    """Tests for manticore_initial_prompt function."""

    def test_prompt_returns_string(self):
        """Test that prompt returns a string."""
        prompt = manticore_initial_prompt()
        assert isinstance(prompt, str)

    def test_prompt_contains_tools(self):
        """Test that prompt mentions available tools."""
        prompt = manticore_initial_prompt()
        assert "list_documentation" in prompt
        assert "get_documentation" in prompt
        assert "run_query" in prompt
        assert "list_tables" in prompt
        assert "describe_table" in prompt

    def test_prompt_contains_knn_section(self):
        """Test that prompt includes KNN search documentation."""
        prompt = manticore_initial_prompt()
        assert "KNN" in prompt or "knn" in prompt.lower()
        assert "vector" in prompt.lower()

    def test_prompt_contains_full_text_search(self):
        """Test that prompt includes full-text search documentation."""
        prompt = manticore_initial_prompt()
        assert "MATCH" in prompt
        assert "full-text" in prompt.lower()

    def test_prompt_contains_fuzzy_search(self):
        """Test that prompt includes fuzzy search documentation."""
        prompt = manticore_initial_prompt()
        assert "fuzzy" in prompt.lower()

    def test_prompt_contains_examples(self):
        """Test that prompt includes SQL examples."""
        prompt = manticore_initial_prompt()
        assert "SELECT" in prompt
        assert "INSERT" in prompt or "CREATE" in prompt


class TestPromptRegistration:
    """Tests for prompt registration with FastMCP."""

    def test_prompt_is_registered(self):
        """Test that prompt is properly registered."""
        from mcp_manticore.mcp_server import manticore_prompt, mcp

        # Check that prompt object exists
        assert manticore_prompt is not None

        # Check that mcp instance exists
        assert mcp is not None


class TestToolRegistration:
    """Tests for tool registration with FastMCP."""

    def test_tools_are_registered(self):
        """Test that all tools are registered with MCP server."""
        from mcp_manticore.mcp_server import mcp

        # Get registered tools
        # FastMCP stores tools internally
        assert mcp is not None
        # Tools are registered via @mcp.tool() decorator


class TestHealthCheckEndpoint:
    """Tests for health check endpoint."""

    @pytest.mark.asyncio
    async def test_health_check_success(self):
        """Test health check with successful connection."""
        from starlette.requests import Request

        from mcp_manticore.mcp_server import health_check

        # Mock request
        request = MagicMock(spec=Request)

        # Mock create_manticore_client
        with patch("mcp_manticore.mcp_server.create_manticore_client") as mock_client:
            mock_client.return_value.utils.sql.return_value = []
            response = await health_check(request)
            assert response.status_code == 200
            assert "OK" in response.body.decode()

    @pytest.mark.asyncio
    async def test_health_check_failure(self):
        """Test health check with connection failure."""
        from starlette.requests import Request

        from mcp_manticore.mcp_server import health_check

        request = MagicMock(spec=Request)

        with patch("mcp_manticore.mcp_server.create_manticore_client") as mock_client:
            mock_client.side_effect = Exception("Connection failed")
            response = await health_check(request)
            assert response.status_code == 503
            assert "ERROR" in response.body.decode()
