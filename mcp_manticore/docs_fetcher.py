"""Documentation fetcher for Manticore Search manual."""

import logging
import os

import httpx

logger = logging.getLogger(__name__)

# GitHub API and raw content URLs
GITHUB_API_URL = (
    "https://api.github.com/repos/manticoresoftware/manticoresearch/contents/manual/english"
)
DOCS_BASE_URL = (
    "https://raw.githubusercontent.com/manticoresoftware/manticoresearch/master/manual/english/"
)

# Cache for documentation files list and content
_docs_cache: list[str] | None = None
_content_cache: dict[str, str] = {}  # file_path -> content

# GitHub token (optional, increases rate limit from 60 to 5000 requests/hour)
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")


def _get_github_headers() -> dict[str, str]:
    """Get headers for GitHub API requests."""
    headers = {"Accept": "application/vnd.github.v3+json"}
    if GITHUB_TOKEN:
        headers["Authorization"] = f"token {GITHUB_TOKEN}"
    return headers


async def list_documentation_files() -> list[str]:
    """List all available documentation files from GitHub API.

    Uses GitHub API to fetch directory listing.
    - Without token: 60 requests/hour per IP
    - With GITHUB_TOKEN env var: 5000 requests/hour

    Results are cached in memory to minimize API calls.

    Returns:
        List of documentation file paths
    """
    global _docs_cache

    if _docs_cache is not None:
        return _docs_cache

    files = []
    headers = _get_github_headers()

    async with httpx.AsyncClient(timeout=30.0) as client:
        # Fetch root directory
        response = await client.get(GITHUB_API_URL, headers=headers)
        response.raise_for_status()
        items = response.json()

        for item in items:
            if item["type"] == "file" and item["name"].endswith(".md"):
                files.append(item["name"])
            elif item["type"] == "dir":
                # Fetch subdirectory
                subdir_url = f"{GITHUB_API_URL}/{item['name']}"
                subdir_response = await client.get(subdir_url, headers=headers)
                if subdir_response.status_code == 200:
                    subdir_items = subdir_response.json()
                    for subitem in subdir_items:
                        if subitem["type"] == "file" and subitem["name"].endswith(".md"):
                            files.append(f"{item['name']}/{subitem['name']}")
                        elif subitem["type"] == "dir":
                            # Fetch sub-subdirectory (e.g., Creating_a_table/Local_tables/)
                            subsubdir_url = f"{GITHUB_API_URL}/{item['name']}/{subitem['name']}"
                            subsubdir_response = await client.get(subsubdir_url, headers=headers)
                            if subsubdir_response.status_code == 200:
                                subsubdir_items = subsubdir_response.json()
                                for subsubitem in subsubdir_items:
                                    if subsubitem["type"] == "file" and subsubitem["name"].endswith(
                                        ".md"
                                    ):
                                        files.append(
                                            f"{item['name']}/{subitem['name']}/{subsubitem['name']}"
                                        )

    _docs_cache = sorted(files)
    logger.info(f"Cached {len(files)} documentation files from GitHub")
    return _docs_cache


def format_doc_list(files: list[str]) -> str:
    """Format the list of documentation files for display.

    Args:
        files: List of file paths

    Returns:
        Formatted string grouped by directory
    """
    # Group by directory
    grouped = {}
    for doc in files:
        if "/" in doc:
            category = doc.split("/")[0]
            if category not in grouped:
                grouped[category] = []
            grouped[category].append(doc)
        else:
            if "Root" not in grouped:
                grouped["Root"] = []
            grouped["Root"].append(doc)

    result = []
    for category in sorted(grouped.keys()):
        if category != "Root":
            result.append(f"\n{category}:")
        for doc in sorted(grouped[category]):
            result.append(f"  - {doc}")

    return "\n".join(result)


async def fetch_documentation(
    file_path: str, content: str | None = None, before: int = 0, after: int = 0
) -> str:
    """Fetch documentation file from GitHub with caching.

    Args:
        file_path: Path to documentation file (e.g., "Searching/KNN.md")
        content: Optional search term to filter content
        before: Number of lines before match to include (default: 0)
        after: Number of lines after match to include (default: 0)

    Returns:
        Documentation content as markdown text

    Raises:
        ValueError: If file_path is not in the available documentation list
        httpx.HTTPError: If fetching fails
    "
    """
    # Get available files and validate
    available_docs = await list_documentation_files()

    if file_path not in available_docs:
        available = format_doc_list(available_docs)
        raise ValueError(
            f"Documentation file '{file_path}' not found.\n\n"
            f"Available documentation files:\n{available}"
        )

    # Check cache first
    if file_path in _content_cache:
        logger.debug(f"Cache hit for {file_path}")
        full_content = _content_cache[file_path]
    else:
        # Fetch from GitHub
        url = f"{DOCS_BASE_URL}{file_path}"
        logger.debug(f"Fetching {url} from GitHub")

        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(url)
            response.raise_for_status()
            full_content = response.text

        # Cache the content
        _content_cache[file_path] = full_content
        logger.debug(f"Cached {file_path} ({len(full_content)} bytes)")

    # If no content filter, return full content
    if not content:
        return full_content

    # Filter by content search term
    lines = full_content.split("\n")
    result_lines = []

    for i, line in enumerate(lines):
        if content.lower() in line.lower():
            # Calculate range
            start = max(0, i - before)
            end = min(len(lines), i + after + 1)

            # Add separator if not first match
            if result_lines:
                result_lines.append("\n---\n")

            # Add context lines
            for j in range(start, end):
                result_lines.append(lines[j])

    if not result_lines:
        return f"No matches found for '{content}' in {file_path}"

    return "\n".join(result_lines)
