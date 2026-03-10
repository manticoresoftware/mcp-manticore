"""Tests for documentation fetcher."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from mcp_manticore.docs_fetcher import (
    fetch_documentation,
    format_doc_list,
    list_documentation_files,
)


class TestListDocumentationFiles:
    """Tests for list_documentation_files."""

    @pytest.mark.asyncio
    async def test_list_files_success(self):
        """Test successful file listing from GitHub API."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = [
            {"type": "file", "name": "README.md"},
            {"type": "file", "name": "Introduction.md"},
            {"type": "dir", "name": "Searching"},
        ]

        mock_subdir_response = MagicMock()
        mock_subdir_response.status_code = 200
        mock_subdir_response.json.return_value = [
            {"type": "file", "name": "KNN.md"},
            {"type": "file", "name": "Intro.md"},
        ]

        with patch("mcp_manticore.docs_fetcher.httpx.AsyncClient") as mock_client:
            mock_instance = AsyncMock()
            mock_instance.__aenter__.return_value = mock_instance
            mock_instance.get.side_effect = [mock_response, mock_subdir_response]
            mock_client.return_value = mock_instance

            # Clear cache
            import mcp_manticore.docs_fetcher as docs_module

            docs_module._docs_cache = None

            files = await list_documentation_files()

            assert "README.md" in files
            assert "Introduction.md" in files
            assert "Searching/KNN.md" in files
            assert "Searching/Intro.md" in files

    @pytest.mark.asyncio
    async def test_list_files_cached(self):
        """Test that cached results are returned."""
        import mcp_manticore.docs_fetcher as docs_module

        # Set cache
        docs_module._docs_cache = ["cached.md"]

        files = await list_documentation_files()

        assert files == ["cached.md"]

        # Reset cache
        docs_module._docs_cache = None


class TestFetchDocumentation:
    """Tests for fetch_documentation."""

    @pytest.mark.asyncio
    async def test_fetch_full_document(self):
        """Test fetching full documentation file."""
        import mcp_manticore.docs_fetcher as docs_module

        # Set available files
        docs_module._docs_cache = ["test.md"]

        mock_response = MagicMock()
        mock_response.text = "# Test Document\n\nContent here."

        with patch("mcp_manticore.docs_fetcher.httpx.AsyncClient") as mock_client:
            mock_instance = AsyncMock()
            mock_instance.__aenter__.return_value = mock_instance
            mock_instance.get.return_value = mock_response
            mock_client.return_value = mock_instance

            # Clear content cache
            docs_module._content_cache = {}

            result = await fetch_documentation("test.md")

            assert "# Test Document" in result
            assert "Content here." in result

    @pytest.mark.asyncio
    async def test_fetch_with_content_filter(self):
        """Test fetching with content search filter."""
        import mcp_manticore.docs_fetcher as docs_module

        # Set available files
        docs_module._docs_cache = ["test.md"]

        mock_response = MagicMock()
        mock_response.text = """# Test Document

Line 1
MATCH keyword here
Line 3
Line 4
Another MATCH
Line 6"""

        with patch("mcp_manticore.docs_fetcher.httpx.AsyncClient") as mock_client:
            mock_instance = AsyncMock()
            mock_instance.__aenter__.return_value = mock_instance
            mock_instance.get.return_value = mock_response
            mock_client.return_value = mock_instance

            # Clear content cache
            docs_module._content_cache = {}

            result = await fetch_documentation("test.md", content="MATCH")

            assert "MATCH" in result

    @pytest.mark.asyncio
    async def test_fetch_invalid_file(self):
        """Test fetching invalid file raises error."""
        import mcp_manticore.docs_fetcher as docs_module

        # Set available files
        docs_module._docs_cache = ["valid.md"]

        with pytest.raises(ValueError, match="not found"):
            await fetch_documentation("invalid.md")

    @pytest.mark.asyncio
    async def test_fetch_cached_content(self):
        """Test that cached content is returned."""
        import mcp_manticore.docs_fetcher as docs_module

        # Set caches
        docs_module._docs_cache = ["test.md"]
        docs_module._content_cache = {"test.md": "cached content"}

        result = await fetch_documentation("test.md")

        assert result == "cached content"

        # Reset cache
        docs_module._content_cache = {}


class TestFormatDocList:
    """Tests for format_doc_list."""

    def test_format_empty_list(self):
        """Test formatting empty list."""
        result = format_doc_list([])
        assert result == ""

    def test_format_root_files(self):
        """Test formatting root-level files."""
        files = ["README.md", "Introduction.md"]
        result = format_doc_list(files)

        # Root files are listed without a "Root:" header
        assert "README.md" in result
        assert "Introduction.md" in result
        # Files should be sorted
        assert result.index("Introduction.md") < result.index("README.md")

    def test_format_categorized_files(self):
        """Test formatting categorized files."""
        files = ["Searching/KNN.md", "Searching/Intro.md", "Creating_a_table.md"]
        result = format_doc_list(files)

        assert "Searching:" in result
        assert "Searching/KNN.md" in result
        assert "Searching/Intro.md" in result
        # Root files appear first without a header
        assert "Creating_a_table.md" in result

    def test_format_sorted_output(self):
        """Test that output is sorted."""
        files = ["Zebra.md", "Alpha.md", "Beta.md"]
        result = format_doc_list(files)

        # Check that Alpha comes before Beta comes before Zebra
        assert result.index("Alpha.md") < result.index("Beta.md")
        assert result.index("Beta.md") < result.index("Zebra.md")


class TestRegexSearch:
    """Tests for regex search functionality in list_documentation."""

    @pytest.mark.asyncio
    async def test_simple_substring_search(self):
        """Test simple substring search (default behavior)."""
        from mcp_manticore.mcp_server import list_documentation

        with patch("mcp_manticore.mcp_server.list_documentation_files") as mock_list:
            mock_list.return_value = [
                "Searching/KNN.md",
                "Searching/Full_text_search.md",
                "Creating_a_table/Local_tables.md",
            ]

            result = await list_documentation(search="knn")
            assert "KNN.md" in result
            assert "Full_text_search.md" not in result

    @pytest.mark.asyncio
    async def test_regex_search_or_pattern(self):
        """Test regex search with OR pattern."""
        from mcp_manticore.mcp_server import list_documentation

        with patch("mcp_manticore.mcp_server.list_documentation_files") as mock_list:
            mock_list.return_value = [
                "Searching/KNN.md",
                "Searching/Full_text_search.md",
                "Creating_a_table/Local_tables.md",
            ]

            result = await list_documentation(search="knn|vector", use_regex=True)
            assert "KNN.md" in result
            assert "Full_text_search.md" not in result

    @pytest.mark.asyncio
    async def test_regex_search_anchored_pattern(self):
        """Test regex search with anchored pattern."""
        from mcp_manticore.mcp_server import list_documentation

        with patch("mcp_manticore.mcp_server.list_documentation_files") as mock_list:
            mock_list.return_value = [
                "Searching/KNN.md",
                "Searching/Full_text_search.md",
                "Creating_a_table/Local_tables.md",
            ]

            result = await list_documentation(search="^Searching/", use_regex=True)
            assert "KNN.md" in result
            assert "Full_text_search.md" in result
            assert "Local_tables.md" not in result

    @pytest.mark.asyncio
    async def test_regex_search_invalid_pattern(self):
        """Test regex search with invalid pattern."""
        from fastmcp.exceptions import ToolError

        from mcp_manticore.mcp_server import list_documentation

        with patch("mcp_manticore.mcp_server.list_documentation_files") as mock_list:
            mock_list.return_value = ["Searching/KNN.md"]

            with pytest.raises(ToolError, match="Invalid regex pattern"):
                await list_documentation(search="[invalid", use_regex=True)

    @pytest.mark.asyncio
    async def test_regex_search_case_insensitive(self):
        """Test that regex search is case-insensitive."""
        from mcp_manticore.mcp_server import list_documentation

        with patch("mcp_manticore.mcp_server.list_documentation_files") as mock_list:
            mock_list.return_value = [
                "Searching/KNN.md",
                "Searching/full_text_search.md",
            ]

            result = await list_documentation(search="KNN", use_regex=True)
            assert "KNN.md" in result

            result = await list_documentation(search="knn", use_regex=True)
            assert "KNN.md" in result
