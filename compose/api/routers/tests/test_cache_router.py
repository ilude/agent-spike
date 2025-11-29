"""Tests for cache router.

Run with: uv run pytest compose/api/routers/tests/test_cache_router.py
"""

import pytest
from unittest.mock import patch, AsyncMock, MagicMock
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
    async def test_search_returns_empty_results(self):
        """Search returns empty results (current implementation)."""
        # Current implementation returns empty results since semantic search
        # requires embedding generation which is not yet implemented
        request = CacheSearchRequest(query="python tutorials", limit=10)
        response = await search_cache(request)

        assert response.query == "python tutorials"
        assert response.total_found == 0
        assert response.results == []


# -----------------------------------------------------------------------------
# Get Cached Item Endpoint Tests
# -----------------------------------------------------------------------------


@pytest.mark.unit
class TestGetCachedItemEndpoint:
    """Test GET /{key} endpoint behavior."""

    @pytest.mark.asyncio
    async def test_get_existing_item(self):
        """Get returns data for existing video from SurrealDB."""
        mock_video = MagicMock()
        mock_video.video_id = "abc123def45"
        mock_video.url = "https://youtube.com/watch?v=abc123def45"
        mock_video.title = "Test Video"
        mock_video.channel_id = "UC123"
        mock_video.channel_name = "Test Channel"

        with patch(
            "compose.services.surrealdb.get_video",
            new_callable=AsyncMock,
            return_value=mock_video,
        ):
            response = await get_cached_item("youtube:video:abc123def45")

        assert response == {
            "key": "youtube:video:abc123def45",
            "data": {
                "video_id": "abc123def45",
                "url": "https://youtube.com/watch?v=abc123def45",
                "title": "Test Video",
                "channel_id": "UC123",
                "channel_name": "Test Channel",
            },
        }

    @pytest.mark.asyncio
    async def test_get_nonexistent_item_returns_404(self):
        """Get returns 404 when video not found in SurrealDB."""
        with patch(
            "compose.services.surrealdb.get_video",
            new_callable=AsyncMock,
            return_value=None,
        ):
            with pytest.raises(HTTPException) as exc_info:
                await get_cached_item("youtube:video:nonexistent")

        assert exc_info.value.status_code == 404
        assert "not found" in exc_info.value.detail

    @pytest.mark.asyncio
    async def test_get_invalid_key_format_returns_404(self):
        """Get returns 404 for invalid cache key format."""
        with pytest.raises(HTTPException) as exc_info:
            await get_cached_item("invalid_key_format")

        assert exc_info.value.status_code == 404
        assert "Invalid cache key format" in exc_info.value.detail

    @pytest.mark.asyncio
    async def test_get_error_returns_500(self):
        """Get returns 500 when SurrealDB operation fails."""
        with patch(
            "compose.services.surrealdb.get_video",
            new_callable=AsyncMock,
            side_effect=Exception("Database error"),
        ):
            with pytest.raises(HTTPException) as exc_info:
                await get_cached_item("youtube:video:test_key")

        assert exc_info.value.status_code == 500
        assert "Failed to get cached item" in exc_info.value.detail
        assert "Database error" in exc_info.value.detail
