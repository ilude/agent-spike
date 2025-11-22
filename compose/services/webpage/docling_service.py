"""Webpage fetching and parsing using Docling HTTP API."""

import hashlib
import os
from typing import Any, Optional, Protocol

import httpx


class CacheManager(Protocol):
    """Cache interface for dependency injection."""

    def get(self, key: str) -> Optional[dict[str, Any]]:
        """Retrieve cached data by key"""
        ...

    def set(
        self, key: str, value: dict[str, Any], metadata: Optional[dict[str, Any]] = None
    ) -> None:
        """Store data with optional metadata"""
        ...

    def exists(self, key: str) -> bool:
        """Check if key exists in cache"""
        ...


def fetch_webpage(
    url: str,
    cache: Optional[CacheManager] = None,
    max_chars: int = 15000,
) -> str:
    """Fetch webpage content and convert to clean Markdown using docling-serve API.

    Uses Docling HTTP API to:
    - Download HTML content
    - Parse and extract main content
    - Strip navigation, ads, and UI elements
    - Convert to Markdown format

    Args:
        url: Webpage URL
        cache: Optional cache manager for storing/retrieving webpage content
        max_chars: Maximum characters to return (default 15000)

    Returns:
        Clean Markdown content or error message prefixed with "ERROR:"
    """
    try:
        url_hash = hashlib.sha256(url.encode()).hexdigest()[:16]
        cache_key = f"webpage:content:{url_hash}"

        if cache and cache.exists(cache_key):
            cached = cache.get(cache_key)
            if cached and "markdown" in cached:
                return cached["markdown"]

        docling_url = os.getenv("DOCLING_URL", "http://localhost:5001")
        endpoint = f"{docling_url}/v1/convert/source"

        response = httpx.post(
            endpoint,
            json={"sources": [{"kind": "http", "url": url}]},
            timeout=30.0,
        )
        response.raise_for_status()

        data = response.json()

        if data.get("status") != "success":
            errors = data.get("errors", [])
            return f"ERROR: Docling conversion failed - {errors}"

        markdown = data["document"]["md_content"]

        if len(markdown.strip()) < 100:
            return "ERROR: Page content too short - may be behind paywall or empty page"

        truncated = False
        if len(markdown) > max_chars:
            markdown = markdown[:max_chars] + "\n\n[Content truncated for analysis...]"
            truncated = True

        if cache:
            cache.set(
                cache_key,
                {
                    "markdown": markdown,
                    "url": url,
                    "length": len(markdown),
                    "truncated": truncated,
                },
                metadata={"type": "webpage_content", "source": "docling-serve"},
            )

        return markdown

    except httpx.HTTPStatusError as e:
        return f"ERROR: Docling service returned {e.response.status_code} - {e.response.text}"
    except httpx.ConnectError:
        return "ERROR: Cannot connect to docling service - ensure docling-serve is running"
    except httpx.TimeoutException:
        return "ERROR: Docling service timeout - page took too long to convert"
    except httpx.HTTPError as e:
        return f"ERROR: HTTP error connecting to docling service - {e}"
    except KeyError as e:
        return f"ERROR: Unexpected response format from docling service - missing {e}"
    except Exception as e:
        error_msg = str(e)
        if "404" in error_msg:
            return "ERROR: Page not found (404)"
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
    if not url.startswith(("http://", "https://")):
        return {"error": "URL must start with http:// or https://"}

    url_hash = hashlib.sha256(url.encode()).hexdigest()[:16]
    cache_key = f"webpage:info:{url_hash}"

    if cache and cache.exists(cache_key):
        cached = cache.get(cache_key)
        if cached:
            return cached

    info = {
        "url": url,
        "protocol": "https" if url.startswith("https") else "http",
    }

    if cache:
        cache.set(cache_key, info, metadata={"type": "webpage_info"})

    return info
