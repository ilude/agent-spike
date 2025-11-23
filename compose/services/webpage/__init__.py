"""Webpage service for fetching and parsing web content using Docling.

This module provides:
- fetch_webpage: Fetch webpage content as clean Markdown via docling-serve
- get_page_info: Get basic information about a webpage URL

Example:
    >>> from compose.services.webpage import fetch_webpage
    >>> markdown = fetch_webpage("https://example.com/article")
    >>> print(markdown[:100])
"""

from .docling_service import fetch_webpage, get_page_info

__all__ = [
    "fetch_webpage",
    "get_page_info",
]
