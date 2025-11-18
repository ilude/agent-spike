"""YouTube utility functions for video data extraction."""

import re
from typing import Any, Optional

from .transcript_service import YouTubeTranscriptService

# Import CacheManager protocol from cache service (avoid duplication)
try:
    from compose.services.cache import CacheManager
except ImportError:
    # If cache service not available, define minimal protocol
    from typing import Protocol

    class CacheManager(Protocol):
        """Cache interface for dependency injection."""
        def get(self, key: str) -> Optional[dict[str, Any]]: ...
        def set(self, key: str, value: dict[str, Any], metadata: Optional[dict[str, Any]] = None) -> None: ...
        def exists(self, key: str) -> bool: ...


def extract_video_id(url: str) -> str:
    """Extract video ID from YouTube URL.

    Supports formats:
    - https://youtube.com/watch?v=VIDEO_ID
    - https://youtu.be/VIDEO_ID
    - https://www.youtube.com/watch?v=VIDEO_ID&other=params

    Args:
        url: YouTube video URL

    Returns:
        11-character video ID

    Raises:
        ValueError: If video ID cannot be extracted from URL

    Example:
        >>> extract_video_id("https://youtube.com/watch?v=dQw4w9WgXcQ")
        'dQw4w9WgXcQ'
    """
    patterns = [
        r'(?:v=|\/)([0-9A-Za-z_-]{11}).*',
        r'youtu\.be\/([0-9A-Za-z_-]{11})',
    ]

    for pattern in patterns:
        match = re.search(pattern, url)
        if match:
            return match.group(1)

    raise ValueError(f"Could not extract video ID from URL: {url}")


def get_video_info(url: str, cache: Optional[CacheManager] = None) -> dict[str, Any]:
    """Fetch YouTube video metadata.

    Note: youtube-transcript-api doesn't provide metadata directly.
    We extract what we can from the API and video ID.
    For full metadata, use the YouTube Data API v3.

    Args:
        url: YouTube video URL
        cache: Optional cache manager for storing/retrieving video info

    Returns:
        Dictionary with video_id, url, and note about limitations

    Example:
        >>> info = get_video_info("https://youtube.com/watch?v=dQw4w9WgXcQ")
        >>> print(info["video_id"])
        'dQw4w9WgXcQ'
    """
    try:
        video_id = extract_video_id(url)

        # Try cache first if available
        cache_key = f"youtube:info:{video_id}"
        if cache and cache.exists(cache_key):
            cached = cache.get(cache_key)
            if cached:
                return cached

        # Fetch fresh data
        info = {
            "video_id": video_id,
            "url": url,
            "note": "Full metadata requires YouTube Data API - using transcript API only"
        }

        # Store in cache if available
        if cache:
            cache.set(cache_key, info, metadata={"type": "youtube_info"})

        return info

    except Exception as e:
        return {"error": str(e)}


def get_transcript(url: str, cache: Optional[CacheManager] = None) -> str:
    """Fetch YouTube video transcript using proxy-enabled service.

    This function automatically handles:
    - Video ID extraction from URL
    - Optional caching to avoid re-fetching
    - Proxy support via Webshare (configured in .env)
    - Error handling with descriptive messages

    Args:
        url: YouTube video URL
        cache: Optional cache manager for storing/retrieving transcripts

    Returns:
        Full transcript text as a single string, or "ERROR: ..." on failure

    Example:
        >>> transcript = get_transcript("https://youtube.com/watch?v=dQw4w9WgXcQ")
        >>> print(transcript[:100])
        'We're no strangers to love...'
    """
    try:
        video_id = extract_video_id(url)

        # Try cache first if available
        cache_key = f"youtube:transcript:{video_id}"
        if cache and cache.exists(cache_key):
            cached = cache.get(cache_key)
            if cached and "transcript" in cached:
                return cached["transcript"]

        # Fetch transcript using proxy-enabled service
        service = YouTubeTranscriptService()
        full_text, error = service.fetch_transcript_safe(video_id)

        if error:
            return f"ERROR: {error}"

        # Store in cache if available
        if cache:
            cache.set(
                cache_key,
                {"transcript": full_text, "video_id": video_id, "url": url},
                metadata={"type": "youtube_transcript", "source": "youtube-transcript-api"}
            )

        return full_text

    except Exception as e:
        return f"ERROR: {str(e)}"
