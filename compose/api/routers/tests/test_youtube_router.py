"""Tests for YouTube router.

Run with: uv run pytest compose/api/routers/tests/test_youtube_router.py
"""

import json
import pytest
from unittest.mock import patch, MagicMock
from pathlib import Path
from pydantic import ValidationError

from compose.api.models import AnalyzeVideoRequest, AnalyzeVideoResponse
from compose.services.youtube import extract_video_id


# -----------------------------------------------------------------------------
# AnalyzeVideoRequest Model Tests
# -----------------------------------------------------------------------------


@pytest.mark.unit
class TestAnalyzeVideoRequestModel:
    """Verify Pydantic AnalyzeVideoRequest model fields and validation."""

    def test_required_url_field(self):
        """url is required."""
        with pytest.raises(ValidationError) as exc_info:
            AnalyzeVideoRequest()
        errors = exc_info.value.errors()
        assert any(e["loc"] == ("url",) and e["type"] == "missing" for e in errors)

    def test_valid_request_with_url_only(self):
        """Request with only url uses default fetch_metadata=False."""
        req = AnalyzeVideoRequest(url="https://youtube.com/watch?v=abc123def45")
        assert str(req.url) == "https://youtube.com/watch?v=abc123def45"
        assert req.fetch_metadata is False

    def test_fetch_metadata_default_false(self):
        """Default fetch_metadata is False."""
        req = AnalyzeVideoRequest(url="https://youtube.com/watch?v=abc123def45")
        assert req.fetch_metadata is False

    def test_fetch_metadata_can_be_true(self):
        """fetch_metadata accepts True."""
        req = AnalyzeVideoRequest(
            url="https://youtube.com/watch?v=abc123def45",
            fetch_metadata=True,
        )
        assert req.fetch_metadata is True

    def test_url_must_be_valid_http_url(self):
        """url field must be a valid HTTP/HTTPS URL."""
        with pytest.raises(ValidationError) as exc_info:
            AnalyzeVideoRequest(url="not-a-url")
        errors = exc_info.value.errors()
        assert any(e["loc"] == ("url",) for e in errors)

    def test_url_accepts_https(self):
        """url accepts HTTPS URLs."""
        req = AnalyzeVideoRequest(url="https://www.youtube.com/watch?v=test123test1")
        assert "https" in str(req.url)

    def test_model_fields(self):
        """Verify model has exactly the expected fields."""
        expected_fields = {"url", "fetch_metadata"}
        actual_fields = set(AnalyzeVideoRequest.model_fields.keys())
        assert actual_fields == expected_fields


# -----------------------------------------------------------------------------
# AnalyzeVideoResponse Model Tests
# -----------------------------------------------------------------------------


@pytest.mark.unit
class TestAnalyzeVideoResponseModel:
    """Verify Pydantic AnalyzeVideoResponse model structure."""

    def test_required_fields(self):
        """video_id, tags, summary, and cached are required."""
        with pytest.raises(ValidationError) as exc_info:
            AnalyzeVideoResponse()
        errors = exc_info.value.errors()
        error_locs = {e["loc"][0] for e in errors}
        assert "video_id" in error_locs
        assert "tags" in error_locs
        assert "summary" in error_locs
        assert "cached" in error_locs

    def test_valid_response_minimal(self):
        """Response with required fields and default metadata=None."""
        resp = AnalyzeVideoResponse(
            video_id="abc123def45",
            tags=["python", "tutorial"],
            summary="A tutorial video",
            cached=False,
        )
        assert resp.video_id == "abc123def45"
        assert resp.tags == ["python", "tutorial"]
        assert resp.summary == "A tutorial video"
        assert resp.cached is False
        assert resp.metadata is None

    def test_valid_response_with_metadata(self):
        """Response with all fields including metadata."""
        metadata = {"title": "Test Video", "channel_title": "Test Channel"}
        resp = AnalyzeVideoResponse(
            video_id="abc123def45",
            tags=["tag1", "tag2"],
            summary="Summary text",
            metadata=metadata,
            cached=True,
        )
        assert resp.video_id == "abc123def45"
        assert resp.tags == ["tag1", "tag2"]
        assert resp.summary == "Summary text"
        assert resp.metadata == metadata
        assert resp.cached is True

    def test_tags_must_be_list_of_strings(self):
        """tags field must be a list of strings."""
        # Valid: list of strings
        resp = AnalyzeVideoResponse(
            video_id="test",
            tags=["a", "b", "c"],
            summary="test",
            cached=False,
        )
        assert resp.tags == ["a", "b", "c"]

    def test_tags_empty_list_allowed(self):
        """tags can be an empty list."""
        resp = AnalyzeVideoResponse(
            video_id="test",
            tags=[],
            summary="test",
            cached=False,
        )
        assert resp.tags == []

    def test_metadata_optional(self):
        """metadata field is optional (defaults to None)."""
        resp = AnalyzeVideoResponse(
            video_id="test",
            tags=[],
            summary="test",
            cached=False,
        )
        assert resp.metadata is None

    def test_metadata_accepts_dict(self):
        """metadata accepts arbitrary dict values."""
        resp = AnalyzeVideoResponse(
            video_id="test",
            tags=[],
            summary="test",
            cached=False,
            metadata={
                "title": "Video Title",
                "view_count": 12345,
                "tags": ["youtube", "tag"],
                "nested": {"key": "value"},
            },
        )
        assert resp.metadata["title"] == "Video Title"
        assert resp.metadata["view_count"] == 12345
        assert resp.metadata["nested"]["key"] == "value"

    def test_model_fields(self):
        """Verify model has exactly the expected fields."""
        expected_fields = {"video_id", "tags", "summary", "metadata", "cached"}
        actual_fields = set(AnalyzeVideoResponse.model_fields.keys())
        assert actual_fields == expected_fields


# -----------------------------------------------------------------------------
# extract_video_id Function Tests
# -----------------------------------------------------------------------------


@pytest.mark.unit
class TestExtractVideoId:
    """Verify YouTube video ID extraction from compose.services.youtube."""

    @pytest.mark.parametrize(
        "url,expected_id",
        [
            ("https://www.youtube.com/watch?v=abc123def45", "abc123def45"),
            ("https://youtube.com/watch?v=xyz789_-ABC", "xyz789_-ABC"),
            ("https://youtu.be/abc123def45", "abc123def45"),
            ("https://www.youtube.com/watch?v=dQw4w9WgXcQ&t=10s", "dQw4w9WgXcQ"),
            ("https://youtube.com/watch?v=test12345ab&list=PL123", "test12345ab"),
        ],
    )
    def test_extracts_valid_video_id(self, url, expected_id):
        """Extracts 11-character video ID from various URL formats."""
        assert extract_video_id(url) == expected_id

    def test_raises_for_invalid_url(self):
        """Raises ValueError for URLs without valid video ID."""
        with pytest.raises(ValueError) as exc_info:
            extract_video_id("https://youtube.com/@channel")
        assert "Could not extract video ID" in str(exc_info.value)

    def test_raises_for_non_youtube_url(self):
        """Raises ValueError for non-YouTube URLs."""
        with pytest.raises(ValueError):
            extract_video_id("https://example.com/video/123")

    def test_raises_for_empty_string(self):
        """Raises ValueError for empty string."""
        with pytest.raises(ValueError):
            extract_video_id("")


# -----------------------------------------------------------------------------
# Analyze Endpoint Tests
# -----------------------------------------------------------------------------


@pytest.mark.unit
class TestAnalyzeEndpoint:
    """Test /analyze endpoint behavior."""

    @pytest.fixture
    def mock_archive_manager(self):
        """Create mock archive manager."""
        mock = MagicMock()
        mock.update_metadata = MagicMock()
        return mock

    @pytest.mark.asyncio
    async def test_invalid_url_returns_400(self):
        """Invalid YouTube URL returns 400 error when extract_video_id returns None."""
        from fastapi import HTTPException
        from compose.api.routers.youtube import analyze_video

        request = AnalyzeVideoRequest(url="https://example.com/not-youtube")

        # When extract_video_id returns None/empty, router returns 400
        with patch("compose.api.routers.youtube.extract_video_id", return_value=None):
            with pytest.raises(HTTPException) as exc_info:
                await analyze_video(request)
            assert exc_info.value.status_code == 400
            assert "Invalid YouTube URL" in exc_info.value.detail

    @pytest.mark.asyncio
    async def test_invalid_url_raises_valueerror_returns_500(self):
        """ValueError from extract_video_id is caught as 500 error."""
        from fastapi import HTTPException
        from compose.api.routers.youtube import analyze_video

        request = AnalyzeVideoRequest(url="https://example.com/not-youtube")

        # When extract_video_id raises ValueError, it's caught by generic handler
        with patch("compose.api.routers.youtube.extract_video_id", side_effect=ValueError("Invalid")):
            with pytest.raises(HTTPException) as exc_info:
                await analyze_video(request)
            assert exc_info.value.status_code == 500
            assert "Analysis failed" in exc_info.value.detail

    @pytest.mark.asyncio
    async def test_uses_cached_data_when_available(self):
        """Uses archived data when available instead of fetching."""
        from compose.api.routers.youtube import analyze_video

        cached_metadata = {
            "title": "Cached Video",
            "channel_title": "Test Channel",
            "description": "Test description",
            "tags": ["cached", "test"],
        }
        archive_data = {"youtube_metadata": cached_metadata}

        request = AnalyzeVideoRequest(url="https://youtube.com/watch?v=abc123def45")

        with patch("compose.api.routers.youtube.extract_video_id", return_value="abc123def45"):
            with patch("compose.api.routers.youtube.create_archive_manager") as mock_create:
                mock_archive = MagicMock()
                mock_create.return_value = mock_archive

                with patch("compose.api.routers.youtube.Path") as mock_path_class:
                    mock_path = MagicMock()
                    mock_path.exists.return_value = True
                    mock_path_class.return_value = mock_path

                    with patch("builtins.open", create=True) as mock_open:
                        mock_open.return_value.__enter__.return_value.read = lambda: json.dumps(archive_data)
                        with patch("json.load", return_value=archive_data):
                            response = await analyze_video(request)

        assert response.cached is True
        assert response.video_id == "abc123def45"

    @pytest.mark.asyncio
    async def test_fetches_metadata_when_not_cached(self):
        """Fetches metadata when archive doesn't exist."""
        from compose.api.routers.youtube import analyze_video

        fresh_metadata = {
            "title": "Fresh Video",
            "channel_title": "New Channel",
            "description": "New description",
            "tags": ["fresh", "new"],
        }

        request = AnalyzeVideoRequest(url="https://youtube.com/watch?v=xyz789abc12")

        with patch("compose.api.routers.youtube.extract_video_id", return_value="xyz789abc12"):
            with patch("compose.api.routers.youtube.create_archive_manager") as mock_create:
                mock_archive = MagicMock()
                mock_create.return_value = mock_archive

                with patch("compose.api.routers.youtube.Path") as mock_path_class:
                    mock_path = MagicMock()
                    mock_path.exists.return_value = False
                    mock_path_class.return_value = mock_path

                    with patch("compose.api.routers.youtube.fetch_video_metadata") as mock_fetch:
                        mock_fetch.return_value = (fresh_metadata, None)
                        response = await analyze_video(request)

        assert response.cached is False
        assert response.video_id == "xyz789abc12"
        assert response.metadata == fresh_metadata


# -----------------------------------------------------------------------------
# Get Metadata Endpoint Tests
# -----------------------------------------------------------------------------


@pytest.mark.unit
class TestGetMetadataEndpoint:
    """Test /metadata/{video_id} endpoint behavior."""

    @pytest.mark.asyncio
    async def test_returns_metadata_when_found(self):
        """Returns metadata dict when video is in archive."""
        from compose.api.routers.youtube import get_metadata

        archive_data = {
            "youtube_metadata": {"title": "Test Video", "channel_title": "Test Channel"},
            "raw_transcript": "Some transcript text",
            "fetched_at": "2025-01-01T00:00:00Z",
        }

        with patch("compose.api.routers.youtube.Path") as mock_path_class:
            mock_path = MagicMock()
            mock_path.exists.return_value = True
            mock_path_class.return_value = mock_path

            with patch("builtins.open", create=True) as mock_open:
                mock_open.return_value.__enter__.return_value.read = lambda: json.dumps(archive_data)
                with patch("json.load", return_value=archive_data):
                    response = await get_metadata("abc123def45")

        assert response["video_id"] == "abc123def45"
        assert response["metadata"] == archive_data["youtube_metadata"]
        assert response["transcript_available"] is True
        assert response["fetched_at"] == "2025-01-01T00:00:00Z"

    @pytest.mark.asyncio
    async def test_returns_404_when_not_found(self):
        """Returns 404 when video is not in archive."""
        from fastapi import HTTPException
        from compose.api.routers.youtube import get_metadata

        with patch("compose.api.routers.youtube.Path") as mock_path_class:
            mock_path = MagicMock()
            mock_path.exists.return_value = False
            mock_path_class.return_value = mock_path

            with pytest.raises(HTTPException) as exc_info:
                await get_metadata("nonexistent123")

        assert exc_info.value.status_code == 404
        assert "Video not found in archive" in exc_info.value.detail

    @pytest.mark.asyncio
    async def test_transcript_available_false_when_missing(self):
        """transcript_available is False when no transcript in archive."""
        from compose.api.routers.youtube import get_metadata

        archive_data = {
            "youtube_metadata": {"title": "Test Video"},
            "fetched_at": "2025-01-01T00:00:00Z",
            # No raw_transcript field
        }

        with patch("compose.api.routers.youtube.Path") as mock_path_class:
            mock_path = MagicMock()
            mock_path.exists.return_value = True
            mock_path_class.return_value = mock_path

            with patch("builtins.open", create=True):
                with patch("json.load", return_value=archive_data):
                    response = await get_metadata("abc123def45")

        assert response["transcript_available"] is False
