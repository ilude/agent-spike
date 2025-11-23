"""Archive reader for reprocessing workflows."""

import json
from pathlib import Path
from typing import Iterator, Optional, Protocol

from .models import YouTubeArchive


class ArchiveReader(Protocol):
    """Protocol for reading archived content.

    Used for reprocessing workflows where you need to:
    - Iterate through all archived content
    - Filter by date, metadata, etc.
    - Rebuild caches with new strategies
    """

    def iter_youtube_videos(
        self,
        start_month: Optional[str] = None,
        end_month: Optional[str] = None,
    ) -> Iterator[YouTubeArchive]:
        """Iterate through all archived YouTube videos.

        Args:
            start_month: Optional start month (e.g., "2024-10")
            end_month: Optional end month (e.g., "2024-11")

        Yields:
            YouTubeArchive objects
        """
        ...

    def get(self, video_id: str) -> Optional[YouTubeArchive]:
        """Retrieve specific archived video.

        Args:
            video_id: YouTube video ID

        Returns:
            YouTubeArchive if found, None otherwise
        """
        ...


class LocalArchiveReader:
    """Local filesystem implementation of ArchiveReader.

    Reads archives from JSON files organized by month.
    """

    def __init__(self, base_dir: Optional[Path] = None):
        """Initialize local archive reader.

        Args:
            base_dir: Base directory for archives (default: compose/data/archive)
        """
        if base_dir is None:
            # Default to compose/data/archive in project root
            base_dir = Path(__file__).parent.parent.parent.parent / "compose" / "data" / "archive"

        self.base_dir = Path(base_dir)
        self.youtube_dir = self.base_dir / "youtube"

    def iter_youtube_videos(
        self,
        start_month: Optional[str] = None,
        end_month: Optional[str] = None,
    ) -> Iterator[YouTubeArchive]:
        """Iterate through all archived YouTube videos.

        Args:
            start_month: Optional start month (e.g., "2024-10")
            end_month: Optional end month (e.g., "2024-11")

        Yields:
            YouTubeArchive objects
        """
        if not self.youtube_dir.exists():
            return

        # Get all month directories
        month_dirs = sorted([d for d in self.youtube_dir.iterdir() if d.is_dir()])

        # Filter by date range if specified
        if start_month:
            month_dirs = [d for d in month_dirs if d.name >= start_month]
        if end_month:
            month_dirs = [d for d in month_dirs if d.name <= end_month]

        # Iterate through all JSON files
        for month_dir in month_dirs:
            for archive_path in sorted(month_dir.glob("*.json")):
                try:
                    with open(archive_path, "r", encoding="utf-8") as f:
                        data = json.load(f)
                    yield YouTubeArchive(**data)
                except Exception as e:
                    print(f"Warning: Failed to load {archive_path}: {e}")
                    continue

    def get(self, video_id: str) -> Optional[YouTubeArchive]:
        """Retrieve specific archived video.

        Args:
            video_id: YouTube video ID

        Returns:
            YouTubeArchive if found, None otherwise
        """
        if not self.youtube_dir.exists():
            return None

        # Search all month directories
        for month_dir in self.youtube_dir.iterdir():
            if not month_dir.is_dir():
                continue

            archive_path = month_dir / f"{video_id}.json"
            if archive_path.exists():
                with open(archive_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                return YouTubeArchive(**data)

        return None

    def count(self) -> int:
        """Count total number of archived videos.

        Returns:
            Total count
        """
        if not self.youtube_dir.exists():
            return 0

        count = 0
        for month_dir in self.youtube_dir.iterdir():
            if not month_dir.is_dir():
                continue
            count += len(list(month_dir.glob("*.json")))
        return count

    def get_month_counts(self) -> dict[str, int]:
        """Get video counts by month.

        Returns:
            Dictionary mapping month string to count
        """
        if not self.youtube_dir.exists():
            return {}

        counts = {}
        for month_dir in sorted(self.youtube_dir.iterdir()):
            if not month_dir.is_dir():
                continue
            counts[month_dir.name] = len(list(month_dir.glob("*.json")))

        return counts

    def get_total_llm_cost(self) -> float:
        """Calculate total LLM cost across all archives.

        Returns:
            Total cost in USD
        """
        total = 0.0
        for archive in self.iter_youtube_videos():
            total += archive.total_llm_cost()
        return total
