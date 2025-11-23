"""Archive writer implementations for storing expensive-to-fetch content."""

import json
from datetime import datetime
from pathlib import Path
from typing import Optional, Protocol

from .models import YouTubeArchive


class ArchiveWriter(Protocol):
    """Protocol for archiving expensive-to-fetch content.

    Implementations must provide methods to:
    - Archive content that costs time/money to fetch
    - Check if content already exists
    - Retrieve archived content
    - Update archives with new LLM outputs or processing records
    """

    def archive_youtube_video(
        self,
        video_id: str,
        url: str,
        transcript: str,
        metadata: Optional[dict] = None,
    ) -> Path:
        """Archive YouTube video data.

        Args:
            video_id: YouTube video ID
            url: Full YouTube URL
            transcript: Raw transcript text
            metadata: Optional YouTube metadata (title, upload_date, channel, etc.)

        Returns:
            Path to archive file
        """
        ...

    def exists(self, video_id: str) -> bool:
        """Check if video already archived.

        Args:
            video_id: YouTube video ID

        Returns:
            True if archive exists, False otherwise
        """
        ...

    def get(self, video_id: str) -> Optional[YouTubeArchive]:
        """Retrieve archived video data.

        Args:
            video_id: YouTube video ID

        Returns:
            YouTubeArchive if found, None otherwise
        """
        ...

    def update(self, video_id: str, archive: YouTubeArchive) -> Path:
        """Update existing archive with new data.

        Args:
            video_id: YouTube video ID
            archive: Updated archive object

        Returns:
            Path to updated archive file
        """
        ...


class LocalArchiveWriter:
    """Local filesystem implementation of ArchiveWriter.

    Stores archives as JSON files organized by month:
        compose/data/archive/youtube/2024-11/VIDEO_ID.json

    Archives are stored in plain JSON (not compressed) for transparency.
    Compression can be added later if disk space becomes an issue.
    """

    def __init__(self, base_dir: Optional[Path] = None):
        """Initialize local archive writer.

        Args:
            base_dir: Base directory for archives (default: compose/data/archive)
        """
        if base_dir is None:
            # Default to compose/data/archive in project root
            # Navigate up from lesson-007/archive/ to project root
            base_dir = Path(__file__).parent.parent.parent.parent / "compose" / "data" / "archive"

        self.base_dir = Path(base_dir)
        self.youtube_dir = self.base_dir / "youtube"
        self.youtube_dir.mkdir(parents=True, exist_ok=True)

    def _get_month_dir(self, dt: Optional[datetime] = None) -> Path:
        """Get directory for a specific month.

        Args:
            dt: Datetime to use for month (default: now)

        Returns:
            Path to month directory (e.g., youtube/2024-11/)
        """
        if dt is None:
            dt = datetime.now()

        month_str = dt.strftime("%Y-%m")
        month_dir = self.youtube_dir / month_str
        month_dir.mkdir(parents=True, exist_ok=True)
        return month_dir

    def _get_archive_path(self, video_id: str, dt: Optional[datetime] = None) -> Path:
        """Get path to archive file for a video.

        Args:
            video_id: YouTube video ID
            dt: Datetime for month directory (default: now)

        Returns:
            Path to archive file
        """
        month_dir = self._get_month_dir(dt)
        return month_dir / f"{video_id}.json"

    def archive_youtube_video(
        self,
        video_id: str,
        url: str,
        transcript: str,
        metadata: Optional[dict] = None,
    ) -> Path:
        """Archive YouTube video data.

        Args:
            video_id: YouTube video ID
            url: Full YouTube URL
            transcript: Raw transcript text
            metadata: Optional YouTube metadata

        Returns:
            Path to archive file
        """
        # Create archive object
        archive = YouTubeArchive(
            video_id=video_id,
            url=url,
            fetched_at=datetime.now(),
            raw_transcript=transcript,
            youtube_metadata=metadata or {},
        )

        # Get archive path
        archive_path = self._get_archive_path(video_id)

        # Write to file
        with open(archive_path, "w", encoding="utf-8") as f:
            json.dump(archive.model_dump(mode="json"), f, indent=2, default=str)

        return archive_path

    def exists(self, video_id: str) -> bool:
        """Check if video already archived.

        Searches all month directories for the video ID.

        Args:
            video_id: YouTube video ID

        Returns:
            True if archive exists, False otherwise
        """
        # Check all month directories
        for month_dir in self.youtube_dir.iterdir():
            if not month_dir.is_dir():
                continue

            archive_path = month_dir / f"{video_id}.json"
            if archive_path.exists():
                return True

        return False

    def get(self, video_id: str) -> Optional[YouTubeArchive]:
        """Retrieve archived video data.

        Searches all month directories for the video ID.

        Args:
            video_id: YouTube video ID

        Returns:
            YouTubeArchive if found, None otherwise
        """
        # Check all month directories
        for month_dir in self.youtube_dir.iterdir():
            if not month_dir.is_dir():
                continue

            archive_path = month_dir / f"{video_id}.json"
            if archive_path.exists():
                with open(archive_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                return YouTubeArchive(**data)

        return None

    def update(self, video_id: str, archive: YouTubeArchive) -> Path:
        """Update existing archive with new data.

        Args:
            video_id: YouTube video ID
            archive: Updated archive object

        Returns:
            Path to updated archive file

        Raises:
            FileNotFoundError: If archive doesn't exist
        """
        # Find existing archive
        existing = self.get(video_id)
        if existing is None:
            raise FileNotFoundError(f"Archive not found for video_id: {video_id}")

        # Use original fetch date for month directory
        archive_path = self._get_archive_path(video_id, existing.fetched_at)

        # Write updated archive
        with open(archive_path, "w", encoding="utf-8") as f:
            json.dump(archive.model_dump(mode="json"), f, indent=2, default=str)

        return archive_path

    def add_llm_output(
        self,
        video_id: str,
        output_type: str,
        output_value: str,
        model: str,
        cost_usd: Optional[float] = None,
        prompt_tokens: Optional[int] = None,
        completion_tokens: Optional[int] = None,
    ) -> Path:
        """Add LLM output to existing archive.

        Args:
            video_id: YouTube video ID
            output_type: Type of output (e.g., "tags", "summary")
            output_value: The generated output
            model: Model used (e.g., "claude-3-5-haiku-20241022")
            cost_usd: Optional cost in USD
            prompt_tokens: Optional prompt token count
            completion_tokens: Optional completion token count

        Returns:
            Path to updated archive file

        Raises:
            FileNotFoundError: If archive doesn't exist
        """
        archive = self.get(video_id)
        if archive is None:
            raise FileNotFoundError(f"Archive not found for video_id: {video_id}")

        archive.add_llm_output(
            output_type=output_type,
            output_value=output_value,
            model=model,
            cost_usd=cost_usd,
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
        )

        return self.update(video_id, archive)

    def add_processing_record(
        self,
        video_id: str,
        version: str,
        collection_name: Optional[str] = None,
        notes: Optional[str] = None,
    ) -> Path:
        """Add processing record to existing archive.

        Args:
            video_id: YouTube video ID
            version: Processing version (e.g., "v1_full_embed", "v2_chunked")
            collection_name: Optional Qdrant collection name
            notes: Optional notes about processing

        Returns:
            Path to updated archive file

        Raises:
            FileNotFoundError: If archive doesn't exist
        """
        archive = self.get(video_id)
        if archive is None:
            raise FileNotFoundError(f"Archive not found for video_id: {video_id}")

        archive.add_processing_record(
            version=version,
            collection_name=collection_name,
            notes=notes,
        )

        return self.update(video_id, archive)

    def count(self) -> int:
        """Count total number of archived videos.

        Returns:
            Total count of archived videos
        """
        count = 0
        for month_dir in self.youtube_dir.iterdir():
            if not month_dir.is_dir():
                continue
            count += len(list(month_dir.glob("*.json")))
        return count
