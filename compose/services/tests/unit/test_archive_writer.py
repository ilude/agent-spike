"""Tests for LocalArchiveWriter.

Focuses on:
- Writer with month-organized structure edge cases
- Writer with flat structure
- Update method behavior
- Derived output functionality
- Error handling
- Non-directory file handling
- Month directory behavior

Run with: uv run pytest compose/services/tests/unit/test_archive_writer.py -v
"""

from datetime import datetime

import pytest

from compose.services.archive import (
    ArchiveConfig,
    LocalArchiveWriter,
    YouTubeArchive,
)


# =============================================================================
# LocalArchiveWriter Tests
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
