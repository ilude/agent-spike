#!/usr/bin/env python3
"""
YouTube channel data caching tool.

Caches YouTube video and channel data in SQLite to minimize API calls.
Queries YouTube Data API only for uncached videos.
"""

import os
import sqlite3
from datetime import datetime, timedelta
from pathlib import Path

from googleapiclient.discovery import build
from tools.dotenv import load_root_env


class YouTubeCache:
    """Manages YouTube channel data caching."""

    def __init__(self, cache_db_path: str = "channel_cache.db", api_key: str | None = None):
        """
        Initialize the cache.

        Args:
            cache_db_path: Path to SQLite cache database
            api_key: YouTube API key (uses YOUTUBE_API_KEY env var if not provided)
        """
        # Load .env file from git repository root
        load_root_env()

        self.cache_db = Path(cache_db_path)
        self.api_key = api_key or os.getenv("YOUTUBE_API_KEY")

        if not self.api_key:
            raise ValueError("YOUTUBE_API_KEY not found. Set it in .env or environment.")

        self.youtube = build("youtube", "v3", developerKey=self.api_key)
        self._init_db()

    def _init_db(self) -> None:
        """Initialize SQLite database with cache tables."""
        conn = sqlite3.connect(self.cache_db)
        cursor = conn.cursor()

        # Videos table: caches video metadata
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS videos (
                video_id TEXT PRIMARY KEY,
                title TEXT,
                channel_id TEXT,
                channel_name TEXT,
                cached_at TIMESTAMP
            )
        """)

        # Channels table: caches channel metadata
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS channels (
                channel_id TEXT PRIMARY KEY,
                channel_name TEXT,
                description TEXT,
                subscriber_count INTEGER,
                view_count INTEGER,
                video_count INTEGER,
                cached_at TIMESTAMP
            )
        """)

        # Video tags table: stores AI-generated tags for videos
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS video_tags (
                video_id TEXT PRIMARY KEY,
                tags TEXT,
                summary TEXT,
                tagged_at TIMESTAMP,
                FOREIGN KEY (video_id) REFERENCES videos(video_id)
            )
        """)

        # Channel tags table: aggregated tags for channels
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS channel_tags (
                channel_id TEXT PRIMARY KEY,
                tags TEXT,
                tag_frequency TEXT,
                updated_at TIMESTAMP,
                FOREIGN KEY (channel_id) REFERENCES channels(channel_id)
            )
        """)

        conn.commit()
        conn.close()

    def get_channel_info(self, video_id: str, use_cache: bool = True) -> dict | None:
        """
        Get channel info for a video.

        Checks cache first, then queries API if needed.

        Args:
            video_id: YouTube video ID
            use_cache: Whether to use cached data (default: True)

        Returns:
            Dict with channel_id, channel_name, or None if not found
        """
        # Check cache first
        if use_cache:
            cached = self._get_from_cache(video_id)
            if cached:
                return cached

        # Fetch from API
        try:
            channel_info = self._fetch_from_api(video_id)
            if channel_info:
                self._cache_result(video_id, channel_info)
                return channel_info
        except Exception as e:
            print(f"Error fetching data for video {video_id}: {e}")

        return None

    def _get_from_cache(self, video_id: str) -> dict | None:
        """Get video info from cache if available."""
        conn = sqlite3.connect(self.cache_db)
        cursor = conn.cursor()

        cursor.execute("""
            SELECT video_id, title, channel_id, channel_name, cached_at
            FROM videos
            WHERE video_id = ?
        """, (video_id,))

        row = cursor.fetchone()
        conn.close()

        if row:
            return {
                "video_id": row[0],
                "title": row[1],
                "channel_id": row[2],
                "channel_name": row[3],
                "cached": True,
            }

        return None

    def _fetch_from_api(self, video_id: str) -> dict | None:
        """Fetch video and channel info from YouTube API."""
        try:
            # Get video info
            videos_response = self.youtube.videos().list(
                part="snippet",
                id=video_id,
            ).execute()

            if not videos_response.get("items"):
                return None

            video_item = videos_response["items"][0]
            snippet = video_item.get("snippet", {})

            channel_id = snippet.get("channelId")
            channel_name = snippet.get("channelTitle")
            title = snippet.get("title")

            return {
                "video_id": video_id,
                "title": title,
                "channel_id": channel_id,
                "channel_name": channel_name,
                "cached": False,
            }

        except Exception as e:
            print(f"API error for video {video_id}: {e}")
            return None

    def _cache_result(self, video_id: str, channel_info: dict) -> None:
        """Store video info in cache."""
        conn = sqlite3.connect(self.cache_db)
        cursor = conn.cursor()

        now = datetime.now().isoformat()

        cursor.execute("""
            INSERT OR REPLACE INTO videos
            (video_id, title, channel_id, channel_name, cached_at)
            VALUES (?, ?, ?, ?, ?)
        """, (
            video_id,
            channel_info.get("title"),
            channel_info.get("channel_id"),
            channel_info.get("channel_name"),
            now,
        ))

        conn.commit()
        conn.close()

    def is_cached(self, video_id: str) -> bool:
        """Check if video info is cached."""
        return self._get_from_cache(video_id) is not None

    def clear_cache(self) -> None:
        """Clear all cached data."""
        if self.cache_db.exists():
            self.cache_db.unlink()
        self._init_db()

    def get_cache_stats(self) -> dict:
        """Get cache statistics."""
        conn = sqlite3.connect(self.cache_db)
        cursor = conn.cursor()

        cursor.execute("SELECT COUNT(*) FROM videos")
        video_count = cursor.fetchone()[0]

        cursor.execute("SELECT COUNT(*) FROM channels")
        channel_count = cursor.fetchone()[0]

        conn.close()

        return {
            "cached_videos": video_count,
            "cached_channels": channel_count,
        }
