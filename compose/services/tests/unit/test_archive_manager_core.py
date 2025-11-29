"""Tests for ArchiveManager coordination logic.

Focuses on:
- ArchiveManager update_transcript method
- ArchiveManager update_metadata method
- ArchiveManager get and exists methods
- Factory function for ArchiveManager
- Atomic write behavior

Run with: uv run pytest compose/services/tests/unit/test_archive_manager_core.py -v
"""

import json
from datetime import datetime
from unittest.mock import patch

import pytest

from compose.services.archive import ArchiveConfig, LocalArchiveWriter
from compose.services.archive.manager import ArchiveManager, create_archive_manager
from compose.services.archive.models import ImportMetadata


# =============================================================================
# ArchiveManager Tests
# =============================================================================


class TestArchiveManagerUpdateTranscript:
    """Tests for ArchiveManager.update_transcript()."""

    @pytest.mark.unit
    def test_update_transcript_new_archive(self, temp_dir):
        """Test creating a new archive with transcript."""
        config = ArchiveConfig(base_dir=temp_dir)
        writer = LocalArchiveWriter(config)
        manager = ArchiveManager(writer=writer)

        video_id = "new_transcript_test"
        url = "https://www.youtube.com/watch?v=new_transcript_test"
        transcript = "This is a brand new transcript."

        result_path = manager.update_transcript(
            video_id=video_id,
            url=url,
            transcript=transcript,
        )

        assert result_path.exists()
        archive = manager.get(video_id)
        assert archive is not None
        assert archive.video_id == video_id
        assert archive.url == url
        assert archive.raw_transcript == transcript
        assert archive.timed_transcript is None
        assert archive.import_metadata is None

    @pytest.mark.unit
    def test_update_transcript_with_timed_transcript(self, temp_dir):
        """Test creating archive with timed transcript."""
        config = ArchiveConfig(base_dir=temp_dir)
        writer = LocalArchiveWriter(config)
        manager = ArchiveManager(writer=writer)

        video_id = "timed_test"
        timed_data = [
            {"text": "Hello", "start": 0.0, "duration": 1.0},
            {"text": "world", "start": 1.0, "duration": 1.0},
        ]

        manager.update_transcript(
            video_id=video_id,
            url="https://www.youtube.com/watch?v=timed_test",
            transcript="Hello world",
            timed_transcript=timed_data,
        )

        archive = manager.get(video_id)
        assert archive.timed_transcript == timed_data

    @pytest.mark.unit
    def test_update_transcript_with_import_metadata(self, temp_dir):
        """Test creating archive with import metadata."""
        config = ArchiveConfig(base_dir=temp_dir)
        writer = LocalArchiveWriter(config)
        manager = ArchiveManager(writer=writer)

        video_id = "import_meta_test"
        import_meta = ImportMetadata(
            source_type="single_import",
            imported_at=datetime.now(),
            import_method="cli",
            recommendation_weight=1.0,
        )

        manager.update_transcript(
            video_id=video_id,
            url="https://www.youtube.com/watch?v=import_meta_test",
            transcript="Test transcript",
            import_metadata=import_meta,
        )

        archive = manager.get(video_id)
        assert archive.import_metadata is not None
        assert archive.import_metadata.source_type == "single_import"
        assert archive.import_metadata.recommendation_weight == 1.0

    @pytest.mark.unit
    def test_update_transcript_merges_with_existing(self, temp_dir):
        """Test updating transcript in existing archive preserves metadata."""
        config = ArchiveConfig(base_dir=temp_dir)
        writer = LocalArchiveWriter(config)
        manager = ArchiveManager(writer=writer)

        video_id = "merge_test"
        url = "https://www.youtube.com/watch?v=merge_test"

        # First, create archive with metadata only
        manager.update_metadata(
            video_id=video_id,
            url=url,
            metadata={"title": "Test Video", "channel": "Test Channel"},
        )

        # Verify initial state
        archive = manager.get(video_id)
        assert archive.raw_transcript == ""  # Empty until transcript added
        assert archive.youtube_metadata["title"] == "Test Video"

        # Now update with transcript
        manager.update_transcript(
            video_id=video_id,
            url=url,
            transcript="New transcript content",
        )

        # Verify merged state
        archive = manager.get(video_id)
        assert archive.raw_transcript == "New transcript content"
        assert archive.youtube_metadata["title"] == "Test Video"

    @pytest.mark.unit
    def test_update_transcript_replaces_existing_transcript(self, temp_dir):
        """Test that update_transcript replaces old transcript."""
        config = ArchiveConfig(base_dir=temp_dir)
        writer = LocalArchiveWriter(config)
        manager = ArchiveManager(writer=writer)

        video_id = "replace_test"
        url = "https://www.youtube.com/watch?v=replace_test"

        manager.update_transcript(video_id, url, "Original transcript")
        manager.update_transcript(video_id, url, "Updated transcript")

        archive = manager.get(video_id)
        assert archive.raw_transcript == "Updated transcript"

    @pytest.mark.unit
    def test_update_existing_archive_with_timed_and_import_metadata(self, temp_dir):
        """Test updating existing archive adds timed_transcript and import_metadata."""
        config = ArchiveConfig(base_dir=temp_dir)
        writer = LocalArchiveWriter(config)
        manager = ArchiveManager(writer=writer)

        video_id = "update_existing_full"
        url = "https://www.youtube.com/watch?v=update_existing_full"

        # Create initial archive
        manager.update_transcript(video_id, url, "Initial transcript")

        # Update with timed transcript and import metadata
        timed_data = [{"text": "Hello", "start": 0.0, "duration": 1.5}]
        import_meta = ImportMetadata(
            source_type="single_import",
            imported_at=datetime.now(),
            import_method="cli",
            recommendation_weight=1.0,
        )

        manager.update_transcript(
            video_id=video_id,
            url=url,
            transcript="Updated transcript",
            timed_transcript=timed_data,
            import_metadata=import_meta,
        )

        archive = manager.get(video_id)
        assert archive.raw_transcript == "Updated transcript"
        assert archive.timed_transcript == timed_data
        assert archive.import_metadata is not None
        assert archive.import_metadata.source_type == "single_import"


class TestArchiveManagerUpdateMetadata:
    """Tests for ArchiveManager.update_metadata()."""

    @pytest.mark.unit
    def test_update_metadata_new_archive(self, temp_dir):
        """Test creating new archive with metadata only."""
        config = ArchiveConfig(base_dir=temp_dir)
        writer = LocalArchiveWriter(config)
        manager = ArchiveManager(writer=writer)

        video_id = "metadata_only"
        url = "https://www.youtube.com/watch?v=metadata_only"
        metadata = {"title": "Metadata Test", "duration": 300}

        result_path = manager.update_metadata(
            video_id=video_id,
            url=url,
            metadata=metadata,
        )

        assert result_path.exists()
        archive = manager.get(video_id)
        assert archive.video_id == video_id
        assert archive.raw_transcript == ""  # Empty placeholder
        assert archive.youtube_metadata["title"] == "Metadata Test"
        assert archive.youtube_metadata["duration"] == 300

    @pytest.mark.unit
    def test_update_metadata_merges_with_existing(self, temp_dir):
        """Test updating metadata merges with existing data."""
        config = ArchiveConfig(base_dir=temp_dir)
        writer = LocalArchiveWriter(config)
        manager = ArchiveManager(writer=writer)

        video_id = "metadata_merge"
        url = "https://www.youtube.com/watch?v=metadata_merge"

        # Create with transcript first
        manager.update_transcript(video_id, url, "Some transcript")

        # Add metadata
        manager.update_metadata(video_id, url, {"title": "First Update"})

        # Add more metadata (should merge)
        manager.update_metadata(video_id, url, {"channel": "Second Update"})

        archive = manager.get(video_id)
        assert archive.raw_transcript == "Some transcript"
        assert archive.youtube_metadata["title"] == "First Update"
        assert archive.youtube_metadata["channel"] == "Second Update"

    @pytest.mark.unit
    def test_update_metadata_overwrites_same_keys(self, temp_dir):
        """Test that metadata update overwrites existing keys."""
        config = ArchiveConfig(base_dir=temp_dir)
        writer = LocalArchiveWriter(config)
        manager = ArchiveManager(writer=writer)

        video_id = "overwrite_test"
        url = "https://www.youtube.com/watch?v=overwrite_test"

        manager.update_metadata(video_id, url, {"title": "Original"})
        manager.update_metadata(video_id, url, {"title": "Updated"})

        archive = manager.get(video_id)
        assert archive.youtube_metadata["title"] == "Updated"


class TestArchiveManagerGetAndExists:
    """Tests for ArchiveManager.get() and exists()."""

    @pytest.mark.unit
    def test_get_existing_archive(self, temp_dir):
        """Test get() returns archive when it exists."""
        config = ArchiveConfig(base_dir=temp_dir)
        writer = LocalArchiveWriter(config)
        manager = ArchiveManager(writer=writer)

        video_id = "get_test"
        manager.update_transcript(
            video_id, "https://youtube.com/watch?v=get_test", "test"
        )

        archive = manager.get(video_id)
        assert archive is not None
        assert archive.video_id == video_id

    @pytest.mark.unit
    def test_get_nonexistent_archive(self, temp_dir):
        """Test get() returns None for nonexistent archive."""
        config = ArchiveConfig(base_dir=temp_dir)
        writer = LocalArchiveWriter(config)
        manager = ArchiveManager(writer=writer)

        assert manager.get("nonexistent") is None

    @pytest.mark.unit
    def test_exists_true(self, temp_dir):
        """Test exists() returns True for existing archive."""
        config = ArchiveConfig(base_dir=temp_dir)
        writer = LocalArchiveWriter(config)
        manager = ArchiveManager(writer=writer)

        video_id = "exists_test"
        manager.update_transcript(video_id, "https://youtube.com/watch?v=x", "test")

        assert manager.exists(video_id) is True

    @pytest.mark.unit
    def test_exists_false(self, temp_dir):
        """Test exists() returns False for nonexistent archive."""
        config = ArchiveConfig(base_dir=temp_dir)
        writer = LocalArchiveWriter(config)
        manager = ArchiveManager(writer=writer)

        assert manager.exists("nonexistent") is False


class TestArchiveManagerFactory:
    """Tests for create_archive_manager() factory function."""

    @pytest.mark.unit
    def test_create_with_default_writer(self):
        """Test factory creates manager with default writer."""
        manager = create_archive_manager()
        assert manager is not None
        assert manager.writer is not None

    @pytest.mark.unit
    def test_create_with_custom_writer(self, temp_dir):
        """Test factory accepts custom writer."""
        config = ArchiveConfig(base_dir=temp_dir)
        custom_writer = LocalArchiveWriter(config)

        manager = create_archive_manager(writer=custom_writer)
        assert manager.writer is custom_writer


class TestArchiveManagerAtomicWrite:
    """Tests for atomic write behavior."""

    @pytest.mark.unit
    def test_atomic_write_cleans_up_temp_on_error(self, temp_dir):
        """Test that temp file is cleaned up if write fails."""
        config = ArchiveConfig(base_dir=temp_dir)
        writer = LocalArchiveWriter(config)
        manager = ArchiveManager(writer=writer)

        video_id = "atomic_test"
        url = "https://youtube.com/watch?v=atomic_test"

        # Mock json.dump to raise an error after temp file is created
        with patch("compose.services.archive.manager.json.dump") as mock_dump:
            mock_dump.side_effect = ValueError("Simulated serialization error")

            with pytest.raises(ValueError):
                manager.update_transcript(video_id, url, "test")

        # Verify no temp files left behind
        youtube_dir = temp_dir / "youtube"
        if youtube_dir.exists():
            # Check for temp files (should be cleaned up)
            temp_files = list(youtube_dir.glob("**/*.json.tmp"))
            assert len(temp_files) == 0

            # Check no partial archives created
            assert not manager.exists(video_id)
