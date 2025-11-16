"""YouTube service for video transcript fetching and utilities.

This module provides:
- extract_video_id: Parse YouTube URLs to get video IDs
- get_video_info: Fetch video metadata (with optional caching)
- get_transcript: Fetch video transcripts using proxy-enabled service
- YouTubeTranscriptService: Low-level transcript fetching with proxy support
- get_default_service: Get singleton YouTubeTranscriptService instance
- YouTubeMetadataService: YouTube Data API v3 metadata fetching
- fetch_video_metadata: Convenience function for fetching metadata

Example:
    >>> from tools.services.youtube import extract_video_id, get_transcript
    >>> video_id = extract_video_id("https://youtube.com/watch?v=dQw4w9WgXcQ")
    >>> transcript = get_transcript("https://youtube.com/watch?v=dQw4w9WgXcQ")
    >>>
    >>> from tools.services.youtube import fetch_video_metadata
    >>> metadata, error = fetch_video_metadata(video_id)
"""

from .utils import extract_video_id, get_video_info, get_transcript
from .transcript_service import YouTubeTranscriptService, get_default_service
from .metadata_service import YouTubeMetadataService, fetch_video_metadata
from .url_filter import (
    extract_urls,
    is_blocked_by_heuristic,
    apply_heuristic_filter,
    classify_url_with_llm,
    filter_urls,
)

__all__ = [
    "extract_video_id",
    "get_video_info",
    "get_transcript",
    "YouTubeTranscriptService",
    "get_default_service",
    "YouTubeMetadataService",
    "fetch_video_metadata",
    "extract_urls",
    "is_blocked_by_heuristic",
    "apply_heuristic_filter",
    "classify_url_with_llm",
    "filter_urls",
]
