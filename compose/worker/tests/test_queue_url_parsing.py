"""Tests for URL and ID parsing in queue processor.

Tests characterize URL parsing behavior for extracting video IDs,
URL type detection, and cache key format.

Run with: uv run pytest compose/worker/tests/test_queue_url_parsing.py -v
"""

import pytest

from compose.services.youtube import extract_video_id


# =============================================================================
# Test: YouTube URL Parsing (via extract_video_id)
# =============================================================================


@pytest.mark.unit
class TestGetVideoIdFromUrl:
    """Test YouTube URL parsing to extract video IDs.

    The queue_processor uses extract_video_id from compose.services.youtube.
    These tests characterize the expected behavior for various URL formats.
    """

    def test_standard_youtube_url(self):
        """Standard youtube.com/watch?v= format."""
        url = "https://www.youtube.com/watch?v=dQw4w9WgXcQ"
        assert extract_video_id(url) == "dQw4w9WgXcQ"

    def test_short_youtu_be_url(self):
        """Short youtu.be/ format."""
        url = "https://youtu.be/dQw4w9WgXcQ"
        assert extract_video_id(url) == "dQw4w9WgXcQ"

    def test_url_with_query_params(self):
        """URL with additional query parameters after video ID."""
        url = "https://www.youtube.com/watch?v=dQw4w9WgXcQ&t=42s&list=PLxyz"
        assert extract_video_id(url) == "dQw4w9WgXcQ"

    def test_url_without_www(self):
        """URL without www prefix."""
        url = "https://youtube.com/watch?v=dQw4w9WgXcQ"
        assert extract_video_id(url) == "dQw4w9WgXcQ"

    def test_url_with_underscore_in_id(self):
        """Video ID containing underscore character."""
        url = "https://youtube.com/watch?v=abc_def_123"
        assert extract_video_id(url) == "abc_def_123"

    def test_url_with_dash_in_id(self):
        """Video ID containing dash character."""
        url = "https://youtube.com/watch?v=abc-def-123"
        assert extract_video_id(url) == "abc-def-123"

    def test_invalid_url_raises_value_error(self):
        """Non-YouTube URL should raise ValueError."""
        url = "https://example.com/invalid"
        with pytest.raises(ValueError, match="Could not extract video ID"):
            extract_video_id(url)

    def test_empty_url_raises_value_error(self):
        """Empty string should raise ValueError."""
        with pytest.raises(ValueError, match="Could not extract video ID"):
            extract_video_id("")


# =============================================================================
# Test: URL Type Detection
# =============================================================================


@pytest.mark.unit
class TestUrlTypeDetection:
    """Test detection of YouTube vs webpage URLs.

    The queue_processor currently only handles YouTube URLs.
    This characterizes the URL patterns that are recognized.
    """

    def test_youtube_watch_url_detected(self):
        """Standard youtube.com/watch URL is detected."""
        url = "https://www.youtube.com/watch?v=dQw4w9WgXcQ"

        # Using the logic from extract_video_id to detect YouTube URLs
        try:
            video_id = extract_video_id(url)
            is_youtube = True
        except ValueError:
            is_youtube = False

        assert is_youtube is True
        assert video_id == "dQw4w9WgXcQ"

    def test_youtu_be_url_detected(self):
        """Short youtu.be URL is detected."""
        url = "https://youtu.be/dQw4w9WgXcQ"

        try:
            video_id = extract_video_id(url)
            is_youtube = True
        except ValueError:
            is_youtube = False

        assert is_youtube is True

    def test_non_youtube_url_may_extract_false_positive(self):
        """Non-YouTube URL with /XXXXXXXXXXX path segment may extract false positive.

        CURRENT BEHAVIOR (characterization): The regex r'(?:v=|/)([0-9A-Za-z_-]{11}).*'
        will match any URL with a path segment of 11 alphanumeric characters.
        This is a known limitation - the queue processor relies on input validation
        at the queue level rather than URL parsing.
        """
        url = "https://example.com/some-articl"  # "some-articl" is exactly 11 chars

        # ACTUAL behavior: extracts false positive ID
        try:
            video_id = extract_video_id(url)
            is_youtube = True
        except ValueError:
            is_youtube = False
            video_id = None

        # Characterization: documents that this DOES extract a false ID
        assert is_youtube is True
        assert video_id == "some-articl"

    def test_short_path_does_not_match(self):
        """URL with path segment shorter than 11 chars raises ValueError."""
        url = "https://example.com/short"  # "short" is only 5 chars

        with pytest.raises(ValueError, match="Could not extract video ID"):
            extract_video_id(url)

    def test_youtube_playlist_url_handling(self):
        """YouTube playlist URL with video should extract video ID."""
        url = "https://www.youtube.com/watch?v=dQw4w9WgXcQ&list=PLrAXtmErZgOeiKm4sgNOknGvNjby9efdf"

        try:
            video_id = extract_video_id(url)
            is_youtube = True
        except ValueError:
            is_youtube = False

        assert is_youtube is True
        assert video_id == "dQw4w9WgXcQ"

    def test_youtube_embed_url_handling(self):
        """YouTube embed URL format."""
        url = "https://www.youtube.com/embed/dQw4w9WgXcQ"

        # Current implementation uses /VIDEO_ID pattern which should match
        try:
            video_id = extract_video_id(url)
            is_youtube = True
        except ValueError:
            is_youtube = False

        # Characterization: document current behavior
        assert is_youtube is True


# =============================================================================
# Test: Cache Key Format
# =============================================================================


@pytest.mark.unit
class TestCacheKeyFormat:
    """Test the cache key format used for YouTube videos."""

    def test_cache_key_format(self):
        """Cache keys should follow 'youtube:video:{video_id}' format."""
        video_id = "dQw4w9WgXcQ"
        cache_key = f"youtube:video:{video_id}"

        assert cache_key == "youtube:video:dQw4w9WgXcQ"
        assert cache_key.startswith("youtube:video:")

    def test_cache_key_extracts_video_id(self):
        """Video ID can be extracted from cache key."""
        cache_key = "youtube:video:dQw4w9WgXcQ"

        parts = cache_key.split(":")
        assert len(parts) == 3
        assert parts[0] == "youtube"
        assert parts[1] == "video"
        assert parts[2] == "dQw4w9WgXcQ"
