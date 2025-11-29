"""Tests for LocalArchiveReader.

Focuses on:
- Reader with flat structure
- Reader with month-organized structure
- Error handling during reading
- Date filtering functionality
- Handling non-directory files

Run with: uv run pytest compose/services/tests/unit/test_archive_reader.py -v
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
)


# =============================================================================
# LocalArchiveReader Tests
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
