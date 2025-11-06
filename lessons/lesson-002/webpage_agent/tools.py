"""Webpage fetching and parsing tools using Docling."""

import hashlib
from typing import Any, Optional, Protocol
from docling.document_converter import DocumentConverter


class CacheManager(Protocol):
    """Cache interface for dependency injection.

    Actual implementation will be in lesson-007.
    This allows tools to optionally use caching without hard dependencies.
    """

    def get(self, key: str) -> Optional[dict[str, Any]]:
        """Retrieve cached data by key"""
        ...

    def set(self, key: str, value: dict[str, Any], metadata: Optional[dict[str, Any]] = None) -> None:
        """Store data with optional metadata"""
        ...

    def exists(self, key: str) -> bool:
        """Check if key exists in cache"""
        ...


def fetch_webpage(url: str, cache: Optional[CacheManager] = None) -> str:
    """Fetch webpage content and convert to clean Markdown.

    Uses Docling to:
    - Download HTML content
    - Parse and extract main content
    - Strip navigation, ads, and UI elements
    - Convert to Markdown format
    - Truncate to ~15k chars for cost control

    Args:
        url: Webpage URL
        cache: Optional cache manager for storing/retrieving webpage content

    Returns:
        Clean Markdown content or error message
    """
    try:
        # Try cache first if available
        # Use hash of URL as key since URLs can be very long
        url_hash = hashlib.sha256(url.encode()).hexdigest()[:16]
        cache_key = f"webpage:content:{url_hash}"

        if cache and cache.exists(cache_key):
            cached = cache.get(cache_key)
            if cached and "markdown" in cached:
                return cached["markdown"]

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
        truncated = False
        if len(markdown) > max_chars:
            markdown = markdown[:max_chars] + "\n\n[Content truncated for analysis...]"
            truncated = True

        # Store in cache if available
        if cache:
            cache.set(
                cache_key,
                {
                    "markdown": markdown,
                    "url": url,
                    "length": len(markdown),
                    "truncated": truncated
                },
                metadata={"type": "webpage_content", "source": "docling"}
            )

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


def get_page_info(url: str, cache: Optional[CacheManager] = None) -> dict[str, Any]:
    """Get basic information about a webpage URL.

    Args:
        url: Webpage URL
        cache: Optional cache manager for storing/retrieving page info

    Returns:
        Dictionary with URL validation info
    """
    # Basic URL validation
    if not url.startswith(("http://", "https://")):
        return {"error": "URL must start with http:// or https://"}

    # Try cache first if available
    url_hash = hashlib.sha256(url.encode()).hexdigest()[:16]
    cache_key = f"webpage:info:{url_hash}"

    if cache and cache.exists(cache_key):
        cached = cache.get(cache_key)
        if cached:
            return cached

    # Create page info
    info = {
        "url": url,
        "protocol": "https" if url.startswith("https") else "http",
        "note": "Use fetch_webpage() to get content"
    }

    # Store in cache if available
    if cache:
        cache.set(cache_key, info, metadata={"type": "webpage_info"})

    return info
