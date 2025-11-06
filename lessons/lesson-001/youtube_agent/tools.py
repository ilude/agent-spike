"""YouTube API tools for fetching video data."""

import re
from typing import Any, Optional, Protocol
from youtube_transcript_api import YouTubeTranscriptApi
from youtube_transcript_api._errors import TranscriptsDisabled, NoTranscriptFound


class CacheManager(Protocol):
    """Cache interface for dependency injection.

    Actual implementation will be in lesson-007.
    This allows tools to optionally use caching without hard dependencies.
    """

    def get(self, key: str) -> Optional[dict[str, Any]]:
        """Retrieve cached data by key"""
        ...

    def set(self, key: str, value: dict[str, Any], metadata: Optional[dict[str, Any]] = None) -> None:
        """Store data with optional metadata"""
        ...

    def exists(self, key: str) -> bool:
        """Check if key exists in cache"""
        ...


def extract_video_id(url: str) -> str:
    """Extract video ID from YouTube URL.

    Supports formats:
    - https://youtube.com/watch?v=VIDEO_ID
    - https://youtu.be/VIDEO_ID
    - https://www.youtube.com/watch?v=VIDEO_ID&other=params
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
    For a production app, you'd use the YouTube Data API v3.

    Args:
        url: YouTube video URL
        cache: Optional cache manager for storing/retrieving video info

    Returns:
        Dictionary with video_id and url
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
    """Fetch YouTube video transcript.

    Args:
        url: YouTube video URL
        cache: Optional cache manager for storing/retrieving transcripts

    Returns:
        Full transcript text as a single string
    """
    try:
        video_id = extract_video_id(url)

        # Try cache first if available
        cache_key = f"youtube:transcript:{video_id}"
        if cache and cache.exists(cache_key):
            cached = cache.get(cache_key)
            if cached and "transcript" in cached:
                return cached["transcript"]

        # Create API instance and fetch transcript
        api = YouTubeTranscriptApi()
        fetched = api.fetch(video_id)

        # Combine all transcript snippets into single text
        full_text = " ".join(snippet.text for snippet in fetched.snippets)

        # Store in cache if available
        if cache:
            cache.set(
                cache_key,
                {"transcript": full_text, "video_id": video_id, "url": url},
                metadata={"type": "youtube_transcript", "source": "youtube-transcript-api"}
            )

        return full_text

    except TranscriptsDisabled:
        return "ERROR: Transcripts are disabled for this video"
    except NoTranscriptFound:
        return "ERROR: No transcript found for this video"
    except Exception as e:
        return f"ERROR: {str(e)}"
