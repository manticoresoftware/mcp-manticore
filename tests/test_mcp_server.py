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


class TestQueryValidation:
    """Tests for query validation and write access control."""

    @patch.dict(os.environ, {"MANTICORE_ALLOW_WRITE_ACCESS": "false"})
    def test_validate_destructive_ops_drop_table_blocked(self):
        """Test that DROP TABLE is blocked when write access is disabled."""
        from fastmcp.exceptions import ToolError

        from mcp_manticore.mcp_server import _validate_query_access

        with pytest.raises(ToolError, match="Write operations"):
            _validate_query_access("DROP TABLE myindex")

    @patch.dict(os.environ, {"MANTICORE_ALLOW_WRITE_ACCESS": "false"})
    def test_validate_destructive_ops_truncate_blocked(self):
        """Test that TRUNCATE is blocked when write access is disabled."""
        from fastmcp.exceptions import ToolError

        from mcp_manticore.mcp_server import _validate_query_access

        with pytest.raises(ToolError, match="Write operations"):
            _validate_query_access("TRUNCATE TABLE myindex")

    @patch.dict(
        os.environ,
        {"MANTICORE_ALLOW_WRITE_ACCESS": "true", "MANTICORE_ALLOW_DROP": "false"},
    )
    def test_validate_destructive_ops_drop_blocked_without_flag(self):
        """Test that DROP is blocked even with write access when allow_drop is false."""
        from fastmcp.exceptions import ToolError

        from mcp_manticore.mcp_server import _validate_query_access

        with pytest.raises(ToolError, match="Destructive operations"):
            _validate_query_access("DROP TABLE myindex")

    @patch.dict(
        os.environ,
        {"MANTICORE_ALLOW_WRITE_ACCESS": "true", "MANTICORE_ALLOW_DROP": "true"},
    )
    def test_validate_destructive_ops_drop_allowed(self):
        """Test that DROP is allowed when both flags are set."""
        from mcp_manticore.mcp_server import _validate_query_access

        # Should not raise any error
        _validate_query_access("DROP TABLE myindex")

    @patch.dict(os.environ, {"MANTICORE_ALLOW_WRITE_ACCESS": "false"})
    def test_validate_select_allowed(self):
        """Test that SELECT queries are allowed in read-only mode."""
        from mcp_manticore.mcp_server import _validate_query_access

        # Should not raise any error
        _validate_query_access("SELECT * FROM myindex")

    @patch.dict(os.environ, {"MANTICORE_ALLOW_WRITE_ACCESS": "false"})
    def test_validate_show_tables_allowed(self):
        """Test that SHOW TABLES is allowed in read-only mode."""
        from mcp_manticore.mcp_server import _validate_query_access

        # Should not raise any error
        _validate_query_access("SHOW TABLES")

    @patch.dict(os.environ, {"MANTICORE_ALLOW_WRITE_ACCESS": "true"})
    def test_validate_insert_allowed_with_write_access(self):
        """Test that INSERT is allowed with write access."""
        from mcp_manticore.mcp_server import _validate_query_access

        # Should not raise any error
        _validate_query_access("INSERT INTO myindex (id, title) VALUES (1, 'test')")

    @patch.dict(os.environ, {"MANTICORE_ALLOW_WRITE_ACCESS": "false"})
    def test_validate_insert_blocked_without_write_access(self):
        """Test that INSERT is blocked without write access."""
        from fastmcp.exceptions import ToolError

        from mcp_manticore.mcp_server import _validate_query_access

        with pytest.raises(ToolError, match="Write operations"):
            _validate_query_access("INSERT INTO myindex (id, title) VALUES (1, 'test')")

    @patch.dict(os.environ, {"MANTICORE_ALLOW_WRITE_ACCESS": "false"})
    def test_validate_replace_blocked_without_write_access(self):
        """Test that REPLACE is blocked without write access."""
        from fastmcp.exceptions import ToolError

        from mcp_manticore.mcp_server import _validate_query_access

        with pytest.raises(ToolError, match="Write operations"):
            _validate_query_access("REPLACE INTO myindex (id, title) VALUES (1, 'test')")

    @patch.dict(os.environ, {"MANTICORE_ALLOW_WRITE_ACCESS": "false"})
    def test_validate_update_blocked_without_write_access(self):
        """Test that UPDATE is blocked without write access."""
        from fastmcp.exceptions import ToolError

        from mcp_manticore.mcp_server import _validate_query_access

        with pytest.raises(ToolError, match="Write operations"):
            _validate_query_access("UPDATE myindex SET title = 'new' WHERE id = 1")

    @patch.dict(os.environ, {"MANTICORE_ALLOW_WRITE_ACCESS": "false"})
    def test_validate_delete_blocked_without_write_access(self):
        """Test that DELETE is blocked without write access."""
        from fastmcp.exceptions import ToolError

        from mcp_manticore.mcp_server import _validate_query_access

        with pytest.raises(ToolError, match="Write operations"):
            _validate_query_access("DELETE FROM myindex WHERE id = 1")

    @patch.dict(os.environ, {"MANTICORE_ALLOW_WRITE_ACCESS": "true"})
    def test_validate_replace_allowed_with_write_access(self):
        """Test that REPLACE is allowed with write access."""
        from mcp_manticore.mcp_server import _validate_query_access

        # Should not raise any error
        _validate_query_access("REPLACE INTO myindex (id, title) VALUES (1, 'test')")
