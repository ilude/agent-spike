"""Characterization tests for compose/api/routers/ingest.py.

These tests capture the CURRENT behavior of the ingest router,
including Pydantic models and endpoint structures.
"""

import pytest
from pydantic import ValidationError

from compose.api.routers.ingest import (
    IngestRequest,
    IngestResponse,
    detect_url_type,
    extract_video_id,
)


# -----------------------------------------------------------------------------
# IngestRequest Model Tests
# -----------------------------------------------------------------------------


@pytest.mark.unit
class TestIngestRequestModel:
    """Verify Pydantic IngestRequest model fields and validation."""

    def test_required_url_field(self):
        """url is required."""
        with pytest.raises(ValidationError) as exc_info:
            IngestRequest()
        errors = exc_info.value.errors()
        assert any(e["loc"] == ("url",) and e["type"] == "missing" for e in errors)

    def test_valid_request_with_url_only(self):
        """Request with only url uses default channel_limit."""
        req = IngestRequest(url="https://youtube.com/watch?v=abc123def45")
        assert req.url == "https://youtube.com/watch?v=abc123def45"
        assert req.channel_limit == "all"  # default value

    def test_channel_limit_default(self):
        """Default channel_limit is 'all'."""
        req = IngestRequest(url="https://example.com")
        assert req.channel_limit == "all"

    def test_channel_limit_valid_values(self):
        """channel_limit accepts all valid literal values."""
        valid_limits = ["month", "year", "50", "100", "all"]
        for limit in valid_limits:
            req = IngestRequest(url="https://youtube.com/@channel", channel_limit=limit)
            assert req.channel_limit == limit

    def test_channel_limit_invalid_value(self):
        """channel_limit rejects invalid values."""
        with pytest.raises(ValidationError) as exc_info:
            IngestRequest(url="https://youtube.com/@channel", channel_limit="invalid")
        errors = exc_info.value.errors()
        assert any(e["loc"] == ("channel_limit",) for e in errors)

    def test_model_fields(self):
        """Verify model has exactly the expected fields."""
        expected_fields = {"url", "channel_limit"}
        actual_fields = set(IngestRequest.model_fields.keys())
        assert actual_fields == expected_fields


# -----------------------------------------------------------------------------
# IngestResponse Model Tests
# -----------------------------------------------------------------------------


@pytest.mark.unit
class TestIngestResponseModel:
    """Verify Pydantic IngestResponse model structure."""

    def test_required_fields(self):
        """type, status, and message are required."""
        with pytest.raises(ValidationError) as exc_info:
            IngestResponse()
        errors = exc_info.value.errors()
        error_locs = {e["loc"][0] for e in errors}
        assert "type" in error_locs
        assert "status" in error_locs
        assert "message" in error_locs

    def test_valid_response_minimal(self):
        """Response with required fields and default details."""
        resp = IngestResponse(type="video", status="success", message="Done")
        assert resp.type == "video"
        assert resp.status == "success"
        assert resp.message == "Done"
        assert resp.details == {}  # default empty dict

    def test_valid_response_with_details(self):
        """Response with all fields including details."""
        resp = IngestResponse(
            type="channel",
            status="queued",
            message="Queued 10 videos",
            details={"video_count": 10, "channel_id": "UC123"},
        )
        assert resp.type == "channel"
        assert resp.status == "queued"
        assert resp.message == "Queued 10 videos"
        assert resp.details == {"video_count": 10, "channel_id": "UC123"}

    def test_type_valid_values(self):
        """type accepts all valid literal values."""
        valid_types = ["video", "channel", "article"]
        for t in valid_types:
            resp = IngestResponse(type=t, status="success", message="test")
            assert resp.type == t

    def test_type_invalid_value(self):
        """type rejects invalid values."""
        with pytest.raises(ValidationError) as exc_info:
            IngestResponse(type="invalid", status="success", message="test")
        errors = exc_info.value.errors()
        assert any(e["loc"] == ("type",) for e in errors)

    def test_status_valid_values(self):
        """status accepts all valid literal values."""
        valid_statuses = ["success", "skipped", "queued", "error"]
        for s in valid_statuses:
            resp = IngestResponse(type="video", status=s, message="test")
            assert resp.status == s

    def test_status_invalid_value(self):
        """status rejects invalid values."""
        with pytest.raises(ValidationError) as exc_info:
            IngestResponse(type="video", status="pending", message="test")
        errors = exc_info.value.errors()
        assert any(e["loc"] == ("status",) for e in errors)

    def test_model_fields(self):
        """Verify model has exactly the expected fields."""
        expected_fields = {"type", "status", "message", "details"}
        actual_fields = set(IngestResponse.model_fields.keys())
        assert actual_fields == expected_fields

    def test_details_accepts_any_dict(self):
        """details field accepts arbitrary dict values."""
        resp = IngestResponse(
            type="article",
            status="success",
            message="Done",
            details={
                "string": "value",
                "number": 42,
                "bool": True,
                "nested": {"key": "value"},
                "list": [1, 2, 3],
            },
        )
        assert resp.details["string"] == "value"
        assert resp.details["number"] == 42
        assert resp.details["nested"]["key"] == "value"


# -----------------------------------------------------------------------------
# URL Detection Helper Tests
# -----------------------------------------------------------------------------


@pytest.mark.unit
class TestDetectUrlType:
    """Verify URL type detection logic."""

    # YouTube video patterns
    @pytest.mark.parametrize(
        "url",
        [
            "https://www.youtube.com/watch?v=abc123def45",
            "https://youtube.com/watch?v=abc123def45",
            "https://youtu.be/abc123def45",
            "https://www.youtube.com/shorts/abc123def45",
            "https://youtube.com/live/abc123def45",
            "https://YOUTUBE.COM/watch?v=ABC123DEF45",  # case insensitive
        ],
    )
    def test_detects_youtube_video(self, url):
        """Correctly identifies YouTube video URLs."""
        assert detect_url_type(url) == "video"

    # YouTube channel patterns
    @pytest.mark.parametrize(
        "url",
        [
            "https://www.youtube.com/@channelname",
            "https://youtube.com/@channel-name",
            "https://www.youtube.com/channel/UC123abc",
            "https://youtube.com/c/channelname",
            "https://youtube.com/user/username",
            "https://YOUTUBE.COM/@CHANNEL",  # case insensitive
        ],
    )
    def test_detects_youtube_channel(self, url):
        """Correctly identifies YouTube channel URLs."""
        assert detect_url_type(url) == "channel"

    # Generic articles (anything that's not YouTube video/channel)
    @pytest.mark.parametrize(
        "url",
        [
            "https://example.com/article",
            "https://medium.com/@author/post",
            "https://github.com/user/repo",
            "https://docs.python.org/3/library/re.html",
            "https://www.youtube.com/playlist?list=PL123",  # playlist, not video/channel
        ],
    )
    def test_detects_article(self, url):
        """Non-YouTube URLs and YouTube playlists are articles."""
        assert detect_url_type(url) == "article"


# -----------------------------------------------------------------------------
# Video ID Extraction Tests
# -----------------------------------------------------------------------------


@pytest.mark.unit
class TestExtractVideoId:
    """Verify YouTube video ID extraction."""

    @pytest.mark.parametrize(
        "url,expected_id",
        [
            ("https://www.youtube.com/watch?v=abc123def45", "abc123def45"),
            ("https://youtube.com/watch?v=xyz789_-ABC", "xyz789_-ABC"),
            ("https://youtu.be/abc123def45", "abc123def45"),
            ("https://www.youtube.com/shorts/abc123def45", "abc123def45"),
            ("https://youtube.com/live/abc123def45", "abc123def45"),
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

    def test_raises_for_short_id(self):
        """Raises ValueError if video ID is not 11 characters."""
        with pytest.raises(ValueError):
            extract_video_id("https://youtube.com/watch?v=short")
