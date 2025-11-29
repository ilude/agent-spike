"""Unit tests for YouTube transcript service.

Tests for transcript_service.py - YouTube transcript fetching with proxy support

Run with: uv run pytest compose/services/tests/unit/test_youtube_transcript.py -v
"""

import pytest
from unittest.mock import MagicMock, patch
import os


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
