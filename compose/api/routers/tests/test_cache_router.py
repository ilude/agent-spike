"""Tests for cache router.

Run with: uv run pytest compose/api/routers/tests/test_cache_router.py
"""

import pytest
from unittest.mock import patch, MagicMock
from fastapi import HTTPException
from pydantic import ValidationError

from compose.api.models import CacheSearchRequest, CacheSearchResponse, CacheSearchResult
from compose.api.routers.cache import router, search_cache, get_cached_item


# -----------------------------------------------------------------------------
# CacheSearchRequest Model Tests
# -----------------------------------------------------------------------------


@pytest.mark.unit
class TestCacheSearchRequestModel:
    """Test CacheSearchRequest Pydantic model."""

    def test_required_query_field(self):
        """query is required."""
        with pytest.raises(ValidationError) as exc_info:
            CacheSearchRequest()
        errors = exc_info.value.errors()
        assert any(e["loc"] == ("query",) and e["type"] == "missing" for e in errors)

    def test_valid_request_with_query_only(self):
        """Request with only query uses defaults."""
        req = CacheSearchRequest(query="test query")
        assert req.query == "test query"
        assert req.limit == 5  # default value
        assert req.filters is None  # default value

    def test_limit_default(self):
        """Default limit is 5."""
        req = CacheSearchRequest(query="test")
        assert req.limit == 5

    def test_limit_valid_range(self):
        """limit accepts values between 1 and 100."""
        req_min = CacheSearchRequest(query="test", limit=1)
        assert req_min.limit == 1

        req_max = CacheSearchRequest(query="test", limit=100)
        assert req_max.limit == 100

        req_mid = CacheSearchRequest(query="test", limit=50)
        assert req_mid.limit == 50

    def test_limit_below_minimum(self):
        """limit rejects values below 1."""
        with pytest.raises(ValidationError) as exc_info:
            CacheSearchRequest(query="test", limit=0)
        errors = exc_info.value.errors()
        assert any(e["loc"] == ("limit",) for e in errors)

    def test_limit_above_maximum(self):
        """limit rejects values above 100."""
        with pytest.raises(ValidationError) as exc_info:
            CacheSearchRequest(query="test", limit=101)
        errors = exc_info.value.errors()
        assert any(e["loc"] == ("limit",) for e in errors)

    def test_filters_optional(self):
        """filters is optional and defaults to None."""
        req = CacheSearchRequest(query="test")
        assert req.filters is None

    def test_filters_accepts_dict(self):
        """filters accepts arbitrary dict."""
        req = CacheSearchRequest(
            query="test",
            filters={"type": "video", "year": 2024},
        )
        assert req.filters == {"type": "video", "year": 2024}

    def test_model_fields(self):
        """Verify model has exactly the expected fields."""
        expected_fields = {"query", "limit", "filters"}
        actual_fields = set(CacheSearchRequest.model_fields.keys())
        assert actual_fields == expected_fields


# -----------------------------------------------------------------------------
# CacheSearchResult Model Tests
# -----------------------------------------------------------------------------


@pytest.mark.unit
class TestCacheSearchResultModel:
    """Test CacheSearchResult Pydantic model."""

    def test_required_fields(self):
        """video_id and score are required."""
        with pytest.raises(ValidationError) as exc_info:
            CacheSearchResult()
        errors = exc_info.value.errors()
        error_locs = {e["loc"][0] for e in errors}
        assert "video_id" in error_locs
        assert "score" in error_locs

    def test_valid_result_minimal(self):
        """Result with required fields and default optionals."""
        result = CacheSearchResult(video_id="abc123def45", score=0.95)
        assert result.video_id == "abc123def45"
        assert result.score == 0.95
        assert result.title is None
        assert result.summary is None
        assert result.tags is None
        assert result.url is None

    def test_valid_result_full(self):
        """Result with all fields."""
        result = CacheSearchResult(
            video_id="abc123def45",
            score=0.95,
            title="Test Video",
            summary="A test video summary",
            tags=["python", "testing"],
            url="https://youtube.com/watch?v=abc123def45",
        )
        assert result.video_id == "abc123def45"
        assert result.score == 0.95
        assert result.title == "Test Video"
        assert result.summary == "A test video summary"
        assert result.tags == ["python", "testing"]
        assert result.url == "https://youtube.com/watch?v=abc123def45"

    def test_model_fields(self):
        """Verify model has exactly the expected fields."""
        expected_fields = {"video_id", "score", "title", "summary", "tags", "url"}
        actual_fields = set(CacheSearchResult.model_fields.keys())
        assert actual_fields == expected_fields


# -----------------------------------------------------------------------------
# CacheSearchResponse Model Tests
# -----------------------------------------------------------------------------


@pytest.mark.unit
class TestCacheSearchResponseModel:
    """Test CacheSearchResponse Pydantic model."""

    def test_required_fields(self):
        """query, results, and total_found are required."""
        with pytest.raises(ValidationError) as exc_info:
            CacheSearchResponse()
        errors = exc_info.value.errors()
        error_locs = {e["loc"][0] for e in errors}
        assert "query" in error_locs
        assert "results" in error_locs
        assert "total_found" in error_locs

    def test_valid_response_empty_results(self):
        """Response with empty results list."""
        resp = CacheSearchResponse(query="test", results=[], total_found=0)
        assert resp.query == "test"
        assert resp.results == []
        assert resp.total_found == 0

    def test_valid_response_with_results(self):
        """Response with results."""
        results = [
            CacheSearchResult(video_id="abc123def45", score=0.95),
            CacheSearchResult(video_id="xyz789abc12", score=0.87),
        ]
        resp = CacheSearchResponse(query="test", results=results, total_found=2)
        assert resp.query == "test"
        assert len(resp.results) == 2
        assert resp.total_found == 2
        assert resp.results[0].video_id == "abc123def45"

    def test_model_fields(self):
        """Verify model has exactly the expected fields."""
        expected_fields = {"query", "results", "total_found"}
        actual_fields = set(CacheSearchResponse.model_fields.keys())
        assert actual_fields == expected_fields


# -----------------------------------------------------------------------------
# Search Endpoint Tests
# -----------------------------------------------------------------------------


@pytest.mark.unit
class TestSearchCacheEndpoint:
    """Test POST /search endpoint behavior."""

    @pytest.mark.asyncio
    async def test_search_returns_results(self):
        """Search returns formatted results from cache."""
        mock_cache = MagicMock()
        mock_cache.search.return_value = [
            {
                "payload": {
                    "video_id": "abc123def45",
                    "title": "Test Video",
                    "summary": "A summary",
                    "tags": ["python"],
                    "url": "https://youtube.com/watch?v=abc123def45",
                },
                "score": 0.95,
            },
            {
                "payload": {
                    "video_id": "xyz789abc12",
                    "title": "Another Video",
                    "summary": "Another summary",
                    "tags": ["testing"],
                    "url": "https://youtube.com/watch?v=xyz789abc12",
                },
                "score": 0.87,
            },
        ]

        with patch(
            "compose.api.routers.cache.create_in_memory_cache", return_value=mock_cache
        ):
            request = CacheSearchRequest(query="python tutorials", limit=10)
            response = await search_cache(request)

        assert response.query == "python tutorials"
        assert response.total_found == 2
        assert len(response.results) == 2
        assert response.results[0].video_id == "abc123def45"
        assert response.results[0].score == 0.95
        assert response.results[0].title == "Test Video"
        assert response.results[1].video_id == "xyz789abc12"
        assert response.results[1].score == 0.87

        mock_cache.search.assert_called_once_with(
            query="python tutorials",
            limit=10,
            filters={},
        )

    @pytest.mark.asyncio
    async def test_search_with_filters(self):
        """Search passes filters to cache."""
        mock_cache = MagicMock()
        mock_cache.search.return_value = []

        with patch(
            "compose.api.routers.cache.create_in_memory_cache", return_value=mock_cache
        ):
            request = CacheSearchRequest(
                query="test", limit=5, filters={"type": "video"}
            )
            response = await search_cache(request)

        mock_cache.search.assert_called_once_with(
            query="test",
            limit=5,
            filters={"type": "video"},
        )
        assert response.total_found == 0
        assert response.results == []

    @pytest.mark.asyncio
    async def test_search_empty_results(self):
        """Search returns empty results when nothing found."""
        mock_cache = MagicMock()
        mock_cache.search.return_value = []

        with patch(
            "compose.api.routers.cache.create_in_memory_cache", return_value=mock_cache
        ):
            request = CacheSearchRequest(query="nonexistent")
            response = await search_cache(request)

        assert response.query == "nonexistent"
        assert response.total_found == 0
        assert response.results == []

    @pytest.mark.asyncio
    async def test_search_handles_missing_payload_fields(self):
        """Search handles results with missing payload fields gracefully."""
        mock_cache = MagicMock()
        mock_cache.search.return_value = [
            {
                "payload": {"video_id": "abc123def45"},  # minimal payload
                "score": 0.9,
            },
        ]

        with patch(
            "compose.api.routers.cache.create_in_memory_cache", return_value=mock_cache
        ):
            request = CacheSearchRequest(query="test")
            response = await search_cache(request)

        assert len(response.results) == 1
        assert response.results[0].video_id == "abc123def45"
        assert response.results[0].score == 0.9
        assert response.results[0].title is None
        assert response.results[0].summary is None
        assert response.results[0].tags is None
        assert response.results[0].url is None

    @pytest.mark.asyncio
    async def test_search_error_returns_500(self):
        """Search returns 500 when cache operation fails."""
        mock_cache = MagicMock()
        mock_cache.search.side_effect = Exception("Connection failed")

        with patch(
            "compose.api.routers.cache.create_in_memory_cache", return_value=mock_cache
        ):
            request = CacheSearchRequest(query="test")
            with pytest.raises(HTTPException) as exc_info:
                await search_cache(request)

        assert exc_info.value.status_code == 500
        assert "Cache search failed" in exc_info.value.detail
        assert "Connection failed" in exc_info.value.detail


# -----------------------------------------------------------------------------
# Get Cached Item Endpoint Tests
# -----------------------------------------------------------------------------


@pytest.mark.unit
class TestGetCachedItemEndpoint:
    """Test GET /{key} endpoint behavior."""

    @pytest.mark.asyncio
    async def test_get_existing_item(self):
        """Get returns data for existing cache key."""
        mock_cache = MagicMock()
        mock_cache.exists.return_value = True
        mock_cache.get.return_value = {
            "video_id": "abc123def45",
            "title": "Test Video",
            "tags": ["python", "testing"],
        }

        with patch(
            "compose.api.routers.cache.create_in_memory_cache", return_value=mock_cache
        ):
            response = await get_cached_item("abc123def45")

        assert response == {
            "key": "abc123def45",
            "data": {
                "video_id": "abc123def45",
                "title": "Test Video",
                "tags": ["python", "testing"],
            },
        }
        mock_cache.exists.assert_called_once_with("abc123def45")
        mock_cache.get.assert_called_once_with("abc123def45")

    @pytest.mark.asyncio
    async def test_get_nonexistent_item_returns_404(self):
        """Get returns 404 when key not found."""
        mock_cache = MagicMock()
        mock_cache.exists.return_value = False

        with patch(
            "compose.api.routers.cache.create_in_memory_cache", return_value=mock_cache
        ):
            with pytest.raises(HTTPException) as exc_info:
                await get_cached_item("nonexistent_key")

        assert exc_info.value.status_code == 404
        assert "nonexistent_key" in exc_info.value.detail
        assert "not found" in exc_info.value.detail
        mock_cache.exists.assert_called_once_with("nonexistent_key")
        mock_cache.get.assert_not_called()

    @pytest.mark.asyncio
    async def test_get_error_returns_500(self):
        """Get returns 500 when cache operation fails."""
        mock_cache = MagicMock()
        mock_cache.exists.side_effect = Exception("Database error")

        with patch(
            "compose.api.routers.cache.create_in_memory_cache", return_value=mock_cache
        ):
            with pytest.raises(HTTPException) as exc_info:
                await get_cached_item("test_key")

        assert exc_info.value.status_code == 500
        assert "Failed to get cached item" in exc_info.value.detail
        assert "Database error" in exc_info.value.detail

    @pytest.mark.asyncio
    async def test_get_error_during_fetch_returns_500(self):
        """Get returns 500 when cache.get() fails after exists() succeeds."""
        mock_cache = MagicMock()
        mock_cache.exists.return_value = True
        mock_cache.get.side_effect = Exception("Read error")

        with patch(
            "compose.api.routers.cache.create_in_memory_cache", return_value=mock_cache
        ):
            with pytest.raises(HTTPException) as exc_info:
                await get_cached_item("test_key")

        assert exc_info.value.status_code == 500
        assert "Failed to get cached item" in exc_info.value.detail
        assert "Read error" in exc_info.value.detail
