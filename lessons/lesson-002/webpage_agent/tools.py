"""Webpage fetching and parsing tools using Docling."""

from typing import Any
from docling.document_converter import DocumentConverter


def fetch_webpage(url: str) -> str:
    """Fetch webpage content and convert to clean Markdown.

    Uses Docling to:
    - Download HTML content
    - Parse and extract main content
    - Strip navigation, ads, and UI elements
    - Convert to Markdown format
    - Truncate to ~15k chars for cost control

    Args:
        url: Webpage URL

    Returns:
        Clean Markdown content or error message
    """
    try:
        # Create converter with default settings
        converter = DocumentConverter()

        # Fetch and convert to Markdown
        result = converter.convert(url)
        markdown = result.document.export_to_markdown()

        # Check if content is too short (likely error/paywall)
        if len(markdown.strip()) < 100:
            return "ERROR: Page content too short - may be behind paywall or empty page"

        # Truncate for cost control (15k chars ~= 3750 words)
        max_chars = 15000
        if len(markdown) > max_chars:
            markdown = markdown[:max_chars] + "\n\n[Content truncated for analysis...]"

        return markdown

    except Exception as e:
        error_msg = str(e)
        # Provide helpful error messages
        if "404" in error_msg:
            return "ERROR: Page not found (404)"
        elif "timeout" in error_msg.lower():
            return "ERROR: Connection timeout - page took too long to respond"
        elif "connection" in error_msg.lower():
            return "ERROR: Connection failed - check URL or network"
        else:
            return f"ERROR: Failed to fetch page - {error_msg}"


def get_page_info(url: str) -> dict[str, Any]:
    """Get basic information about a webpage URL.

    Args:
        url: Webpage URL

    Returns:
        Dictionary with URL validation info
    """
    # Basic URL validation
    if not url.startswith(("http://", "https://")):
        return {"error": "URL must start with http:// or https://"}

    return {
        "url": url,
        "protocol": "https" if url.startswith("https") else "http",
        "note": "Use fetch_webpage() to get content"
    }
