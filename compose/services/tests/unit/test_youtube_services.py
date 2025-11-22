"""Comprehensive unit tests for YouTube services.

Tests for:
- metadata_service.py - YouTube Data API metadata fetching
- transcript_service.py - YouTube transcript fetching with proxy support
- url_filter.py - URL extraction and filtering
- utils.py - Utility functions

Run with: uv run pytest compose/services/tests/unit/test_youtube_services.py -v
"""

import pytest
from unittest.mock import MagicMock, patch, PropertyMock
import os


# =============================================================================
# metadata_service.py Tests
# =============================================================================


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


# =============================================================================
# transcript_service.py Tests
# =============================================================================


class TestYouTubeTranscriptServiceInit:
    """Test YouTubeTranscriptService initialization."""

    @pytest.mark.unit
    def test_init_with_proxy_credentials(self):
        """Test initialization with explicit proxy credentials."""
        from compose.services.youtube.transcript_service import (
            YouTubeTranscriptService,
        )

        service = YouTubeTranscriptService(
            proxy_username="testuser", proxy_password="testpass", use_proxy=True
        )

        assert service.proxy_username == "testuser"
        assert service.proxy_password == "testpass"
        assert service.use_proxy is True
        assert service._proxy_configured is True

    @pytest.mark.unit
    def test_init_without_proxy(self):
        """Test initialization with proxy disabled."""
        from compose.services.youtube.transcript_service import (
            YouTubeTranscriptService,
        )

        service = YouTubeTranscriptService(use_proxy=False)

        assert service.use_proxy is False
        assert service._proxy_configured is False

    @pytest.mark.unit
    def test_init_proxy_from_env(self):
        """Test initialization loads proxy from environment."""
        with patch.dict(
            os.environ,
            {
                "WEBSHARE_PROXY_USERNAME": "envuser",
                "WEBSHARE_PROXY_PASSWORD": "envpass",
                "YOUTUBE_TRANSCRIPT_USE_PROXY": "true",
            },
        ):
            from compose.services.youtube.transcript_service import (
                YouTubeTranscriptService,
            )

            service = YouTubeTranscriptService()

            assert service.proxy_username == "envuser"
            assert service.proxy_password == "envpass"
            assert service._proxy_configured is True

    @pytest.mark.unit
    def test_init_proxy_disabled_from_env(self):
        """Test initialization respects YOUTUBE_TRANSCRIPT_USE_PROXY=false."""
        with patch.dict(
            os.environ,
            {
                "WEBSHARE_PROXY_USERNAME": "envuser",
                "WEBSHARE_PROXY_PASSWORD": "envpass",
                "YOUTUBE_TRANSCRIPT_USE_PROXY": "false",
            },
        ):
            from compose.services.youtube.transcript_service import (
                YouTubeTranscriptService,
            )

            service = YouTubeTranscriptService()

            assert service.use_proxy is False
            assert service._proxy_configured is False

    @pytest.mark.unit
    def test_init_missing_proxy_credentials(self):
        """Test initialization without proxy credentials doesn't configure proxy."""
        with patch.dict(os.environ, {}, clear=True):
            os.environ.pop("WEBSHARE_PROXY_USERNAME", None)
            os.environ.pop("WEBSHARE_PROXY_PASSWORD", None)
            from compose.services.youtube.transcript_service import (
                YouTubeTranscriptService,
            )

            service = YouTubeTranscriptService()

            assert service._proxy_configured is False


class TestYouTubeTranscriptServiceMethods:
    """Test YouTubeTranscriptService methods."""

    @pytest.mark.unit
    def test_is_proxy_configured(self):
        """Test is_proxy_configured method."""
        from compose.services.youtube.transcript_service import (
            YouTubeTranscriptService,
        )

        service_with_proxy = YouTubeTranscriptService(
            proxy_username="user", proxy_password="pass", use_proxy=True
        )
        service_without_proxy = YouTubeTranscriptService(use_proxy=False)

        assert service_with_proxy.is_proxy_configured() is True
        assert service_without_proxy.is_proxy_configured() is False

    @pytest.mark.unit
    def test_get_proxy_info_configured(self):
        """Test get_proxy_info when proxy is configured."""
        from compose.services.youtube.transcript_service import (
            YouTubeTranscriptService,
        )

        service = YouTubeTranscriptService(
            proxy_username="testuser", proxy_password="testpass", use_proxy=True
        )

        info = service.get_proxy_info()

        assert info["use_proxy"] == "True"
        assert info["proxy_configured"] == "True"
        assert info["proxy_username"] == "testuser"
        assert info["proxy_host"] == "p.webshare.io:80"

    @pytest.mark.unit
    def test_get_proxy_info_not_configured(self):
        """Test get_proxy_info when proxy is not configured."""
        from compose.services.youtube.transcript_service import (
            YouTubeTranscriptService,
        )

        service = YouTubeTranscriptService(use_proxy=False)

        info = service.get_proxy_info()

        assert info["use_proxy"] == "False"
        assert info["proxy_configured"] == "False"
        assert info["proxy_username"] == "not configured"
        assert info["proxy_host"] == "not configured"

    @pytest.mark.unit
    def test_fetch_transcript_success(self):
        """Test successful transcript fetch."""
        mock_snippet1 = MagicMock()
        mock_snippet1.text = "Hello world"
        mock_snippet2 = MagicMock()
        mock_snippet2.text = "this is a test"

        mock_fetched = MagicMock()
        mock_fetched.snippets = [mock_snippet1, mock_snippet2]

        with patch(
            "compose.services.youtube.transcript_service.YouTubeTranscriptApi"
        ) as mock_api_class:
            mock_api = MagicMock()
            mock_api.fetch.return_value = mock_fetched
            mock_api_class.return_value = mock_api

            from compose.services.youtube.transcript_service import (
                YouTubeTranscriptService,
            )

            service = YouTubeTranscriptService(use_proxy=False)
            transcript = service.fetch_transcript("test123")

            assert transcript == "Hello world this is a test"
            mock_api.fetch.assert_called_once_with("test123", languages=["en"])

    @pytest.mark.unit
    def test_fetch_transcript_custom_languages(self):
        """Test transcript fetch with custom languages."""
        mock_snippet = MagicMock()
        mock_snippet.text = "Bonjour"

        mock_fetched = MagicMock()
        mock_fetched.snippets = [mock_snippet]

        with patch(
            "compose.services.youtube.transcript_service.YouTubeTranscriptApi"
        ) as mock_api_class:
            mock_api = MagicMock()
            mock_api.fetch.return_value = mock_fetched
            mock_api_class.return_value = mock_api

            from compose.services.youtube.transcript_service import (
                YouTubeTranscriptService,
            )

            service = YouTubeTranscriptService(use_proxy=False)
            transcript = service.fetch_transcript("test123", languages=["fr", "en"])

            mock_api.fetch.assert_called_once_with("test123", languages=["fr", "en"])

    @pytest.mark.unit
    def test_fetch_timed_transcript_success(self):
        """Test successful timed transcript fetch."""
        mock_snippet1 = MagicMock()
        mock_snippet1.text = "Hello"
        mock_snippet1.start = 0.0
        mock_snippet1.duration = 2.5

        mock_snippet2 = MagicMock()
        mock_snippet2.text = "World"
        mock_snippet2.start = 2.5
        mock_snippet2.duration = 1.5

        mock_fetched = MagicMock()
        mock_fetched.snippets = [mock_snippet1, mock_snippet2]

        with patch(
            "compose.services.youtube.transcript_service.YouTubeTranscriptApi"
        ) as mock_api_class:
            mock_api = MagicMock()
            mock_api.fetch.return_value = mock_fetched
            mock_api_class.return_value = mock_api

            from compose.services.youtube.transcript_service import (
                YouTubeTranscriptService,
            )

            service = YouTubeTranscriptService(use_proxy=False)
            segments = service.fetch_timed_transcript("test123")

            assert len(segments) == 2
            assert segments[0] == {"text": "Hello", "start": 0.0, "duration": 2.5}
            assert segments[1] == {"text": "World", "start": 2.5, "duration": 1.5}

    @pytest.mark.unit
    def test_fetch_transcript_safe_success(self):
        """Test fetch_transcript_safe returns tuple on success."""
        mock_snippet = MagicMock()
        mock_snippet.text = "Test transcript"

        mock_fetched = MagicMock()
        mock_fetched.snippets = [mock_snippet]

        with patch(
            "compose.services.youtube.transcript_service.YouTubeTranscriptApi"
        ) as mock_api_class:
            mock_api = MagicMock()
            mock_api.fetch.return_value = mock_fetched
            mock_api_class.return_value = mock_api

            from compose.services.youtube.transcript_service import (
                YouTubeTranscriptService,
            )

            service = YouTubeTranscriptService(use_proxy=False)
            transcript, error = service.fetch_transcript_safe("test123")

            assert transcript == "Test transcript"
            assert error is None

    @pytest.mark.unit
    def test_fetch_transcript_safe_transcripts_disabled(self):
        """Test fetch_transcript_safe handles TranscriptsDisabled."""
        from youtube_transcript_api._errors import TranscriptsDisabled

        with patch(
            "compose.services.youtube.transcript_service.YouTubeTranscriptApi"
        ) as mock_api_class:
            mock_api = MagicMock()
            mock_api.fetch.side_effect = TranscriptsDisabled("test123")
            mock_api_class.return_value = mock_api

            from compose.services.youtube.transcript_service import (
                YouTubeTranscriptService,
            )

            service = YouTubeTranscriptService(use_proxy=False)
            transcript, error = service.fetch_transcript_safe("test123")

            assert transcript is None
            assert error == "Transcripts are disabled for this video"

    @pytest.mark.unit
    def test_fetch_transcript_safe_no_transcript_found(self):
        """Test fetch_transcript_safe handles NoTranscriptFound."""
        from youtube_transcript_api._errors import NoTranscriptFound

        with patch(
            "compose.services.youtube.transcript_service.YouTubeTranscriptApi"
        ) as mock_api_class:
            mock_api = MagicMock()
            mock_api.fetch.side_effect = NoTranscriptFound(
                "test123", ["en"], {"en": "available"}
            )
            mock_api_class.return_value = mock_api

            from compose.services.youtube.transcript_service import (
                YouTubeTranscriptService,
            )

            service = YouTubeTranscriptService(use_proxy=False)
            transcript, error = service.fetch_transcript_safe(
                "test123", languages=["de"]
            )

            assert transcript is None
            assert "No transcript found" in error

    @pytest.mark.unit
    def test_fetch_transcript_safe_generic_error(self):
        """Test fetch_transcript_safe handles generic errors."""
        with patch(
            "compose.services.youtube.transcript_service.YouTubeTranscriptApi"
        ) as mock_api_class:
            mock_api = MagicMock()
            mock_api.fetch.side_effect = RuntimeError("Network error")
            mock_api_class.return_value = mock_api

            from compose.services.youtube.transcript_service import (
                YouTubeTranscriptService,
            )

            service = YouTubeTranscriptService(use_proxy=False)
            transcript, error = service.fetch_transcript_safe("test123")

            assert transcript is None
            assert "Error fetching transcript" in error
            assert "Network error" in error


class TestTranscriptServiceSingleton:
    """Test singleton and convenience functions."""

    @pytest.mark.unit
    def test_get_default_service_creates_singleton(self):
        """Test that get_default_service creates and reuses instance."""
        # Reset singleton for clean test
        import compose.services.youtube.transcript_service as ts_module

        ts_module._default_service = None

        with patch.dict(os.environ, {"YOUTUBE_TRANSCRIPT_USE_PROXY": "false"}):
            from compose.services.youtube.transcript_service import get_default_service

            service1 = get_default_service()
            service2 = get_default_service()

            assert service1 is service2


# =============================================================================
# url_filter.py Tests
# =============================================================================


class TestExtractUrls:
    """Test URL extraction from text."""

    @pytest.mark.unit
    def test_extract_single_url(self):
        """Test extracting a single URL."""
        from compose.services.youtube.url_filter import extract_urls

        text = "Check out https://github.com/user/repo for more info."
        urls = extract_urls(text)

        assert urls == ["https://github.com/user/repo"]

    @pytest.mark.unit
    def test_extract_multiple_urls(self):
        """Test extracting multiple URLs."""
        from compose.services.youtube.url_filter import extract_urls

        text = "Visit https://example.com and http://test.org for details."
        urls = extract_urls(text)

        assert urls == ["https://example.com", "http://test.org"]

    @pytest.mark.unit
    def test_extract_urls_deduplicates(self):
        """Test that duplicate URLs are removed."""
        from compose.services.youtube.url_filter import extract_urls

        text = "See https://example.com first, then https://example.com again."
        urls = extract_urls(text)

        assert urls == ["https://example.com"]

    @pytest.mark.unit
    def test_extract_urls_removes_trailing_punctuation(self):
        """Test that trailing punctuation is removed."""
        from compose.services.youtube.url_filter import extract_urls

        text = "Check https://example.com. Also https://test.org!"
        urls = extract_urls(text)

        assert urls == ["https://example.com", "https://test.org"]

    @pytest.mark.unit
    def test_extract_urls_handles_parentheses(self):
        """Test handling of unbalanced parentheses."""
        from compose.services.youtube.url_filter import extract_urls

        text = "(See https://example.com/path)"
        urls = extract_urls(text)

        # Should handle unbalanced closing paren
        assert "https://example.com/path" in urls[0]

    @pytest.mark.unit
    def test_extract_urls_no_urls(self):
        """Test extraction from text with no URLs."""
        from compose.services.youtube.url_filter import extract_urls

        text = "This is plain text with no links."
        urls = extract_urls(text)

        assert urls == []

    @pytest.mark.unit
    def test_extract_urls_complex_urls(self):
        """Test extraction of URLs with query parameters."""
        from compose.services.youtube.url_filter import extract_urls

        text = "Link: https://example.com/path?foo=bar&baz=qux"
        urls = extract_urls(text)

        assert urls == ["https://example.com/path?foo=bar&baz=qux"]


class TestIsBlockedByHeuristic:
    """Test heuristic URL blocking."""

    @pytest.mark.unit
    def test_blocked_domain_gumroad(self):
        """Test that gumroad.com is blocked."""
        from compose.services.youtube.url_filter import is_blocked_by_heuristic

        is_blocked, reason = is_blocked_by_heuristic("https://gumroad.com/product")

        assert is_blocked is True
        assert "gumroad.com" in reason

    @pytest.mark.unit
    def test_blocked_domain_patreon(self):
        """Test that patreon.com/join is blocked."""
        from compose.services.youtube.url_filter import is_blocked_by_heuristic

        is_blocked, reason = is_blocked_by_heuristic(
            "https://patreon.com/join/creator"
        )

        assert is_blocked is True
        assert "patreon.com/join" in reason

    @pytest.mark.unit
    def test_blocked_domain_bit_ly(self):
        """Test that bit.ly is blocked."""
        from compose.services.youtube.url_filter import is_blocked_by_heuristic

        is_blocked, reason = is_blocked_by_heuristic("https://bit.ly/abc123")

        assert is_blocked is True
        assert "bit.ly" in reason

    @pytest.mark.unit
    def test_blocked_pattern_checkout(self):
        """Test that checkout URLs are blocked."""
        from compose.services.youtube.url_filter import is_blocked_by_heuristic

        is_blocked, reason = is_blocked_by_heuristic(
            "https://store.example.com/checkout"
        )

        assert is_blocked is True
        assert "checkout" in reason

    @pytest.mark.unit
    def test_blocked_pattern_utm(self):
        """Test that URLs with UTM parameters are blocked."""
        from compose.services.youtube.url_filter import is_blocked_by_heuristic

        is_blocked, reason = is_blocked_by_heuristic(
            "https://example.com/page?utm_source=youtube"
        )

        assert is_blocked is True
        assert "utm_" in reason

    @pytest.mark.unit
    def test_blocked_pattern_affiliate(self):
        """Test that affiliate links are blocked."""
        from compose.services.youtube.url_filter import is_blocked_by_heuristic

        is_blocked, reason = is_blocked_by_heuristic(
            "https://example.com/product?affiliate=abc"
        )

        assert is_blocked is True
        assert "affiliate=" in reason

    @pytest.mark.unit
    def test_blocked_social_twitter_profile(self):
        """Test that Twitter/X profiles are blocked."""
        from compose.services.youtube.url_filter import is_blocked_by_heuristic

        is_blocked, reason = is_blocked_by_heuristic("https://twitter.com/username")

        assert is_blocked is True
        assert "Social media profile" in reason

    @pytest.mark.unit
    def test_blocked_social_instagram_profile(self):
        """Test that Instagram profiles are blocked."""
        from compose.services.youtube.url_filter import is_blocked_by_heuristic

        is_blocked, reason = is_blocked_by_heuristic("https://instagram.com/username")

        assert is_blocked is True
        assert "Social media profile" in reason

    @pytest.mark.unit
    def test_blocked_social_youtube_channel(self):
        """Test that YouTube channel profiles are blocked."""
        from compose.services.youtube.url_filter import is_blocked_by_heuristic

        is_blocked, reason = is_blocked_by_heuristic("https://youtube.com/@username")

        assert is_blocked is True
        assert "Social media profile" in reason

    @pytest.mark.unit
    def test_not_blocked_github(self):
        """Test that GitHub repos are not blocked."""
        from compose.services.youtube.url_filter import is_blocked_by_heuristic

        is_blocked, reason = is_blocked_by_heuristic("https://github.com/user/repo")

        assert is_blocked is False
        assert reason is None

    @pytest.mark.unit
    def test_not_blocked_documentation(self):
        """Test that documentation sites are not blocked."""
        from compose.services.youtube.url_filter import is_blocked_by_heuristic

        is_blocked, reason = is_blocked_by_heuristic("https://docs.python.org/3/")

        assert is_blocked is False
        assert reason is None

    @pytest.mark.unit
    def test_not_blocked_clean_url(self):
        """Test that clean URLs without patterns are not blocked."""
        from compose.services.youtube.url_filter import is_blocked_by_heuristic

        is_blocked, reason = is_blocked_by_heuristic("https://example.com/tutorial")

        assert is_blocked is False
        assert reason is None


class TestApplyHeuristicFilter:
    """Test applying heuristic filter to URL list."""

    @pytest.mark.unit
    def test_apply_filter_mixed_urls(self):
        """Test filtering a mix of blocked and allowed URLs."""
        from compose.services.youtube.url_filter import apply_heuristic_filter

        urls = [
            "https://github.com/user/repo",
            "https://gumroad.com/product",
            "https://docs.python.org",
            "https://bit.ly/abc123",
        ]

        result = apply_heuristic_filter(urls)

        assert len(result["blocked"]) == 2
        assert len(result["remaining"]) == 2
        assert "https://github.com/user/repo" in result["remaining"]
        assert "https://docs.python.org" in result["remaining"]

    @pytest.mark.unit
    def test_apply_filter_all_blocked(self):
        """Test filtering when all URLs are blocked."""
        from compose.services.youtube.url_filter import apply_heuristic_filter

        urls = ["https://gumroad.com/a", "https://bit.ly/b", "https://amzn.to/c"]

        result = apply_heuristic_filter(urls)

        assert len(result["blocked"]) == 3
        assert len(result["remaining"]) == 0

    @pytest.mark.unit
    def test_apply_filter_none_blocked(self):
        """Test filtering when no URLs are blocked."""
        from compose.services.youtube.url_filter import apply_heuristic_filter

        urls = [
            "https://github.com/user/repo",
            "https://docs.python.org",
            "https://stackoverflow.com/questions/123",
        ]

        result = apply_heuristic_filter(urls)

        assert len(result["blocked"]) == 0
        assert len(result["remaining"]) == 3

    @pytest.mark.unit
    def test_apply_filter_empty_list(self):
        """Test filtering empty URL list."""
        from compose.services.youtube.url_filter import apply_heuristic_filter

        result = apply_heuristic_filter([])

        assert result["blocked"] == []
        assert result["remaining"] == []


class TestClassifyUrlWithLlm:
    """Test LLM-based URL classification."""

    @pytest.mark.unit
    def test_classify_url_content(self):
        """Test classifying a content URL."""
        mock_response = MagicMock()
        mock_response.content = [
            MagicMock(
                text='{"classification": "content", "confidence": 0.95, "reason": "Documentation site"}'
            )
        ]
        mock_response.usage = MagicMock()
        mock_response.usage.input_tokens = 100
        mock_response.usage.output_tokens = 50

        with patch(
            "compose.services.youtube.url_filter.Anthropic"
        ) as mock_anthropic_class:
            mock_client = MagicMock()
            mock_client.messages.create.return_value = mock_response
            mock_anthropic_class.return_value = mock_client

            from compose.services.youtube.url_filter import classify_url_with_llm

            classification, confidence, reason, pattern, cost = classify_url_with_llm(
                url="https://docs.python.org",
                video_context={"video_title": "Python Tutorial"},
                api_key="test-key",
            )

            assert classification == "content"
            assert confidence == 0.95
            assert reason == "Documentation site"
            assert cost > 0

    @pytest.mark.unit
    def test_classify_url_marketing(self):
        """Test classifying a marketing URL."""
        mock_response = MagicMock()
        mock_response.content = [
            MagicMock(
                text='{"classification": "marketing", "confidence": 0.85, "reason": "Product page"}'
            )
        ]
        mock_response.usage = MagicMock()
        mock_response.usage.input_tokens = 100
        mock_response.usage.output_tokens = 50

        with patch(
            "compose.services.youtube.url_filter.Anthropic"
        ) as mock_anthropic_class:
            mock_client = MagicMock()
            mock_client.messages.create.return_value = mock_response
            mock_anthropic_class.return_value = mock_client

            from compose.services.youtube.url_filter import classify_url_with_llm

            classification, confidence, reason, pattern, cost = classify_url_with_llm(
                url="https://store.example.com/product",
                video_context={"video_title": "Review"},
                api_key="test-key",
            )

            assert classification == "marketing"
            assert confidence == 0.85

    @pytest.mark.unit
    def test_classify_url_with_suggested_pattern(self):
        """Test classification that includes a suggested pattern."""
        mock_response = MagicMock()
        mock_response.content = [
            MagicMock(
                text="""{
                "classification": "content",
                "confidence": 0.9,
                "reason": "GitHub repo",
                "suggested_pattern": {
                    "pattern": "github.com",
                    "type": "domain",
                    "rationale": "GitHub repos are typically content"
                }
            }"""
            )
        ]
        mock_response.usage = MagicMock()
        mock_response.usage.input_tokens = 100
        mock_response.usage.output_tokens = 80

        with patch(
            "compose.services.youtube.url_filter.Anthropic"
        ) as mock_anthropic_class:
            mock_client = MagicMock()
            mock_client.messages.create.return_value = mock_response
            mock_anthropic_class.return_value = mock_client

            from compose.services.youtube.url_filter import classify_url_with_llm

            classification, confidence, reason, pattern, cost = classify_url_with_llm(
                url="https://github.com/user/repo",
                video_context={"video_title": "Tutorial"},
                api_key="test-key",
            )

            assert pattern is not None
            assert pattern["pattern"] == "github.com"
            assert pattern["type"] == "domain"

    @pytest.mark.unit
    def test_classify_url_fallback_parsing(self):
        """Test fallback when JSON parsing fails."""
        mock_response = MagicMock()
        mock_response.content = [MagicMock(text="Invalid response - not JSON")]
        mock_response.usage = MagicMock()
        mock_response.usage.input_tokens = 100
        mock_response.usage.output_tokens = 50

        with patch(
            "compose.services.youtube.url_filter.Anthropic"
        ) as mock_anthropic_class:
            mock_client = MagicMock()
            mock_client.messages.create.return_value = mock_response
            mock_anthropic_class.return_value = mock_client

            from compose.services.youtube.url_filter import classify_url_with_llm

            classification, confidence, reason, pattern, cost = classify_url_with_llm(
                url="https://example.com",
                video_context={"video_title": "Test"},
                api_key="test-key",
            )

            # Should fall back to marketing with 0.5 confidence
            assert classification == "marketing"
            assert confidence == 0.5
            assert "Failed to parse" in reason

    @pytest.mark.unit
    def test_classify_url_no_api_key(self):
        """Test that missing API key raises ValueError."""
        with patch.dict(os.environ, {}, clear=True):
            os.environ.pop("ANTHROPIC_API_KEY", None)
            from compose.services.youtube.url_filter import classify_url_with_llm

            with pytest.raises(ValueError, match="ANTHROPIC_API_KEY not set"):
                classify_url_with_llm(
                    url="https://example.com",
                    video_context={"video_title": "Test"},
                )


class TestFilterUrls:
    """Test the main filter_urls orchestrator function."""

    @pytest.mark.unit
    def test_filter_urls_no_urls(self):
        """Test filtering text with no URLs."""
        from compose.services.youtube.url_filter import filter_urls

        result = filter_urls(
            description="No URLs here",
            video_context={"video_title": "Test"},
            use_llm=False,
        )

        assert result["all_urls"] == []
        assert result["content_urls"] == []
        assert result["blocked_urls"] == []

    @pytest.mark.unit
    def test_filter_urls_heuristic_only(self):
        """Test filtering with heuristics only (no LLM)."""
        from compose.services.youtube.url_filter import filter_urls

        result = filter_urls(
            description="Check https://github.com/user/repo and https://gumroad.com/product",
            video_context={"video_title": "Test"},
            use_llm=False,
        )

        assert len(result["all_urls"]) == 2
        assert "https://gumroad.com/product" in result["blocked_urls"]
        # Without LLM, remaining URLs go to content
        assert "https://github.com/user/repo" in result["content_urls"]

    @pytest.mark.unit
    def test_filter_urls_all_blocked(self):
        """Test when all URLs are blocked by heuristics."""
        from compose.services.youtube.url_filter import filter_urls

        result = filter_urls(
            description="Links: https://gumroad.com/a https://bit.ly/b",
            video_context={"video_title": "Test"},
            use_llm=False,
        )

        assert len(result["blocked_urls"]) == 2
        assert result["content_urls"] == []
        assert result["remaining"] if "remaining" in result else True

    @pytest.mark.unit
    def test_filter_urls_cost_tracking(self):
        """Test that LLM costs are tracked."""
        mock_response = MagicMock()
        mock_response.content = [
            MagicMock(
                text='{"classification": "content", "confidence": 0.9, "reason": "Test"}'
            )
        ]
        mock_response.usage = MagicMock()
        mock_response.usage.input_tokens = 200
        mock_response.usage.output_tokens = 100

        with patch(
            "compose.services.youtube.url_filter.Anthropic"
        ) as mock_anthropic_class:
            mock_client = MagicMock()
            mock_client.messages.create.return_value = mock_response
            mock_anthropic_class.return_value = mock_client

            from compose.services.youtube.url_filter import filter_urls

            result = filter_urls(
                description="Check https://docs.python.org for info",
                video_context={"video_title": "Tutorial"},
                use_llm=True,
                api_key="test-key",
            )

            assert result["total_llm_cost"] > 0
            assert len(result["llm_classifications"]) == 1


# =============================================================================
# utils.py Tests (Additional coverage beyond test_youtube.py)
# =============================================================================


class TestGetTranscript:
    """Test get_transcript function."""

    @pytest.mark.unit
    def test_get_transcript_success(self):
        """Test successful transcript retrieval."""
        mock_snippet = MagicMock()
        mock_snippet.text = "Test transcript content"

        mock_fetched = MagicMock()
        mock_fetched.snippets = [mock_snippet]

        with patch(
            "compose.services.youtube.utils.YouTubeTranscriptService"
        ) as mock_service_class:
            mock_service = MagicMock()
            mock_service.fetch_transcript_safe.return_value = (
                "Test transcript content",
                None,
            )
            mock_service_class.return_value = mock_service

            from compose.services.youtube.utils import get_transcript

            # Use valid 11-character video ID
            transcript = get_transcript("https://youtube.com/watch?v=dQw4w9WgXcQ")

            assert transcript == "Test transcript content"

    @pytest.mark.unit
    def test_get_transcript_error(self):
        """Test transcript retrieval error handling."""
        with patch(
            "compose.services.youtube.utils.YouTubeTranscriptService"
        ) as mock_service_class:
            mock_service = MagicMock()
            mock_service.fetch_transcript_safe.return_value = (
                None,
                "Transcripts disabled",
            )
            mock_service_class.return_value = mock_service

            from compose.services.youtube.utils import get_transcript

            # Use valid 11-character video ID
            transcript = get_transcript("https://youtube.com/watch?v=dQw4w9WgXcQ")

            assert transcript.startswith("ERROR:")
            assert "Transcripts disabled" in transcript

    @pytest.mark.unit
    def test_get_transcript_invalid_url(self):
        """Test transcript retrieval with invalid URL."""
        from compose.services.youtube.utils import get_transcript

        transcript = get_transcript("https://example.com/invalid")

        assert transcript.startswith("ERROR:")
        assert "video ID" in transcript.lower() or "extract" in transcript.lower()

    @pytest.mark.unit
    def test_get_transcript_with_cache_hit(self):
        """Test transcript retrieval with cache hit."""
        mock_cache = MagicMock()
        mock_cache.exists.return_value = True
        mock_cache.get.return_value = {
            "transcript": "Cached transcript",
            "video_id": "dQw4w9WgXcQ",
        }

        from compose.services.youtube.utils import get_transcript

        # Use valid 11-character video ID
        transcript = get_transcript(
            "https://youtube.com/watch?v=dQw4w9WgXcQ", cache=mock_cache
        )

        assert transcript == "Cached transcript"
        mock_cache.exists.assert_called_once()
        mock_cache.get.assert_called_once()

    @pytest.mark.unit
    def test_get_transcript_with_cache_miss(self):
        """Test transcript retrieval with cache miss."""
        mock_cache = MagicMock()
        mock_cache.exists.return_value = False

        with patch(
            "compose.services.youtube.utils.YouTubeTranscriptService"
        ) as mock_service_class:
            mock_service = MagicMock()
            mock_service.fetch_transcript_safe.return_value = ("Fresh transcript", None)
            mock_service_class.return_value = mock_service

            from compose.services.youtube.utils import get_transcript

            # Use valid 11-character video ID
            transcript = get_transcript(
                "https://youtube.com/watch?v=dQw4w9WgXcQ", cache=mock_cache
            )

            assert transcript == "Fresh transcript"
            mock_cache.set.assert_called_once()


class TestExtractVideoIdEdgeCases:
    """Additional edge case tests for extract_video_id."""

    @pytest.mark.unit
    def test_extract_video_id_embed_url(self):
        """Test extracting video ID from embed URL."""
        from compose.services.youtube.utils import extract_video_id

        url = "https://www.youtube.com/embed/dQw4w9WgXcQ"
        video_id = extract_video_id(url)

        assert video_id == "dQw4w9WgXcQ"

    @pytest.mark.unit
    def test_extract_video_id_special_characters(self):
        """Test extracting video ID with special characters."""
        from compose.services.youtube.utils import extract_video_id

        # Video IDs can contain hyphens and underscores
        url = "https://youtube.com/watch?v=a-B_c1D2e3F"
        video_id = extract_video_id(url)

        assert video_id == "a-B_c1D2e3F"

    @pytest.mark.unit
    def test_extract_video_id_mobile_url(self):
        """Test extracting video ID from mobile URL."""
        from compose.services.youtube.utils import extract_video_id

        url = "https://m.youtube.com/watch?v=dQw4w9WgXcQ"
        video_id = extract_video_id(url)

        assert video_id == "dQw4w9WgXcQ"
