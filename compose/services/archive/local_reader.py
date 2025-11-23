"""Local filesystem implementation of ArchiveReader protocol."""

import json
from pathlib import Path
from typing import Iterator, Optional

from .config import ArchiveConfig
from .models import YouTubeArchive


class LocalArchiveReader:
    """Local filesystem implementation of ArchiveReader.

    Reads archives from JSON files, optionally organized by month.
    """

    def __init__(self, config: ArchiveConfig):
        """Initialize local archive reader.

        Args:
            config: Archive configuration
        """
        self.config = config
        self.youtube_dir = config.base_dir / "youtube"

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

        if not self.config.organize_by_month:
            # Flat structure - yield all JSON files
            for archive_path in sorted(self.youtube_dir.glob("*.json")):
                try:
                    with open(archive_path, "r", encoding="utf-8") as f:
                        data = json.load(f)
                    yield YouTubeArchive(**data)
                except Exception as e:
                    print(f"Warning: Failed to load {archive_path}: {e}")
                    continue
            return

        # Month-organized structure
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

        if not self.config.organize_by_month:
            # Flat structure
            archive_path = self.youtube_dir / f"{video_id}.json"
            if archive_path.exists():
                with open(archive_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                return YouTubeArchive(**data)
            return None

        # Search month directories
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

        if not self.config.organize_by_month:
            return len(list(self.youtube_dir.glob("*.json")))

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
        if not self.youtube_dir.exists() or not self.config.organize_by_month:
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


def create_local_archive_reader(base_dir: Optional[Path] = None) -> LocalArchiveReader:
    """Factory function to create LocalArchiveReader with sensible defaults.

    Uses projects/data/archive as default base directory.

    Args:
        base_dir: Optional custom base directory

    Returns:
        Configured LocalArchiveReader instance

    Example:
        >>> # Use defaults
        >>> reader = create_local_archive_reader()
        >>> for video in reader.iter_youtube_videos():
        ...     print(video.video_id)
        >>>
        >>> # Custom location
        >>> reader = create_local_archive_reader(Path("/custom/archive"))
    """
    if base_dir is None:
        # Default to compose/data/archive in project root
        project_root = Path(__file__).parent.parent.parent.parent
        base_dir = project_root / "compose" / "data" / "archive"

    config = ArchiveConfig(base_dir=base_dir, organize_by_month=True)
    return LocalArchiveReader(config)
