"""Tests for YouTube service utilities.

Run with: uv run pytest tools/tests/unit/test_youtube.py
"""

import pytest
from tools.services.youtube import extract_video_id, get_video_info


@pytest.mark.unit
def test_extract_video_id_standard_url():
    """Test extracting video ID from standard YouTube URL."""
    url = "https://www.youtube.com/watch?v=dQw4w9WgXcQ"
    video_id = extract_video_id(url)
    assert video_id == "dQw4w9WgXcQ"


@pytest.mark.unit
def test_extract_video_id_short_url():
    """Test extracting video ID from short youtu.be URL."""
    url = "https://youtu.be/dQw4w9WgXcQ"
    video_id = extract_video_id(url)
    assert video_id == "dQw4w9WgXcQ"


@pytest.mark.unit
def test_extract_video_id_with_params():
    """Test extracting video ID from URL with query parameters."""
    url = "https://www.youtube.com/watch?v=dQw4w9WgXcQ&t=42s&list=PLxyz"
    video_id = extract_video_id(url)
    assert video_id == "dQw4w9WgXcQ"


@pytest.mark.unit
def test_extract_video_id_without_www():
    """Test extracting video ID from URL without www."""
    url = "https://youtube.com/watch?v=dQw4w9WgXcQ"
    video_id = extract_video_id(url)
    assert video_id == "dQw4w9WgXcQ"


@pytest.mark.unit
def test_extract_video_id_invalid_url():
    """Test that invalid URL raises ValueError."""
    url = "https://example.com/invalid"
    with pytest.raises(ValueError, match="Could not extract video ID"):
        extract_video_id(url)


@pytest.mark.unit
def test_get_video_info_no_cache():
    """Test getting video info without cache."""
    url = "https://youtube.com/watch?v=dQw4w9WgXcQ"
    info = get_video_info(url)

    assert info["video_id"] == "dQw4w9WgXcQ"
    assert info["url"] == url
    assert "note" in info
    assert "error" not in info


@pytest.mark.unit
def test_get_video_info_with_cache():
    """Test getting video info with caching."""
    from tools.services.cache import create_in_memory_cache

    cache = create_in_memory_cache()
    url = "https://youtube.com/watch?v=dQw4w9WgXcQ"

    # First call - should cache
    info1 = get_video_info(url, cache=cache)
    assert info1["video_id"] == "dQw4w9WgXcQ"

    # Second call - should use cache
    info2 = get_video_info(url, cache=cache)
    assert info2 == info1

    # Verify it was cached
    cache_key = "youtube:info:dQw4w9WgXcQ"
    assert cache.exists(cache_key)


@pytest.mark.unit
def test_get_video_info_invalid_url():
    """Test that invalid URL returns error dict."""
    url = "https://example.com/invalid"
    info = get_video_info(url)

    assert "error" in info
    assert "video id" in info["error"].lower()
