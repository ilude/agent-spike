"""Unit tests for YouTube utilities.

Tests for utils.py - Utility functions

Run with: uv run pytest compose/services/tests/unit/test_youtube_utils.py -v
"""

import pytest


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
