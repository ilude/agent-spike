"""Tests for web search API router."""

import pytest
from unittest.mock import patch, MagicMock, AsyncMock

from fastapi.testclient import TestClient

from compose.api.main import app
from compose.services.websearch import SearchResponse, SearchResult


@pytest.fixture
def client():
    """Create test client."""
    return TestClient(app)


class TestSearchEndpoint:
    """Tests for GET /search."""

    def test_search_requires_query(self, client):
        """Test search requires query parameter."""
        response = client.get("/search")
        assert response.status_code == 422  # Validation error

    def test_search_returns_results(self, client):
        """Test search returns results."""
        mock_response = SearchResponse(
            results=[
                SearchResult(
                    title="Test Result",
                    url="https://example.com",
                    snippet="Test snippet",
                    source="duckduckgo",
                )
            ],
            query="test query",
            source="duckduckgo",
        )

        with patch(
            "compose.api.routers.websearch.get_search_service"
        ) as mock_get_service:
            mock_service = AsyncMock()
            mock_service.search.return_value = mock_response
            mock_get_service.return_value = mock_service

            response = client.get("/search?q=test+query")

            assert response.status_code == 200
            data = response.json()
            assert data["query"] == "test query"
            assert len(data["results"]) == 1
            assert data["results"][0]["title"] == "Test Result"

    def test_search_limits_num_results(self, client):
        """Test search respects num parameter."""
        mock_response = SearchResponse(results=[], query="test", source="duckduckgo")

        with patch(
            "compose.api.routers.websearch.get_search_service"
        ) as mock_get_service:
            mock_service = AsyncMock()
            mock_service.search.return_value = mock_response
            mock_get_service.return_value = mock_service

            response = client.get("/search?q=test&num=3")

            assert response.status_code == 200
            mock_service.search.assert_called_once_with("test", num_results=3)

    def test_search_validates_num_max(self, client):
        """Test search validates num <= 10."""
        response = client.get("/search?q=test&num=20")
        assert response.status_code == 422  # Validation error

    def test_search_validates_num_min(self, client):
        """Test search validates num >= 1."""
        response = client.get("/search?q=test&num=0")
        assert response.status_code == 422  # Validation error


class TestFreediumCheckEndpoint:
    """Tests for GET /search/freedium."""

    def test_freedium_check_medium_url(self, client):
        """Test Freedium check with Medium URL."""
        response = client.get(
            "/search/freedium?url=https://medium.com/article/test"
        )
        assert response.status_code == 200
        data = response.json()
        assert data["is_medium"] is True
        assert "freedium.cfd" in data["freedium_url"]

    def test_freedium_check_non_medium_url(self, client):
        """Test Freedium check with non-Medium URL."""
        response = client.get("/search/freedium?url=https://github.com/test")
        assert response.status_code == 200
        data = response.json()
        assert data["is_medium"] is False
        assert data["freedium_url"] == "https://github.com/test"

    def test_freedium_check_requires_url(self, client):
        """Test Freedium check requires URL."""
        response = client.get("/search/freedium")
        assert response.status_code == 422


class TestFreediumFetchEndpoint:
    """Tests for POST /search/freedium."""

    def test_freedium_fetch_medium_url(self, client):
        """Test Freedium fetch with Medium URL."""
        with patch(
            "compose.api.routers.websearch.get_freedium_service"
        ) as mock_get_service:
            mock_service = MagicMock()
            mock_service.is_medium_url.return_value = True
            mock_service.get_freedium_url.return_value = (
                "https://freedium.cfd/https://medium.com/test"
            )
            mock_service.fetch_article = AsyncMock(
                return_value="<html>Article</html>"
            )
            mock_get_service.return_value = mock_service

            response = client.post(
                "/search/freedium",
                json={"url": "https://medium.com/test"},
            )

            assert response.status_code == 200
            data = response.json()
            assert data["is_medium"] is True
            assert data["content"] == "<html>Article</html>"

    def test_freedium_fetch_non_medium_url(self, client):
        """Test Freedium fetch with non-Medium URL doesn't fetch."""
        with patch(
            "compose.api.routers.websearch.get_freedium_service"
        ) as mock_get_service:
            mock_service = MagicMock()
            mock_service.is_medium_url.return_value = False
            mock_get_service.return_value = mock_service

            response = client.post(
                "/search/freedium",
                json={"url": "https://github.com/test"},
            )

            assert response.status_code == 200
            data = response.json()
            assert data["is_medium"] is False
            assert data["content"] is None
            mock_service.fetch_article.assert_not_called()

    def test_freedium_fetch_handles_fetch_error(self, client):
        """Test Freedium fetch handles errors gracefully."""
        with patch(
            "compose.api.routers.websearch.get_freedium_service"
        ) as mock_get_service:
            mock_service = MagicMock()
            mock_service.is_medium_url.return_value = True
            mock_service.get_freedium_url.return_value = "https://freedium.cfd/test"
            mock_service.fetch_article = AsyncMock(return_value=None)
            mock_get_service.return_value = mock_service

            response = client.post(
                "/search/freedium",
                json={"url": "https://medium.com/test"},
            )

            assert response.status_code == 200
            data = response.json()
            assert data["content"] is None
