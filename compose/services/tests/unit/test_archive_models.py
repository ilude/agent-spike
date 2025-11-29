"""Tests for archive models and configuration.

Focuses on:
- Factory functions for creating readers/writers
- YouTubeArchive model methods
- ArchiveConfig validation
- ImportMetadata handling

Run with: uv run pytest compose/services/tests/unit/test_archive_models.py -v
"""

from datetime import datetime

import pytest

from compose.services.archive import (
    ArchiveConfig,
    LocalArchiveWriter,
    YouTubeArchive,
    create_local_archive_reader,
    create_local_archive_writer,
)
from compose.services.archive.models import ChannelContext, ImportMetadata


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
