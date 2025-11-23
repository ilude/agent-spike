"""Tests for archive manager module.

Focuses on:
- ArchiveManager coordination logic
- Reader functions with flat structure and error handling
- Writer functions including derived outputs and update methods

Run with: uv run pytest compose/services/tests/unit/test_archive_manager.py -v
"""

import json
from datetime import datetime
from pathlib import Path

import pytest

from compose.services.archive import (
    ArchiveConfig,
    LocalArchiveReader,
    LocalArchiveWriter,
    YouTubeArchive,
    create_local_archive_reader,
    create_local_archive_writer,
)
from compose.services.archive.manager import ArchiveManager, create_archive_manager
from compose.services.archive.models import ImportMetadata, ChannelContext
from unittest.mock import patch, MagicMock


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


# =============================================================================
# LocalArchiveReader Additional Tests
# =============================================================================


class TestLocalArchiveReaderFlatStructure:
    """Tests for LocalArchiveReader with flat (non-month) structure."""

    @pytest.mark.unit
    def test_iter_flat_structure(self, temp_dir):
        """Test iterating archives in flat structure."""
        config = ArchiveConfig(base_dir=temp_dir, organize_by_month=False)
        writer = LocalArchiveWriter(config)

        for i in range(3):
            writer.archive_youtube_video(
                video_id=f"flat{i}",
                url=f"https://youtube.com/watch?v=flat{i}",
                transcript=f"Flat test {i}",
            )

        reader = LocalArchiveReader(config)
        videos = list(reader.iter_youtube_videos())

        assert len(videos) == 3
        assert reader.count() == 3

    @pytest.mark.unit
    def test_get_flat_structure(self, temp_dir):
        """Test getting specific archive in flat structure."""
        config = ArchiveConfig(base_dir=temp_dir, organize_by_month=False)
        writer = LocalArchiveWriter(config)

        writer.archive_youtube_video(
            video_id="flat_get",
            url="https://youtube.com/watch?v=flat_get",
            transcript="Flat get test",
        )

        reader = LocalArchiveReader(config)
        archive = reader.get("flat_get")

        assert archive is not None
        assert archive.video_id == "flat_get"

    @pytest.mark.unit
    def test_get_nonexistent_flat(self, temp_dir):
        """Test getting nonexistent archive in flat structure."""
        config = ArchiveConfig(base_dir=temp_dir, organize_by_month=False)
        writer = LocalArchiveWriter(config)
        reader = LocalArchiveReader(config)

        assert reader.get("nonexistent") is None

    @pytest.mark.unit
    def test_month_counts_empty_for_flat(self, temp_dir):
        """Test get_month_counts returns empty for flat structure."""
        config = ArchiveConfig(base_dir=temp_dir, organize_by_month=False)
        reader = LocalArchiveReader(config)

        assert reader.get_month_counts() == {}


class TestLocalArchiveReaderMonthStructure:
    """Tests for LocalArchiveReader with month-organized structure edge cases."""

    @pytest.mark.unit
    def test_get_ignores_non_dir_files(self, temp_dir):
        """Test reader.get() ignores non-directory files when searching months."""
        config = ArchiveConfig(base_dir=temp_dir, organize_by_month=True)
        writer = LocalArchiveWriter(config)

        # Create a valid archive
        writer.archive_youtube_video(
            video_id="valid_video",
            url="https://youtube.com/watch?v=valid_video",
            transcript="Valid transcript",
        )

        # Add a non-directory file in youtube root
        youtube_dir = temp_dir / "youtube"
        (youtube_dir / "not_a_dir.json").write_text("{}", encoding="utf-8")

        reader = LocalArchiveReader(config)

        # Should find the valid video despite non-dir file
        archive = reader.get("valid_video")
        assert archive is not None
        assert archive.video_id == "valid_video"

    @pytest.mark.unit
    def test_get_returns_none_when_not_found_in_any_month(self, temp_dir):
        """Test reader.get() returns None when video not in any month dir."""
        config = ArchiveConfig(base_dir=temp_dir, organize_by_month=True)
        writer = LocalArchiveWriter(config)

        # Create an archive (creates month dir)
        writer.archive_youtube_video(
            video_id="existing",
            url="https://youtube.com/watch?v=existing",
            transcript="test",
        )

        reader = LocalArchiveReader(config)

        # Search for non-existent video
        result = reader.get("nonexistent_in_months")
        assert result is None

    @pytest.mark.unit
    def test_get_skips_non_dir_files_during_search(self, temp_dir):
        """Test reader.get() correctly skips non-directory files when searching."""
        config = ArchiveConfig(base_dir=temp_dir, organize_by_month=True)

        # Create youtube dir and month dir manually
        youtube_dir = temp_dir / "youtube"
        youtube_dir.mkdir(parents=True)

        # Add a non-directory file first (will be encountered during iteration)
        (youtube_dir / "stray_file.txt").write_text("stray", encoding="utf-8")

        # Create a valid archive in a month dir
        month_dir = youtube_dir / "2024-11"
        month_dir.mkdir()
        archive = YouTubeArchive(
            video_id="target_video",
            url="https://youtube.com/watch?v=target_video",
            fetched_at=datetime.now(),
            raw_transcript="test transcript",
        )
        archive_path = month_dir / "target_video.json"
        with open(archive_path, "w", encoding="utf-8") as f:
            json.dump(archive.model_dump(mode="json"), f, indent=2, default=str)

        reader = LocalArchiveReader(config)

        # Should find video despite stray file
        result = reader.get("target_video")
        assert result is not None
        assert result.video_id == "target_video"

        # Also verify non-existent returns None after checking all dirs
        assert reader.get("not_there") is None


class TestLocalArchiveReaderErrorHandling:
    """Tests for reader error handling."""

    @pytest.mark.unit
    def test_iter_skips_malformed_json(self, temp_dir, capsys):
        """Test that malformed JSON files are skipped with warning."""
        config = ArchiveConfig(base_dir=temp_dir, organize_by_month=False)
        writer = LocalArchiveWriter(config)

        # Create valid archive
        writer.archive_youtube_video(
            video_id="valid",
            url="https://youtube.com/watch?v=valid",
            transcript="Valid transcript",
        )

        # Manually create malformed JSON
        youtube_dir = temp_dir / "youtube"
        malformed_path = youtube_dir / "malformed.json"
        malformed_path.write_text("{invalid json", encoding="utf-8")

        reader = LocalArchiveReader(config)
        videos = list(reader.iter_youtube_videos())

        # Should get only the valid video
        assert len(videos) == 1
        assert videos[0].video_id == "valid"

        # Should have printed a warning
        captured = capsys.readouterr()
        assert "Warning" in captured.out
        assert "malformed.json" in captured.out

    @pytest.mark.unit
    def test_iter_skips_malformed_in_month_dirs(self, temp_dir, capsys):
        """Test malformed JSON in month directories is skipped."""
        config = ArchiveConfig(base_dir=temp_dir, organize_by_month=True)
        writer = LocalArchiveWriter(config)

        # Create valid archive
        writer.archive_youtube_video(
            video_id="valid_month",
            url="https://youtube.com/watch?v=valid_month",
            transcript="Valid transcript",
        )

        # Find month dir and add malformed file
        youtube_dir = temp_dir / "youtube"
        month_dir = list(youtube_dir.iterdir())[0]
        malformed_path = month_dir / "bad.json"
        malformed_path.write_text("not valid json!", encoding="utf-8")

        reader = LocalArchiveReader(config)
        videos = list(reader.iter_youtube_videos())

        assert len(videos) == 1
        captured = capsys.readouterr()
        assert "Warning" in captured.out

    @pytest.mark.unit
    def test_iter_empty_directory(self, temp_dir):
        """Test iterating when youtube directory doesn't exist."""
        config = ArchiveConfig(base_dir=temp_dir)
        reader = LocalArchiveReader(config)

        videos = list(reader.iter_youtube_videos())
        assert videos == []

    @pytest.mark.unit
    def test_get_empty_directory(self, temp_dir):
        """Test get when youtube directory doesn't exist."""
        config = ArchiveConfig(base_dir=temp_dir)
        reader = LocalArchiveReader(config)

        assert reader.get("any_id") is None

    @pytest.mark.unit
    def test_count_empty_directory(self, temp_dir):
        """Test count when youtube directory doesn't exist."""
        config = ArchiveConfig(base_dir=temp_dir)
        reader = LocalArchiveReader(config)

        assert reader.count() == 0

    @pytest.mark.unit
    def test_month_counts_empty_directory(self, temp_dir):
        """Test get_month_counts when youtube directory doesn't exist."""
        config = ArchiveConfig(base_dir=temp_dir)
        reader = LocalArchiveReader(config)

        assert reader.get_month_counts() == {}


class TestLocalArchiveReaderDateFiltering:
    """Tests for date range filtering in iter_youtube_videos."""

    @pytest.mark.unit
    def test_filter_by_start_month(self, temp_dir):
        """Test filtering by start_month."""
        config = ArchiveConfig(base_dir=temp_dir)
        youtube_dir = temp_dir / "youtube"

        # Create archives in different months manually
        self._create_archive_in_month(youtube_dir, "2024-10", "vid_oct")
        self._create_archive_in_month(youtube_dir, "2024-11", "vid_nov")
        self._create_archive_in_month(youtube_dir, "2024-12", "vid_dec")

        reader = LocalArchiveReader(config)

        # Filter: start from November
        videos = list(reader.iter_youtube_videos(start_month="2024-11"))
        video_ids = [v.video_id for v in videos]

        assert len(videos) == 2
        assert "vid_oct" not in video_ids
        assert "vid_nov" in video_ids
        assert "vid_dec" in video_ids

    @pytest.mark.unit
    def test_filter_by_end_month(self, temp_dir):
        """Test filtering by end_month."""
        config = ArchiveConfig(base_dir=temp_dir)
        youtube_dir = temp_dir / "youtube"

        self._create_archive_in_month(youtube_dir, "2024-10", "vid_oct")
        self._create_archive_in_month(youtube_dir, "2024-11", "vid_nov")
        self._create_archive_in_month(youtube_dir, "2024-12", "vid_dec")

        reader = LocalArchiveReader(config)

        # Filter: end at November
        videos = list(reader.iter_youtube_videos(end_month="2024-11"))
        video_ids = [v.video_id for v in videos]

        assert len(videos) == 2
        assert "vid_oct" in video_ids
        assert "vid_nov" in video_ids
        assert "vid_dec" not in video_ids

    @pytest.mark.unit
    def test_filter_by_date_range(self, temp_dir):
        """Test filtering by both start and end month."""
        config = ArchiveConfig(base_dir=temp_dir)
        youtube_dir = temp_dir / "youtube"

        self._create_archive_in_month(youtube_dir, "2024-09", "vid_sep")
        self._create_archive_in_month(youtube_dir, "2024-10", "vid_oct")
        self._create_archive_in_month(youtube_dir, "2024-11", "vid_nov")
        self._create_archive_in_month(youtube_dir, "2024-12", "vid_dec")

        reader = LocalArchiveReader(config)

        # Filter: Oct to Nov only
        videos = list(
            reader.iter_youtube_videos(start_month="2024-10", end_month="2024-11")
        )
        video_ids = [v.video_id for v in videos]

        assert len(videos) == 2
        assert "vid_sep" not in video_ids
        assert "vid_oct" in video_ids
        assert "vid_nov" in video_ids
        assert "vid_dec" not in video_ids

    def _create_archive_in_month(self, youtube_dir: Path, month: str, video_id: str):
        """Helper to create archive in specific month directory."""
        month_dir = youtube_dir / month
        month_dir.mkdir(parents=True, exist_ok=True)

        archive = YouTubeArchive(
            video_id=video_id,
            url=f"https://youtube.com/watch?v={video_id}",
            fetched_at=datetime.now(),
            raw_transcript=f"Transcript for {video_id}",
        )

        archive_path = month_dir / f"{video_id}.json"
        with open(archive_path, "w", encoding="utf-8") as f:
            json.dump(archive.model_dump(mode="json"), f, indent=2, default=str)


class TestLocalArchiveReaderNonDirFiles:
    """Test reader handles non-directory items in youtube folder."""

    @pytest.mark.unit
    def test_count_ignores_files_in_youtube_root(self, temp_dir):
        """Test that count ignores loose files in youtube dir."""
        config = ArchiveConfig(base_dir=temp_dir)
        writer = LocalArchiveWriter(config)

        # Create valid archive (in month dir)
        writer.archive_youtube_video(
            video_id="valid",
            url="https://youtube.com/watch?v=valid",
            transcript="Valid",
        )

        # Add a stray file in youtube root (not in month dir)
        youtube_dir = temp_dir / "youtube"
        stray_file = youtube_dir / "stray.txt"
        stray_file.write_text("not a json", encoding="utf-8")

        reader = LocalArchiveReader(config)
        assert reader.count() == 1  # Only counts archive in month dir

    @pytest.mark.unit
    def test_month_counts_ignores_files(self, temp_dir):
        """Test get_month_counts ignores non-directory items."""
        config = ArchiveConfig(base_dir=temp_dir)
        writer = LocalArchiveWriter(config)

        writer.archive_youtube_video(
            video_id="valid",
            url="https://youtube.com/watch?v=valid",
            transcript="Valid",
        )

        # Add stray file
        youtube_dir = temp_dir / "youtube"
        (youtube_dir / ".DS_Store").write_text("", encoding="utf-8")

        reader = LocalArchiveReader(config)
        counts = reader.get_month_counts()

        # Should only have the one month, not .DS_Store
        assert len(counts) == 1
        assert all(len(k) == 7 for k in counts.keys())  # YYYY-MM format


# =============================================================================
# LocalArchiveWriter Additional Tests
# =============================================================================


class TestLocalArchiveWriterMonthStructureEdgeCases:
    """Tests for writer month-organized edge cases."""

    @pytest.mark.unit
    def test_exists_ignores_non_dir_files(self, temp_dir):
        """Test exists() skips non-directory items when searching months."""
        config = ArchiveConfig(base_dir=temp_dir, organize_by_month=True)
        writer = LocalArchiveWriter(config)

        # Create a valid archive
        writer.archive_youtube_video(
            video_id="exists_test",
            url="https://youtube.com/watch?v=exists_test",
            transcript="test",
        )

        # Add non-directory file in youtube root
        youtube_dir = temp_dir / "youtube"
        (youtube_dir / "metadata.json").write_text("{}", encoding="utf-8")

        # Should still find the archive
        assert writer.exists("exists_test") is True
        # Should return False for non-existent (not crash)
        assert writer.exists("not_there") is False

    @pytest.mark.unit
    def test_get_ignores_non_dir_files(self, temp_dir):
        """Test get() skips non-directory items when searching months."""
        config = ArchiveConfig(base_dir=temp_dir, organize_by_month=True)
        writer = LocalArchiveWriter(config)

        # Create a valid archive
        writer.archive_youtube_video(
            video_id="get_month_test",
            url="https://youtube.com/watch?v=get_month_test",
            transcript="test transcript",
        )

        # Add non-directory file in youtube root
        youtube_dir = temp_dir / "youtube"
        (youtube_dir / ".gitkeep").write_text("", encoding="utf-8")

        # Should still retrieve the archive
        archive = writer.get("get_month_test")
        assert archive is not None
        assert archive.video_id == "get_month_test"

        # Non-existent should return None
        assert writer.get("nonexistent") is None


class TestLocalArchiveWriterFlatStructure:
    """Tests for writer with flat structure."""

    @pytest.mark.unit
    def test_exists_flat_structure(self, temp_dir):
        """Test exists() in flat structure."""
        config = ArchiveConfig(base_dir=temp_dir, organize_by_month=False)
        writer = LocalArchiveWriter(config)

        writer.archive_youtube_video(
            video_id="flat_exists",
            url="https://youtube.com/watch?v=flat_exists",
            transcript="test",
        )

        assert writer.exists("flat_exists") is True
        assert writer.exists("nonexistent") is False

    @pytest.mark.unit
    def test_get_flat_structure(self, temp_dir):
        """Test get() in flat structure."""
        config = ArchiveConfig(base_dir=temp_dir, organize_by_month=False)
        writer = LocalArchiveWriter(config)

        writer.archive_youtube_video(
            video_id="flat_get",
            url="https://youtube.com/watch?v=flat_get",
            transcript="test transcript",
        )

        archive = writer.get("flat_get")
        assert archive is not None
        assert archive.video_id == "flat_get"
        assert writer.get("nonexistent") is None

    @pytest.mark.unit
    def test_count_flat_structure(self, temp_dir):
        """Test count() in flat structure."""
        config = ArchiveConfig(base_dir=temp_dir, organize_by_month=False)
        writer = LocalArchiveWriter(config)

        for i in range(3):
            writer.archive_youtube_video(
                video_id=f"flat{i}",
                url=f"https://youtube.com/watch?v=flat{i}",
                transcript=f"test {i}",
            )

        assert writer.count() == 3


class TestLocalArchiveWriterUpdate:
    """Tests for writer update() method."""

    @pytest.mark.unit
    def test_update_existing_archive(self, temp_dir):
        """Test updating an existing archive."""
        config = ArchiveConfig(base_dir=temp_dir)
        writer = LocalArchiveWriter(config)

        video_id = "update_test"
        writer.archive_youtube_video(
            video_id=video_id,
            url="https://youtube.com/watch?v=update_test",
            transcript="Original transcript",
        )

        # Get, modify, update
        archive = writer.get(video_id)
        archive.raw_transcript = "Modified transcript"

        result_path = writer.update(video_id, archive)

        assert result_path.exists()
        updated = writer.get(video_id)
        assert updated.raw_transcript == "Modified transcript"

    @pytest.mark.unit
    def test_update_nonexistent_raises(self, temp_dir):
        """Test update() raises FileNotFoundError for missing archive."""
        config = ArchiveConfig(base_dir=temp_dir)
        writer = LocalArchiveWriter(config)

        archive = YouTubeArchive(
            video_id="nonexistent",
            url="https://youtube.com/watch?v=nonexistent",
            fetched_at=datetime.now(),
            raw_transcript="test",
        )

        with pytest.raises(FileNotFoundError) as exc_info:
            writer.update("nonexistent", archive)

        assert "nonexistent" in str(exc_info.value)


class TestLocalArchiveWriterDerivedOutput:
    """Tests for add_derived_output() method."""

    @pytest.mark.unit
    def test_add_derived_output(self, temp_dir):
        """Test adding derived output to archive."""
        config = ArchiveConfig(base_dir=temp_dir)
        writer = LocalArchiveWriter(config)

        video_id = "derived_test"
        writer.archive_youtube_video(
            video_id=video_id,
            url="https://youtube.com/watch?v=derived_test",
            transcript="test transcript",
        )

        manifest = {"transformer": "1.0.0", "normalizer": "2.0.0"}

        result_path = writer.add_derived_output(
            video_id=video_id,
            output_type="normalized_metadata_v1",
            output_value='{"normalized": "data"}',
            transformer_version="1.0.0",
            transform_manifest=manifest,
            source_outputs=["tags", "summary"],
        )

        assert result_path.exists()

        archive = writer.get(video_id)
        assert len(archive.derived_outputs) == 1

        derived = archive.derived_outputs[0]
        assert derived.output_type == "normalized_metadata_v1"
        assert derived.output_value == '{"normalized": "data"}'
        assert derived.transformer_version == "1.0.0"
        assert derived.transform_manifest == manifest
        assert derived.source_outputs == ["tags", "summary"]

    @pytest.mark.unit
    def test_add_derived_output_nonexistent_raises(self, temp_dir):
        """Test add_derived_output raises for missing archive."""
        config = ArchiveConfig(base_dir=temp_dir)
        writer = LocalArchiveWriter(config)

        with pytest.raises(FileNotFoundError):
            writer.add_derived_output(
                video_id="nonexistent",
                output_type="test",
                output_value="test",
                transformer_version="1.0",
                transform_manifest={},
            )

    @pytest.mark.unit
    def test_add_multiple_derived_outputs(self, temp_dir):
        """Test adding multiple derived outputs to same archive."""
        config = ArchiveConfig(base_dir=temp_dir)
        writer = LocalArchiveWriter(config)

        video_id = "multi_derived"
        writer.archive_youtube_video(
            video_id=video_id,
            url="https://youtube.com/watch?v=multi_derived",
            transcript="test",
        )

        writer.add_derived_output(
            video_id=video_id,
            output_type="output_v1",
            output_value="first",
            transformer_version="1.0",
            transform_manifest={"v": "1"},
        )

        writer.add_derived_output(
            video_id=video_id,
            output_type="output_v2",
            output_value="second",
            transformer_version="2.0",
            transform_manifest={"v": "2"},
        )

        archive = writer.get(video_id)
        assert len(archive.derived_outputs) == 2


class TestLocalArchiveWriterErrorCases:
    """Tests for writer error handling."""

    @pytest.mark.unit
    def test_add_llm_output_nonexistent_raises(self, temp_dir):
        """Test add_llm_output raises for missing archive."""
        config = ArchiveConfig(base_dir=temp_dir)
        writer = LocalArchiveWriter(config)

        with pytest.raises(FileNotFoundError):
            writer.add_llm_output(
                video_id="nonexistent",
                output_type="tags",
                output_value="test",
                model="test-model",
            )

    @pytest.mark.unit
    def test_add_processing_record_nonexistent_raises(self, temp_dir):
        """Test add_processing_record raises for missing archive."""
        config = ArchiveConfig(base_dir=temp_dir)
        writer = LocalArchiveWriter(config)

        with pytest.raises(FileNotFoundError):
            writer.add_processing_record(
                video_id="nonexistent",
                version="v1",
            )


class TestLocalArchiveWriterCountWithNonDirs:
    """Test writer count handles non-directory items."""

    @pytest.mark.unit
    def test_count_ignores_files_in_youtube_root(self, temp_dir):
        """Test count ignores files in youtube root (month-organized mode)."""
        config = ArchiveConfig(base_dir=temp_dir, organize_by_month=True)
        writer = LocalArchiveWriter(config)

        writer.archive_youtube_video(
            video_id="counted",
            url="https://youtube.com/watch?v=counted",
            transcript="test",
        )

        # Add stray file
        youtube_dir = temp_dir / "youtube"
        (youtube_dir / "metadata.json").write_text("{}", encoding="utf-8")

        assert writer.count() == 1


class TestLocalArchiveWriterMonthDir:
    """Tests for _get_month_dir() behavior."""

    @pytest.mark.unit
    def test_get_month_dir_flat_returns_youtube_dir(self, temp_dir):
        """Test _get_month_dir returns youtube_dir in flat mode."""
        config = ArchiveConfig(base_dir=temp_dir, organize_by_month=False)
        writer = LocalArchiveWriter(config)

        month_dir = writer._get_month_dir()
        assert month_dir == writer.youtube_dir

    @pytest.mark.unit
    def test_get_month_dir_with_custom_date(self, temp_dir):
        """Test _get_month_dir with custom datetime."""
        config = ArchiveConfig(base_dir=temp_dir, organize_by_month=True)
        writer = LocalArchiveWriter(config)

        custom_date = datetime(2023, 6, 15)
        month_dir = writer._get_month_dir(custom_date)

        assert month_dir.name == "2023-06"
        assert month_dir.exists()


# =============================================================================
# Factory Function Tests
# =============================================================================


class TestFactoryFunctions:
    """Tests for factory functions."""

    @pytest.mark.unit
    def test_create_local_archive_writer_with_custom_dir(self, temp_dir):
        """Test create_local_archive_writer with custom directory."""
        writer = create_local_archive_writer(temp_dir)
        assert writer.config.base_dir == temp_dir
        assert writer.config.organize_by_month is True

    @pytest.mark.unit
    def test_create_local_archive_reader_with_custom_dir(self, temp_dir):
        """Test create_local_archive_reader with custom directory."""
        reader = create_local_archive_reader(temp_dir)
        assert reader.config.base_dir == temp_dir
        assert reader.config.organize_by_month is True

    @pytest.mark.unit
    def test_create_local_archive_reader_with_default_dir(self):
        """Test create_local_archive_reader with default directory."""
        reader = create_local_archive_reader()
        # Should use project default path
        assert reader.config.base_dir.name == "archive"
        assert "compose" in str(reader.config.base_dir) or "data" in str(
            reader.config.base_dir
        )
        assert reader.config.organize_by_month is True


# =============================================================================
# YouTubeArchive Model Tests
# =============================================================================


class TestYouTubeArchiveModel:
    """Tests for YouTubeArchive model methods."""

    @pytest.mark.unit
    def test_get_latest_output_returns_most_recent(self):
        """Test get_latest_output returns most recent by timestamp."""
        archive = YouTubeArchive(
            video_id="test",
            url="https://youtube.com/watch?v=test",
            fetched_at=datetime.now(),
            raw_transcript="test",
        )

        # Add multiple outputs of same type
        archive.add_llm_output("tags", "first", "model-1", cost_usd=0.01)
        archive.add_llm_output("tags", "second", "model-1", cost_usd=0.01)
        archive.add_llm_output("tags", "third", "model-1", cost_usd=0.01)

        latest = archive.get_latest_output("tags")
        assert latest is not None
        assert latest.output_value == "third"

    @pytest.mark.unit
    def test_get_latest_output_returns_none_for_missing_type(self):
        """Test get_latest_output returns None for nonexistent type."""
        archive = YouTubeArchive(
            video_id="test",
            url="https://youtube.com/watch?v=test",
            fetched_at=datetime.now(),
            raw_transcript="test",
        )

        assert archive.get_latest_output("nonexistent") is None

    @pytest.mark.unit
    def test_get_latest_derived_output(self):
        """Test get_latest_derived_output returns most recent."""
        archive = YouTubeArchive(
            video_id="test",
            url="https://youtube.com/watch?v=test",
            fetched_at=datetime.now(),
            raw_transcript="test",
        )

        archive.add_derived_output("norm", "v1", "1.0", {})
        archive.add_derived_output("norm", "v2", "2.0", {})

        latest = archive.get_latest_derived_output("norm")
        assert latest is not None
        assert latest.output_value == "v2"

    @pytest.mark.unit
    def test_get_latest_derived_output_none(self):
        """Test get_latest_derived_output returns None for missing type."""
        archive = YouTubeArchive(
            video_id="test",
            url="https://youtube.com/watch?v=test",
            fetched_at=datetime.now(),
            raw_transcript="test",
        )

        assert archive.get_latest_derived_output("missing") is None

    @pytest.mark.unit
    def test_total_llm_cost_with_none_costs(self):
        """Test total_llm_cost handles None costs correctly."""
        archive = YouTubeArchive(
            video_id="test",
            url="https://youtube.com/watch?v=test",
            fetched_at=datetime.now(),
            raw_transcript="test",
        )

        archive.add_llm_output("tags", "value", "model", cost_usd=0.01)
        archive.add_llm_output("summary", "value", "model", cost_usd=None)
        archive.add_llm_output("other", "value", "model", cost_usd=0.02)

        total = archive.total_llm_cost()
        assert abs(total - 0.03) < 0.0001


# =============================================================================
# Config Validation Tests
# =============================================================================


class TestArchiveConfig:
    """Tests for ArchiveConfig validation."""

    @pytest.mark.unit
    def test_valid_compression_gzip(self, temp_dir):
        """Test gzip compression is valid."""
        config = ArchiveConfig(base_dir=temp_dir, compression="gzip")
        assert config.compression == "gzip"

    @pytest.mark.unit
    def test_valid_compression_bz2(self, temp_dir):
        """Test bz2 compression is valid."""
        config = ArchiveConfig(base_dir=temp_dir, compression="bz2")
        assert config.compression == "bz2"

    @pytest.mark.unit
    def test_valid_compression_none(self, temp_dir):
        """Test None compression is valid."""
        config = ArchiveConfig(base_dir=temp_dir, compression=None)
        assert config.compression is None

    @pytest.mark.unit
    def test_invalid_compression_raises(self, temp_dir):
        """Test invalid compression raises ValueError."""
        with pytest.raises(ValueError) as exc_info:
            ArchiveConfig(base_dir=temp_dir, compression="invalid")

        assert "Invalid compression" in str(exc_info.value)


# =============================================================================
# Import Metadata Tests
# =============================================================================


class TestImportMetadata:
    """Tests for ImportMetadata handling."""

    @pytest.mark.unit
    def test_archive_with_import_metadata(self, temp_dir):
        """Test archiving with import metadata."""
        config = ArchiveConfig(base_dir=temp_dir)
        writer = LocalArchiveWriter(config)

        import_meta = ImportMetadata(
            source_type="bulk_channel",
            imported_at=datetime.now(),
            import_method="scheduled",
            channel_context=ChannelContext(
                channel_id="UC123",
                channel_name="Test Channel",
                is_bulk_import=True,
            ),
            recommendation_weight=0.5,
        )

        writer.archive_youtube_video(
            video_id="import_test",
            url="https://youtube.com/watch?v=import_test",
            transcript="test",
            import_metadata=import_meta,
        )

        archive = writer.get("import_test")
        assert archive.import_metadata is not None
        assert archive.import_metadata.source_type == "bulk_channel"
        assert archive.import_metadata.channel_context.channel_name == "Test Channel"
        assert archive.import_metadata.recommendation_weight == 0.5
