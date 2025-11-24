"""
Video import service with deduplication logic.

Handles importing video watch history from multiple sources (Brave, Google Takeout)
into SurrealDB with proper deduplication.
"""

import asyncio
import sys
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import List, Optional

# Add project root to path
project_root = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(project_root))

from compose.lib.env_loader import load_root_env
from compose.services.surrealdb.config import SurrealDBConfig
from surrealdb import AsyncSurreal


@dataclass
class ImportResult:
    """Results from importing videos."""

    total_videos: int = 0
    new_videos: int = 0
    existing_videos: int = 0
    new_signals: int = 0
    duplicate_signals: int = 0
    errors: int = 0


class VideoImporter:
    """Import video watch history into SurrealDB."""

    def __init__(self, db: AsyncSurreal, user_id: str = "default_user"):
        self.db = db
        self.user_id = user_id

    async def import_video_ids(
        self, video_ids: List[str], source: str, signal_type: str = "watched"
    ) -> ImportResult:
        """
        Import video IDs from a source with deduplication.

        Args:
            video_ids: List of YouTube video IDs
            source: Source of the data ('brave', 'takeout', etc.)
            signal_type: Type of signal ('watched', 'thumbs_up', etc.)

        Returns:
            ImportResult with stats
        """
        result = ImportResult(total_videos=len(video_ids))

        for video_id in video_ids:
            try:
                # Check if video already exists in video_rec
                video_exists = await self._video_exists(video_id)

                if not video_exists:
                    # Create minimal video record
                    await self._create_video_record(video_id)
                    result.new_videos += 1
                else:
                    result.existing_videos += 1

                # Check if signal already exists
                signal_exists = await self._signal_exists(
                    video_id, signal_type, source
                )

                if not signal_exists:
                    # Create user signal
                    await self._create_signal(video_id, signal_type, source)
                    result.new_signals += 1
                else:
                    result.duplicate_signals += 1

            except Exception as e:
                print(f"Error importing {video_id}: {e}")
                result.errors += 1

        return result

    async def _video_exists(self, video_id: str) -> bool:
        """Check if video exists in video_rec table."""
        query = "SELECT * FROM video_rec WHERE video_id = $video_id LIMIT 1"
        response = await self.db.query(query, {"video_id": video_id})

        # Response is a list of results, each with a 'result' key
        return len(response) > 0 and len(response[0].get("result", [])) > 0

    async def _create_video_record(self, video_id: str) -> None:
        """Create minimal video record (will be enriched later)."""
        query = """
        CREATE video_rec CONTENT {
            video_id: $video_id,
            url: $url,
            title: $title,
            channel_id: "",
            channel_name: "",
            thumbnail_url: "",
            duration_seconds: 0,
            view_count: 0,
            upload_date: time::now(),
            tags: [],
            categories: [],
            created_at: time::now(),
            updated_at: time::now()
        }
        """
        await self.db.query(
            query,
            {
                "video_id": video_id,
                "url": f"https://www.youtube.com/watch?v={video_id}",
                "title": f"Video {video_id} (title pending)",
            },
        )

    async def _signal_exists(
        self, video_id: str, signal_type: str, source: str
    ) -> bool:
        """Check if signal already exists for this user/video/type/source."""
        query = """
        SELECT * FROM user_video_signal
        WHERE user_id = $user_id
        AND video_id = $video_id
        AND signal_type = $signal_type
        AND source = $source
        LIMIT 1
        """
        response = await self.db.query(
            query,
            {
                "user_id": self.user_id,
                "video_id": video_id,
                "signal_type": signal_type,
                "source": source,
            },
        )
        return len(response) > 0 and len(response[0].get("result", [])) > 0

    async def _create_signal(
        self, video_id: str, signal_type: str, source: str
    ) -> None:
        """Create user video signal."""
        query = """
        CREATE user_video_signal CONTENT {
            user_id: $user_id,
            video_id: $video_id,
            signal_type: $signal_type,
            source: $source,
            timestamp: time::now(),
            metadata: {}
        }
        """
        await self.db.query(
            query,
            {
                "user_id": self.user_id,
                "video_id": video_id,
                "signal_type": signal_type,
                "source": source,
            },
        )


async def get_db_connection() -> AsyncSurreal:
    """Get connected SurrealDB instance."""
    load_root_env()
    config = SurrealDBConfig()
    config.validate()

    url = config.url.replace("ws://", "http://")
    db = AsyncSurreal(url)
    await db.use(config.namespace, config.database)
    await db.signin({"username": config.user, "password": config.password})

    return db
