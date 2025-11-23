"""Web search service for real-time information retrieval.

Supports multiple search backends (Serper, Brave, or fallback to DuckDuckGo).
Also includes Freedium integration for accessing paywalled Medium articles.
"""

import json
import os
import re
from typing import Optional

import httpx
from pydantic import BaseModel, Field


# Configuration
SERPER_API_KEY = os.getenv("SERPER_API_KEY", "")
BRAVE_API_KEY = os.getenv("BRAVE_API_KEY", "")
FREEDIUM_URL = "https://freedium.cfd"


class SearchResult(BaseModel):
    """A single search result."""

    title: str
    url: str
    snippet: str
    source: str = "web"


class SearchResponse(BaseModel):
    """Response from web search."""

    results: list[SearchResult] = Field(default_factory=list)
    query: str
    source: str  # Which search backend was used


class WebSearchService:
    """Service for performing web searches."""

    def __init__(self):
        """Initialize the search service."""
        self.serper_key = SERPER_API_KEY
        self.brave_key = BRAVE_API_KEY

    async def search(
        self, query: str, num_results: int = 5, timeout: float = 10.0
    ) -> SearchResponse:
        """Perform a web search.

        Tries backends in order: Serper > Brave > DuckDuckGo

        Args:
            query: Search query
            num_results: Number of results to return (max 10)
            timeout: Request timeout in seconds

        Returns:
            SearchResponse with results
        """
        num_results = min(num_results, 10)

        # Try Serper first (best results)
        if self.serper_key:
            try:
                return await self._search_serper(query, num_results, timeout)
            except Exception as e:
                print(f"Serper search failed: {e}")

        # Try Brave next
        if self.brave_key:
            try:
                return await self._search_brave(query, num_results, timeout)
            except Exception as e:
                print(f"Brave search failed: {e}")

        # Fallback to DuckDuckGo (no API key needed)
        return await self._search_duckduckgo(query, num_results, timeout)

    async def _search_serper(
        self, query: str, num_results: int, timeout: float
    ) -> SearchResponse:
        """Search using Serper API (Google results)."""
        async with httpx.AsyncClient(timeout=timeout) as client:
            response = await client.post(
                "https://google.serper.dev/search",
                headers={
                    "X-API-KEY": self.serper_key,
                    "Content-Type": "application/json",
                },
                json={"q": query, "num": num_results},
            )
            response.raise_for_status()
            data = response.json()

        results = []
        for item in data.get("organic", [])[:num_results]:
            results.append(
                SearchResult(
                    title=item.get("title", ""),
                    url=item.get("link", ""),
                    snippet=item.get("snippet", ""),
                    source="serper",
                )
            )

        return SearchResponse(results=results, query=query, source="serper")

    async def _search_brave(
        self, query: str, num_results: int, timeout: float
    ) -> SearchResponse:
        """Search using Brave Search API."""
        async with httpx.AsyncClient(timeout=timeout) as client:
            response = await client.get(
                "https://api.search.brave.com/res/v1/web/search",
                headers={
                    "X-Subscription-Token": self.brave_key,
                    "Accept": "application/json",
                },
                params={"q": query, "count": num_results},
            )
            response.raise_for_status()
            data = response.json()

        results = []
        for item in data.get("web", {}).get("results", [])[:num_results]:
            results.append(
                SearchResult(
                    title=item.get("title", ""),
                    url=item.get("url", ""),
                    snippet=item.get("description", ""),
                    source="brave",
                )
            )

        return SearchResponse(results=results, query=query, source="brave")

    async def _search_duckduckgo(
        self, query: str, num_results: int, timeout: float
    ) -> SearchResponse:
        """Search using DuckDuckGo HTML scraping (fallback, no API needed)."""
        # Use DuckDuckGo HTML search (no API key needed)
        async with httpx.AsyncClient(timeout=timeout) as client:
            response = await client.get(
                "https://html.duckduckgo.com/html/",
                params={"q": query},
                headers={
                    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
                },
            )
            response.raise_for_status()
            html = response.text

        # Simple regex extraction (not perfect but works without dependencies)
        results = []
        # Match result blocks
        pattern = r'<a rel="nofollow" class="result__a" href="([^"]+)"[^>]*>([^<]+)</a>.*?<a class="result__snippet"[^>]*>([^<]+)</a>'
        matches = re.findall(pattern, html, re.DOTALL)

        for url, title, snippet in matches[:num_results]:
            results.append(
                SearchResult(
                    title=title.strip(),
                    url=url.strip(),
                    snippet=snippet.strip(),
                    source="duckduckgo",
                )
            )

        return SearchResponse(results=results, query=query, source="duckduckgo")


class FreediumService:
    """Service for accessing paywalled Medium content via Freedium."""

    def __init__(self):
        """Initialize Freedium service."""
        self.base_url = FREEDIUM_URL

    def is_medium_url(self, url: str) -> bool:
        """Check if URL is a Medium article.

        Args:
            url: URL to check

        Returns:
            True if URL is a Medium article
        """
        medium_patterns = [
            r"medium\.com",
            r"[a-z]+\.medium\.com",  # Subdomains
            r"towardsdatascience\.com",
            r"levelup\.gitconnected\.com",
            r"betterprogramming\.pub",
            r"javascript\.plainenglish\.io",
        ]
        for pattern in medium_patterns:
            if re.search(pattern, url, re.IGNORECASE):
                return True
        return False

    def get_freedium_url(self, medium_url: str) -> str:
        """Convert Medium URL to Freedium URL.

        Args:
            medium_url: Original Medium URL

        Returns:
            Freedium URL that bypasses paywall
        """
        # Freedium uses the path from the medium URL
        return f"{self.base_url}/{medium_url}"

    async def fetch_article(
        self, medium_url: str, timeout: float = 15.0
    ) -> Optional[str]:
        """Fetch article content via Freedium.

        Args:
            medium_url: Original Medium URL
            timeout: Request timeout

        Returns:
            Article HTML content or None if failed
        """
        freedium_url = self.get_freedium_url(medium_url)

        try:
            async with httpx.AsyncClient(timeout=timeout) as client:
                response = await client.get(
                    freedium_url,
                    headers={
                        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
                    },
                    follow_redirects=True,
                )
                response.raise_for_status()
                return response.text
        except Exception as e:
            print(f"Freedium fetch failed: {e}")
            return None


# Singleton instances
_search_service: Optional[WebSearchService] = None
_freedium_service: Optional[FreediumService] = None


def get_search_service() -> WebSearchService:
    """Get or create the search service singleton."""
    global _search_service
    if _search_service is None:
        _search_service = WebSearchService()
    return _search_service


def get_freedium_service() -> FreediumService:
    """Get or create the Freedium service singleton."""
    global _freedium_service
    if _freedium_service is None:
        _freedium_service = FreediumService()
    return _freedium_service
