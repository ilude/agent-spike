"""Archive manager for reading and updating YouTube archive files.

This module provides high-level operations for managing YouTube archives,
handling both creation and updates. It supports order-independent merging
where either transcript or metadata can be added first.
"""

import json
from datetime import datetime
from pathlib import Path
from typing import Optional
import tempfile
import shutil

from .models import YouTubeArchive, ImportMetadata
from .local_writer import LocalArchiveWriter


class ArchiveManager:
    """Manages YouTube archive creation and updates with safe merging.

    Provides high-level operations for:
    - Creating archives with partial data (transcript OR metadata)
    - Merging new data into existing archives
    - Atomic writes to prevent corruption
    - Order-independent updates (transcript/metadata can be added in any order)

    Example:
        >>> manager = ArchiveManager()
        >>>
        >>> # Add transcript first
        >>> manager.update_transcript(video_id, url, transcript)
        >>>
        >>> # Add metadata later (merges with existing)
        >>> manager.update_metadata(video_id, metadata_dict)
        >>>
        >>> # Or reverse order - metadata first, transcript later
        >>> manager.update_metadata(video_id, metadata_dict)
        >>> manager.update_transcript(video_id, url, transcript)
    """

    def __init__(self, writer: Optional[LocalArchiveWriter] = None):
        """Initialize archive manager.

        Args:
            writer: Optional LocalArchiveWriter instance (creates default if None)
        """
        if writer is None:
            from .local_writer import create_local_archive_writer
            writer = create_local_archive_writer()

        self.writer = writer

    def update_transcript(
        self,
        video_id: str,
        url: str,
        transcript: str,
        timed_transcript: Optional[list[dict]] = None,
        import_metadata: Optional[ImportMetadata] = None,
    ) -> Path:
        """Add or update transcript data in archive.

        If archive exists, merges transcript into existing data.
        If archive doesn't exist, creates new archive with transcript.

        Args:
            video_id: YouTube video ID
            url: Full YouTube URL
            transcript: Raw transcript text
            timed_transcript: Optional timed transcript data
            import_metadata: Optional import tracking metadata

        Returns:
            Path to archive file
        """
        existing = self.writer.get(video_id)

        if existing:
            # Merge with existing archive
            existing.raw_transcript = transcript
            if timed_transcript:
                existing.timed_transcript = timed_transcript
            if import_metadata:
                existing.import_metadata = import_metadata

            return self._atomic_update(video_id, existing)
        else:
            # Create new archive with transcript
            archive = YouTubeArchive(
                video_id=video_id,
                url=url,
                fetched_at=datetime.now(),
                raw_transcript=transcript,
                timed_transcript=timed_transcript,
                import_metadata=import_metadata,
            )

            return self._atomic_write(video_id, archive)

    def update_metadata(
        self,
        video_id: str,
        url: str,
        metadata: dict,
    ) -> Path:
        """Add or update YouTube metadata in archive.

        If archive exists, merges metadata into existing data.
        If archive doesn't exist, creates minimal archive with metadata only.

        Args:
            video_id: YouTube video ID
            url: Full YouTube URL
            metadata: YouTube metadata dict (title, description, etc.)

        Returns:
            Path to archive file
        """
        existing = self.writer.get(video_id)

        if existing:
            # Merge with existing metadata
            existing.youtube_metadata.update(metadata)
            return self._atomic_update(video_id, existing)
        else:
            # Create minimal archive with metadata only
            # Use empty string for transcript (will be filled later)
            archive = YouTubeArchive(
                video_id=video_id,
                url=url,
                fetched_at=datetime.now(),
                raw_transcript="",  # Will be updated when transcript is fetched
                youtube_metadata=metadata,
            )

            return self._atomic_write(video_id, archive)

    def get(self, video_id: str) -> Optional[YouTubeArchive]:
        """Retrieve archive for video.

        Args:
            video_id: YouTube video ID

        Returns:
            YouTubeArchive if exists, None otherwise
        """
        return self.writer.get(video_id)

    def exists(self, video_id: str) -> bool:
        """Check if archive exists for video.

        Args:
            video_id: YouTube video ID

        Returns:
            True if archive exists, False otherwise
        """
        return self.writer.exists(video_id)

    def _atomic_write(self, video_id: str, archive: YouTubeArchive) -> Path:
        """Write archive atomically to prevent corruption.

        Uses temp file + rename pattern for atomic write.

        Args:
            video_id: YouTube video ID
            archive: Archive to write

        Returns:
            Path to archive file
        """
        # Get target path
        archive_path = self.writer._get_archive_path(video_id)

        # Write to temp file first
        temp_fd, temp_path = tempfile.mkstemp(
            suffix='.json',
            dir=archive_path.parent,
            text=True,
        )

        try:
            with open(temp_fd, 'w', encoding='utf-8') as f:
                json.dump(archive.model_dump(mode='json'), f, indent=2, default=str)

            # Atomic rename
            shutil.move(temp_path, archive_path)

            return archive_path
        except Exception:
            # Clean up temp file on error
            Path(temp_path).unlink(missing_ok=True)
            raise

    def _atomic_update(self, video_id: str, archive: YouTubeArchive) -> Path:
        """Update existing archive atomically.

        Args:
            video_id: YouTube video ID
            archive: Updated archive

        Returns:
            Path to archive file
        """
        # For updates, we use the same atomic write pattern
        return self._atomic_write(video_id, archive)


def create_archive_manager(writer: Optional[LocalArchiveWriter] = None) -> ArchiveManager:
    """Factory function to create ArchiveManager with sensible defaults.

    Args:
        writer: Optional LocalArchiveWriter instance

    Returns:
        Configured ArchiveManager instance

    Example:
        >>> # Use defaults
        >>> manager = create_archive_manager()
        >>>
        >>> # Custom writer
        >>> from .local_writer import create_local_archive_writer
        >>> writer = create_local_archive_writer(custom_base_dir)
        >>> manager = create_archive_manager(writer)
    """
    return ArchiveManager(writer)
