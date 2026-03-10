"""Shared pytest fixtures and configuration."""

import os
from unittest.mock import patch

import pytest


@pytest.fixture(autouse=True)
def reset_config_singleton():
    """Reset configuration singletons before each test."""
    from mcp_manticore import mcp_env

    # Reset singletons
    mcp_env._MANTICORE_CONFIG_INSTANCE = None
    mcp_env._MCP_CONFIG_INSTANCE = None

    yield

    # Clean up after test
    mcp_env._MANTICORE_CONFIG_INSTANCE = None
    mcp_env._MCP_CONFIG_INSTANCE = None


@pytest.fixture
def clean_env():
    """Fixture to provide clean environment variables."""
    original_env = os.environ.copy()
    yield
    # Restore original environment
    os.environ.clear()
    os.environ.update(original_env)


@pytest.fixture
def mock_manticore_config():
    """Fixture for mock Manticore configuration."""
    with patch.dict(
        os.environ,
        {
            "MANTICORE_HOST": "localhost",
            "MANTICORE_PORT": "9308",
        },
    ):
        yield


@pytest.fixture
def mock_github_response():
    """Fixture for mock GitHub API response."""
    return [
        {"type": "file", "name": "README.md"},
        {"type": "dir", "name": "Searching"},
    ]


# Configure pytest-asyncio
pytest_plugins = ("pytest_asyncio",)


def pytest_configure(config):
    """Configure pytest with async mode."""
    config.addinivalue_line("markers", "asyncio: mark test as async")


# Set asyncio mode to auto
pytestmark = pytest.mark.asyncio(loop_scope="function")
