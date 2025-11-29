"""Unit tests for YouTube metadata service.

Tests for metadata_service.py - YouTube Data API metadata fetching

Run with: uv run pytest compose/services/tests/unit/test_youtube_metadata.py -v
"""

import pytest
from unittest.mock import MagicMock, patch
import os


class TestYouTubeMetadataServiceInit:
    """Test YouTubeMetadataService initialization."""

    @pytest.mark.unit
    def test_init_with_api_key(self):
        """Test initialization with explicit API key."""
        with patch("compose.services.youtube.metadata_service.build") as mock_build:
            mock_build.return_value = MagicMock()
            from compose.services.youtube.metadata_service import YouTubeMetadataService

            service = YouTubeMetadataService(api_key="test-api-key")
            assert service.api_key == "test-api-key"
            mock_build.assert_called_once_with(
                "youtube", "v3", developerKey="test-api-key"
            )

    @pytest.mark.unit
    def test_init_with_env_var(self):
        """Test initialization from environment variable."""
        with patch.dict(os.environ, {"YOUTUBE_API_KEY": "env-api-key"}):
            with patch("compose.services.youtube.metadata_service.build") as mock_build:
                mock_build.return_value = MagicMock()
                from compose.services.youtube.metadata_service import (
                    YouTubeMetadataService,
                )

                service = YouTubeMetadataService()
                assert service.api_key == "env-api-key"

    @pytest.mark.unit
    def test_init_raises_without_api_key(self):
        """Test that initialization raises ValueError without API key."""
        with patch.dict(os.environ, {}, clear=True):
            # Ensure YOUTUBE_API_KEY is not set
            os.environ.pop("YOUTUBE_API_KEY", None)
            from compose.services.youtube.metadata_service import YouTubeMetadataService

            with pytest.raises(ValueError, match="YouTube API key not provided"):
                YouTubeMetadataService()


class TestParseDurationToSeconds:
    """Test _parse_duration_to_seconds static method."""

    @pytest.mark.unit
    def test_minutes_and_seconds(self):
        """Test parsing duration with minutes and seconds."""
        from compose.services.youtube.metadata_service import YouTubeMetadataService

        assert YouTubeMetadataService._parse_duration_to_seconds("PT15M33S") == 933

    @pytest.mark.unit
    def test_hours_minutes_seconds(self):
        """Test parsing duration with hours, minutes, and seconds."""
        from compose.services.youtube.metadata_service import YouTubeMetadataService

        assert YouTubeMetadataService._parse_duration_to_seconds("PT1H2M3S") == 3723

    @pytest.mark.unit
    def test_hours_only(self):
        """Test parsing duration with only hours."""
        from compose.services.youtube.metadata_service import YouTubeMetadataService

        assert YouTubeMetadataService._parse_duration_to_seconds("PT2H") == 7200

    @pytest.mark.unit
    def test_minutes_only(self):
        """Test parsing duration with only minutes."""
        from compose.services.youtube.metadata_service import YouTubeMetadataService

        assert YouTubeMetadataService._parse_duration_to_seconds("PT30M") == 1800

    @pytest.mark.unit
    def test_seconds_only(self):
        """Test parsing duration with only seconds."""
        from compose.services.youtube.metadata_service import YouTubeMetadataService

        assert YouTubeMetadataService._parse_duration_to_seconds("PT45S") == 45

    @pytest.mark.unit
    def test_invalid_format(self):
        """Test parsing invalid duration format returns 0."""
        from compose.services.youtube.metadata_service import YouTubeMetadataService

        assert YouTubeMetadataService._parse_duration_to_seconds("invalid") == 0
        assert YouTubeMetadataService._parse_duration_to_seconds("") == 0
        assert YouTubeMetadataService._parse_duration_to_seconds("P1D") == 0


class TestFormatDuration:
    """Test format_duration static method."""

    @pytest.mark.unit
    def test_format_minutes_seconds(self):
        """Test formatting with minutes and seconds."""
        from compose.services.youtube.metadata_service import YouTubeMetadataService

        assert YouTubeMetadataService.format_duration("PT15M33S") == "15:33"

    @pytest.mark.unit
    def test_format_hours_minutes_seconds(self):
        """Test formatting with hours, minutes, and seconds."""
        from compose.services.youtube.metadata_service import YouTubeMetadataService

        assert YouTubeMetadataService.format_duration("PT1H2M3S") == "1:02:03"

    @pytest.mark.unit
    def test_format_hours_only(self):
        """Test formatting with only hours."""
        from compose.services.youtube.metadata_service import YouTubeMetadataService

        assert YouTubeMetadataService.format_duration("PT2H") == "2:00:00"

    @pytest.mark.unit
    def test_format_short_duration(self):
        """Test formatting short duration (under 10 seconds)."""
        from compose.services.youtube.metadata_service import YouTubeMetadataService

        assert YouTubeMetadataService.format_duration("PT0M5S") == "0:05"

    @pytest.mark.unit
    def test_format_invalid_returns_input(self):
        """Test that invalid format returns original input."""
        from compose.services.youtube.metadata_service import YouTubeMetadataService

        assert YouTubeMetadataService.format_duration("invalid") == "invalid"


class TestFetchMetadata:
    """Test fetch_metadata and fetch_metadata_safe methods."""

    @pytest.mark.unit
    def test_fetch_metadata_success(self):
        """Test successful metadata fetch."""
        mock_response = {
            "items": [
                {
                    "snippet": {
                        "title": "Test Video",
                        "description": "Test description",
                        "publishedAt": "2024-01-15T10:30:00Z",
                        "channelId": "UCtest123",
                        "channelTitle": "Test Channel",
                        "tags": ["tag1", "tag2"],
                        "categoryId": "22",
                        "thumbnails": {"default": {"url": "http://example.com/thumb.jpg"}},
                    },
                    "statistics": {
                        "viewCount": "1000",
                        "likeCount": "100",
                        "commentCount": "50",
                    },
                    "contentDetails": {"duration": "PT15M33S"},
                }
            ]
        }

        with patch("compose.services.youtube.metadata_service.build") as mock_build:
            mock_youtube = MagicMock()
            mock_request = MagicMock()
            mock_request.execute.return_value = mock_response
            mock_youtube.videos.return_value.list.return_value = mock_request
            mock_build.return_value = mock_youtube

            from compose.services.youtube.metadata_service import YouTubeMetadataService

            service = YouTubeMetadataService(api_key="test-key")
            metadata = service.fetch_metadata("test123")

            assert metadata["video_id"] == "test123"
            assert metadata["title"] == "Test Video"
            assert metadata["description"] == "Test description"
            assert metadata["channel_title"] == "Test Channel"
            assert metadata["view_count"] == 1000
            assert metadata["like_count"] == 100
            assert metadata["comment_count"] == 50
            assert metadata["duration_seconds"] == 933
            assert metadata["tags"] == ["tag1", "tag2"]

    @pytest.mark.unit
    def test_fetch_metadata_video_not_found(self):
        """Test fetch_metadata raises ValueError for non-existent video."""
        mock_response = {"items": []}

        with patch("compose.services.youtube.metadata_service.build") as mock_build:
            mock_youtube = MagicMock()
            mock_request = MagicMock()
            mock_request.execute.return_value = mock_response
            mock_youtube.videos.return_value.list.return_value = mock_request
            mock_build.return_value = mock_youtube

            from compose.services.youtube.metadata_service import YouTubeMetadataService

            service = YouTubeMetadataService(api_key="test-key")
            with pytest.raises(ValueError, match="Video not found"):
                service.fetch_metadata("nonexistent")

    @pytest.mark.unit
    def test_fetch_metadata_missing_optional_fields(self):
        """Test fetch_metadata handles missing optional fields."""
        mock_response = {
            "items": [
                {
                    "snippet": {
                        "title": "Test Video",
                        "publishedAt": "2024-01-15T10:30:00Z",
                        "channelId": "UCtest123",
                        "channelTitle": "Test Channel",
                        # No description, tags, categoryId, thumbnails
                    },
                    "statistics": {
                        "viewCount": "1000",
                        # No likeCount, commentCount (could be hidden)
                    },
                    "contentDetails": {"duration": "PT5M"},
                }
            ]
        }

        with patch("compose.services.youtube.metadata_service.build") as mock_build:
            mock_youtube = MagicMock()
            mock_request = MagicMock()
            mock_request.execute.return_value = mock_response
            mock_youtube.videos.return_value.list.return_value = mock_request
            mock_build.return_value = mock_youtube

            from compose.services.youtube.metadata_service import YouTubeMetadataService

            service = YouTubeMetadataService(api_key="test-key")
            metadata = service.fetch_metadata("test123")

            assert metadata["description"] == ""
            assert metadata["tags"] == []
            assert metadata["like_count"] is None
            assert metadata["comment_count"] is None

    @pytest.mark.unit
    def test_fetch_metadata_safe_success(self):
        """Test fetch_metadata_safe returns tuple on success."""
        with patch("compose.services.youtube.metadata_service.build") as mock_build:
            mock_youtube = MagicMock()
            mock_request = MagicMock()
            mock_request.execute.return_value = {
                "items": [
                    {
                        "snippet": {
                            "title": "Test",
                            "publishedAt": "2024-01-01T00:00:00Z",
                            "channelId": "UC123",
                            "channelTitle": "Channel",
                        },
                        "statistics": {"viewCount": "100"},
                        "contentDetails": {"duration": "PT1M"},
                    }
                ]
            }
            mock_youtube.videos.return_value.list.return_value = mock_request
            mock_build.return_value = mock_youtube

            from compose.services.youtube.metadata_service import YouTubeMetadataService

            service = YouTubeMetadataService(api_key="test-key")
            metadata, error = service.fetch_metadata_safe("test123")

            assert metadata is not None
            assert error is None
            assert metadata["title"] == "Test"

    @pytest.mark.unit
    def test_fetch_metadata_safe_video_not_found(self):
        """Test fetch_metadata_safe returns error tuple for non-existent video."""
        with patch("compose.services.youtube.metadata_service.build") as mock_build:
            mock_youtube = MagicMock()
            mock_request = MagicMock()
            mock_request.execute.return_value = {"items": []}
            mock_youtube.videos.return_value.list.return_value = mock_request
            mock_build.return_value = mock_youtube

            from compose.services.youtube.metadata_service import YouTubeMetadataService

            service = YouTubeMetadataService(api_key="test-key")
            metadata, error = service.fetch_metadata_safe("nonexistent")

            assert metadata is None
            assert error is not None
            assert "Video not found" in error

    @pytest.mark.unit
    def test_fetch_metadata_safe_http_error(self):
        """Test fetch_metadata_safe handles HTTP errors."""
        from googleapiclient.errors import HttpError

        with patch("compose.services.youtube.metadata_service.build") as mock_build:
            mock_youtube = MagicMock()
            mock_request = MagicMock()
            # Create a proper HttpError
            resp = MagicMock()
            resp.status = 403
            resp.reason = "Forbidden"
            mock_request.execute.side_effect = HttpError(resp, b"Quota exceeded")
            mock_youtube.videos.return_value.list.return_value = mock_request
            mock_build.return_value = mock_youtube

            from compose.services.youtube.metadata_service import YouTubeMetadataService

            service = YouTubeMetadataService(api_key="test-key")
            metadata, error = service.fetch_metadata_safe("test123")

            assert metadata is None
            assert error is not None
            assert "API error" in error

    @pytest.mark.unit
    def test_fetch_metadata_safe_unexpected_error(self):
        """Test fetch_metadata_safe handles unexpected errors."""
        with patch("compose.services.youtube.metadata_service.build") as mock_build:
            mock_youtube = MagicMock()
            mock_request = MagicMock()
            mock_request.execute.side_effect = RuntimeError("Network failure")
            mock_youtube.videos.return_value.list.return_value = mock_request
            mock_build.return_value = mock_youtube

            from compose.services.youtube.metadata_service import YouTubeMetadataService

            service = YouTubeMetadataService(api_key="test-key")
            metadata, error = service.fetch_metadata_safe("test123")

            assert metadata is None
            assert error is not None
            assert "Unexpected error" in error


class TestFetchVideoMetadataFunction:
    """Test the convenience function fetch_video_metadata."""

    @pytest.mark.unit
    def test_fetch_video_metadata_without_api_key(self):
        """Test fetch_video_metadata returns error without API key."""
        with patch.dict(os.environ, {}, clear=True):
            os.environ.pop("YOUTUBE_API_KEY", None)
            from compose.services.youtube.metadata_service import fetch_video_metadata

            metadata, error = fetch_video_metadata("test123")

            assert metadata is None
            assert error is not None
            assert "API key" in error
