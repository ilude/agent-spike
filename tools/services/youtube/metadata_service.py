"""YouTube Data API v3 metadata fetching service.

This module wraps the YouTube Data API to fetch video metadata
(title, description, statistics, channel info, etc.).
"""

import os
import re
from typing import Optional, Tuple
from datetime import datetime

from googleapiclient.discovery import build
from googleapiclient.errors import HttpError


class YouTubeMetadataService:
    """Service for fetching YouTube video metadata using Data API v3.

    Wraps googleapiclient to provide clean interface for fetching
    video metadata. Auto-configures from YOUTUBE_API_KEY environment variable.

    Example:
        >>> service = YouTubeMetadataService()
        >>> metadata, error = service.fetch_metadata_safe("dQw4w9WgXcQ")
        >>> if metadata:
        ...     print(f"Title: {metadata['title']}")
        ...     print(f"Views: {metadata['view_count']}")
    """

    def __init__(self, api_key: Optional[str] = None):
        """Initialize YouTube metadata service.

        Args:
            api_key: Optional YouTube Data API v3 key (uses YOUTUBE_API_KEY env var if not provided)
        """
        self.api_key = api_key or os.getenv("YOUTUBE_API_KEY")

        if not self.api_key:
            raise ValueError(
                "YouTube API key not provided and YOUTUBE_API_KEY environment variable not set"
            )

        self.youtube = build("youtube", "v3", developerKey=self.api_key)

    def fetch_metadata(self, video_id: str) -> dict:
        """Fetch metadata for a YouTube video.

        Args:
            video_id: YouTube video ID (11 characters)

        Returns:
            Dict with metadata fields:
                - video_id: str
                - title: str
                - description: str (full text)
                - published_at: str (ISO 8601 timestamp)
                - channel_id: str
                - channel_title: str
                - duration: str (ISO 8601 duration, e.g., "PT15M33S")
                - duration_seconds: int (parsed duration in seconds)
                - view_count: int
                - like_count: int (may be None if hidden)
                - comment_count: int (may be None if disabled)
                - tags: list[str] (may be empty)
                - category_id: str
                - thumbnails: dict (with keys: default, medium, high, standard, maxres)
                - fetched_at: str (ISO 8601 timestamp)

        Raises:
            HttpError: If API request fails
            ValueError: If video not found
        """
        request = self.youtube.videos().list(
            part="snippet,statistics,contentDetails",
            id=video_id,
        )
        response = request.execute()

        if not response.get("items"):
            raise ValueError(f"Video not found: {video_id}")

        video = response["items"][0]
        snippet = video["snippet"]
        statistics = video.get("statistics", {})
        content_details = video["contentDetails"]

        # Parse duration to seconds
        duration_iso = content_details["duration"]
        duration_seconds = self._parse_duration_to_seconds(duration_iso)

        metadata = {
            "video_id": video_id,
            "title": snippet["title"],
            "description": snippet.get("description", ""),
            "published_at": snippet["publishedAt"],
            "channel_id": snippet["channelId"],
            "channel_title": snippet["channelTitle"],
            "duration": duration_iso,
            "duration_seconds": duration_seconds,
            "view_count": int(statistics.get("viewCount", 0)),
            "like_count": int(statistics["likeCount"]) if "likeCount" in statistics else None,
            "comment_count": int(statistics["commentCount"]) if "commentCount" in statistics else None,
            "tags": snippet.get("tags", []),
            "category_id": snippet.get("categoryId"),
            "thumbnails": snippet.get("thumbnails", {}),
            "fetched_at": datetime.now().isoformat(),
        }

        return metadata

    def fetch_metadata_safe(self, video_id: str) -> Tuple[Optional[dict], Optional[str]]:
        """Fetch metadata with error handling.

        Args:
            video_id: YouTube video ID

        Returns:
            Tuple of (metadata_dict, error_string)
            - If successful: (metadata, None)
            - If failed: (None, error_message)
        """
        try:
            metadata = self.fetch_metadata(video_id)
            return metadata, None
        except HttpError as e:
            error_msg = f"YouTube API error: {e}"
            return None, error_msg
        except ValueError as e:
            error_msg = f"Video not found: {e}"
            return None, error_msg
        except Exception as e:
            error_msg = f"Unexpected error fetching metadata: {e}"
            return None, error_msg

    @staticmethod
    def _parse_duration_to_seconds(duration: str) -> int:
        """Parse ISO 8601 duration to seconds.

        Args:
            duration: ISO 8601 duration string (e.g., "PT15M33S", "PT1H2M3S")

        Returns:
            Duration in seconds

        Example:
            >>> YouTubeMetadataService._parse_duration_to_seconds("PT15M33S")
            933
            >>> YouTubeMetadataService._parse_duration_to_seconds("PT1H2M3S")
            3723
        """
        match = re.match(r'PT(?:(\d+)H)?(?:(\d+)M)?(?:(\d+)S)?', duration)
        if not match:
            return 0

        hours, minutes, seconds = match.groups()
        hours = int(hours) if hours else 0
        minutes = int(minutes) if minutes else 0
        seconds = int(seconds) if seconds else 0

        return hours * 3600 + minutes * 60 + seconds

    @staticmethod
    def format_duration(duration: str) -> str:
        """Format ISO 8601 duration to human-readable format.

        Args:
            duration: ISO 8601 duration string (e.g., "PT15M33S")

        Returns:
            Human-readable duration (e.g., "15:33" or "1:02:03")

        Example:
            >>> YouTubeMetadataService.format_duration("PT15M33S")
            '15:33'
            >>> YouTubeMetadataService.format_duration("PT1H2M3S")
            '1:02:03'
        """
        match = re.match(r'PT(?:(\d+)H)?(?:(\d+)M)?(?:(\d+)S)?', duration)
        if not match:
            return duration

        hours, minutes, seconds = match.groups()
        hours = int(hours) if hours else 0
        minutes = int(minutes) if minutes else 0
        seconds = int(seconds) if seconds else 0

        if hours > 0:
            return f"{hours}:{minutes:02d}:{seconds:02d}"
        else:
            return f"{minutes}:{seconds:02d}"


def fetch_video_metadata(video_id: str) -> Tuple[Optional[dict], Optional[str]]:
    """Convenience function to fetch video metadata.

    Creates service instance and fetches metadata with error handling.

    Args:
        video_id: YouTube video ID

    Returns:
        Tuple of (metadata_dict, error_string)
        - If successful: (metadata, None)
        - If failed: (None, error_message)

    Example:
        >>> metadata, error = fetch_video_metadata("dQw4w9WgXcQ")
        >>> if metadata:
        ...     print(f"Title: {metadata['title']}")
    """
    try:
        service = YouTubeMetadataService()
        return service.fetch_metadata_safe(video_id)
    except ValueError as e:
        return None, str(e)
