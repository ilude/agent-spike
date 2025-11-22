"""Tests for the web search service."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from compose.services.websearch import (
    FreediumService,
    SearchResponse,
    SearchResult,
    WebSearchService,
    get_freedium_service,
    get_search_service,
)


class TestSearchResult:
    """Tests for SearchResult model."""

    def test_search_result_creation(self):
        """Test creating a SearchResult."""
        result = SearchResult(
            title="Test Title",
            url="https://example.com",
            snippet="Test snippet",
        )
        assert result.title == "Test Title"
        assert result.url == "https://example.com"
        assert result.snippet == "Test snippet"
        assert result.source == "web"

    def test_search_result_with_source(self):
        """Test creating a SearchResult with custom source."""
        result = SearchResult(
            title="Test", url="https://test.com", snippet="Snippet", source="serper"
        )
        assert result.source == "serper"


class TestSearchResponse:
    """Tests for SearchResponse model."""

    def test_search_response_creation(self):
        """Test creating a SearchResponse."""
        results = [
            SearchResult(title="Result 1", url="https://1.com", snippet="S1"),
            SearchResult(title="Result 2", url="https://2.com", snippet="S2"),
        ]
        response = SearchResponse(results=results, query="test query", source="brave")
        assert len(response.results) == 2
        assert response.query == "test query"
        assert response.source == "brave"

    def test_search_response_empty(self):
        """Test creating empty SearchResponse."""
        response = SearchResponse(results=[], query="no results", source="duckduckgo")
        assert response.results == []


class TestWebSearchService:
    """Tests for WebSearchService class."""

    @pytest.fixture
    def service(self):
        """Create a search service."""
        return WebSearchService()

    @pytest.mark.asyncio
    @patch("httpx.AsyncClient")
    async def test_search_serper(self, mock_client_class, service):
        """Test search using Serper API."""
        service.serper_key = "test-key"

        mock_response = MagicMock()
        mock_response.raise_for_status = MagicMock()
        mock_response.json.return_value = {
            "organic": [
                {
                    "title": "Test Result",
                    "link": "https://example.com",
                    "snippet": "Test snippet",
                }
            ]
        }

        mock_client = AsyncMock()
        mock_client.post.return_value = mock_response
        mock_client.__aenter__.return_value = mock_client
        mock_client.__aexit__.return_value = None
        mock_client_class.return_value = mock_client

        result = await service._search_serper("test query", 5, 10.0)

        assert result.source == "serper"
        assert len(result.results) == 1
        assert result.results[0].title == "Test Result"

    @pytest.mark.asyncio
    @patch("httpx.AsyncClient")
    async def test_search_brave(self, mock_client_class, service):
        """Test search using Brave API."""
        service.brave_key = "test-key"

        mock_response = MagicMock()
        mock_response.raise_for_status = MagicMock()
        mock_response.json.return_value = {
            "web": {
                "results": [
                    {
                        "title": "Brave Result",
                        "url": "https://brave.com",
                        "description": "Brave snippet",
                    }
                ]
            }
        }

        mock_client = AsyncMock()
        mock_client.get.return_value = mock_response
        mock_client.__aenter__.return_value = mock_client
        mock_client.__aexit__.return_value = None
        mock_client_class.return_value = mock_client

        result = await service._search_brave("test query", 5, 10.0)

        assert result.source == "brave"
        assert len(result.results) == 1
        assert result.results[0].title == "Brave Result"

    @pytest.mark.asyncio
    @patch("httpx.AsyncClient")
    async def test_search_duckduckgo(self, mock_client_class, service):
        """Test search using DuckDuckGo scraping."""
        mock_response = MagicMock()
        mock_response.raise_for_status = MagicMock()
        mock_response.text = """
        <a rel="nofollow" class="result__a" href="https://duck.com">Duck Result</a>
        <a class="result__snippet">Duck snippet</a>
        """

        mock_client = AsyncMock()
        mock_client.get.return_value = mock_response
        mock_client.__aenter__.return_value = mock_client
        mock_client.__aexit__.return_value = None
        mock_client_class.return_value = mock_client

        result = await service._search_duckduckgo("test query", 5, 10.0)

        assert result.source == "duckduckgo"
        assert result.query == "test query"

    @pytest.mark.asyncio
    @patch("httpx.AsyncClient")
    async def test_search_fallback_order(self, mock_client_class, service):
        """Test that search falls back correctly."""
        service.serper_key = ""  # No Serper
        service.brave_key = ""  # No Brave

        mock_response = MagicMock()
        mock_response.raise_for_status = MagicMock()
        mock_response.text = ""  # Empty response

        mock_client = AsyncMock()
        mock_client.get.return_value = mock_response
        mock_client.__aenter__.return_value = mock_client
        mock_client.__aexit__.return_value = None
        mock_client_class.return_value = mock_client

        result = await service.search("test query", 5)

        # Should fall back to DuckDuckGo
        assert result.source == "duckduckgo"

    @pytest.mark.asyncio
    @patch("httpx.AsyncClient")
    async def test_search_limits_results(self, mock_client_class, service):
        """Test that search limits results to max 10."""
        service.serper_key = "test-key"

        mock_response = MagicMock()
        mock_response.raise_for_status = MagicMock()
        mock_response.json.return_value = {"organic": []}

        mock_client = AsyncMock()
        mock_client.post.return_value = mock_response
        mock_client.__aenter__.return_value = mock_client
        mock_client.__aexit__.return_value = None
        mock_client_class.return_value = mock_client

        # Request 20 results, should be limited to 10
        await service.search("test", num_results=20)

        # Check that API was called with num=10
        call_args = mock_client.post.call_args
        assert call_args[1]["json"]["num"] == 10


class TestFreediumService:
    """Tests for FreediumService class."""

    @pytest.fixture
    def service(self):
        """Create a Freedium service."""
        return FreediumService()

    def test_is_medium_url_medium_com(self, service):
        """Test detection of medium.com URLs."""
        assert service.is_medium_url("https://medium.com/article/test")
        assert service.is_medium_url("https://www.medium.com/article/test")
        assert service.is_medium_url("https://user.medium.com/article/test")

    def test_is_medium_url_publications(self, service):
        """Test detection of Medium publication URLs."""
        assert service.is_medium_url("https://towardsdatascience.com/article")
        assert service.is_medium_url("https://levelup.gitconnected.com/article")
        assert service.is_medium_url("https://betterprogramming.pub/article")

    def test_is_medium_url_false(self, service):
        """Test non-Medium URLs return False."""
        assert not service.is_medium_url("https://google.com")
        assert not service.is_medium_url("https://github.com")
        assert not service.is_medium_url("https://example.com/medium")

    def test_get_freedium_url(self, service):
        """Test Freedium URL generation."""
        medium_url = "https://medium.com/article/test-article-123"
        freedium_url = service.get_freedium_url(medium_url)
        assert freedium_url == f"https://freedium.cfd/{medium_url}"

    @pytest.mark.asyncio
    @patch("httpx.AsyncClient")
    async def test_fetch_article_success(self, mock_client_class, service):
        """Test successful article fetch."""
        mock_response = MagicMock()
        mock_response.raise_for_status = MagicMock()
        mock_response.text = "<html>Article content</html>"

        mock_client = AsyncMock()
        mock_client.get.return_value = mock_response
        mock_client.__aenter__.return_value = mock_client
        mock_client.__aexit__.return_value = None
        mock_client_class.return_value = mock_client

        result = await service.fetch_article("https://medium.com/test")

        assert result == "<html>Article content</html>"

    @pytest.mark.asyncio
    @patch("httpx.AsyncClient")
    async def test_fetch_article_failure(self, mock_client_class, service):
        """Test article fetch handles errors."""
        mock_client = AsyncMock()
        mock_client.get.side_effect = Exception("Network error")
        mock_client.__aenter__.return_value = mock_client
        mock_client.__aexit__.return_value = None
        mock_client_class.return_value = mock_client

        result = await service.fetch_article("https://medium.com/test")

        assert result is None


class TestSingletons:
    """Tests for singleton instances."""

    def test_get_search_service_returns_instance(self):
        """Test get_search_service returns WebSearchService."""
        import compose.services.websearch as module

        module._search_service = None

        service = get_search_service()
        assert isinstance(service, WebSearchService)

    def test_get_search_service_returns_same_instance(self):
        """Test get_search_service returns same instance."""
        import compose.services.websearch as module

        module._search_service = None

        service1 = get_search_service()
        service2 = get_search_service()
        assert service1 is service2

    def test_get_freedium_service_returns_instance(self):
        """Test get_freedium_service returns FreediumService."""
        import compose.services.websearch as module

        module._freedium_service = None

        service = get_freedium_service()
        assert isinstance(service, FreediumService)

    def test_get_freedium_service_returns_same_instance(self):
        """Test get_freedium_service returns same instance."""
        import compose.services.websearch as module

        module._freedium_service = None

        service1 = get_freedium_service()
        service2 = get_freedium_service()
        assert service1 is service2
