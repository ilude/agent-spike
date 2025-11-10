"""YouTube service for video transcript fetching and utilities.

This module provides:
- extract_video_id: Parse YouTube URLs to get video IDs
- get_video_info: Fetch video metadata (with optional caching)
- get_transcript: Fetch video transcripts using proxy-enabled service
- YouTubeTranscriptService: Low-level transcript fetching with proxy support
- get_default_service: Get singleton YouTubeTranscriptService instance

Example:
    >>> from tools.services.youtube import extract_video_id, get_transcript
    >>> video_id = extract_video_id("https://youtube.com/watch?v=dQw4w9WgXcQ")
    >>> transcript = get_transcript("https://youtube.com/watch?v=dQw4w9WgXcQ")
"""

from .utils import extract_video_id, get_video_info, get_transcript
from .transcript_service import YouTubeTranscriptService, get_default_service

__all__ = [
    "extract_video_id",
    "get_video_info",
    "get_transcript",
    "YouTubeTranscriptService",
    "get_default_service",
]
