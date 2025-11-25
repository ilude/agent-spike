"""Tests for compose/cli/validate_migration.py migration validation script."""

import json
from datetime import datetime
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest


@pytest.fixture
def mock_archive_dir(tmp_path):
    """Create mock archive directory with test files."""
    archive_dir = tmp_path / "archive" / "youtube" / "2025-11"
    archive_dir.mkdir(parents=True)

    # Create 5 test archive files
    for i in range(5):
        video_id = f"test_video_{i}"
        archive_file = archive_dir / f"{video_id}.json"
        archive_data = {
            "video_id": video_id,
            "url": f"https://youtube.com/watch?v={video_id}",
            "youtube_metadata": {
                "title": f"Test Video {i}",
                "channel_title": f"Test Channel {i}",
            },
            "llm_outputs": [],
        }
        archive_file.write_text(json.dumps(archive_data))

    return tmp_path / "archive" / "youtube"


@pytest.fixture
def mock_video_records():
    """Create mock video records from SurrealDB."""
    records = []
    for i in range(5):
        records.append({
            "video_id": f"test_video_{i}",
            "url": f"https://youtube.com/watch?v=test_video_{i}",
            "title": f"Test Video {i}",
            "channel_name": f"Test Channel {i}",
            "embedding": [0.1] * 1024,  # 1024-dimensional embedding
            "archive_path": f"archive/youtube/2025-11/test_video_{i}.json",
            "fetched_at": datetime.now(),
            "created_at": datetime.now(),
            "updated_at": datetime.now(),
        })
    return records


class TestCountValidation:
    """Test counting archives vs SurrealDB records."""

    def test_count_archive_files(self, mock_archive_dir):
        """Test counting archive files in directory."""
        from compose.cli.validate_migration import count_archive_files

        count = count_archive_files(mock_archive_dir)
        assert count == 5

    def test_count_archive_files_empty_dir(self, tmp_path):
        """Test counting with empty directory."""
        from compose.cli.validate_migration import count_archive_files

        empty_dir = tmp_path / "empty"
        empty_dir.mkdir()
        count = count_archive_files(empty_dir)
        assert count == 0

    @pytest.mark.asyncio
    async def test_get_surrealdb_count(self):
        """Test getting video count from SurrealDB."""
        from compose.cli.validate_migration import get_surrealdb_count

        with patch("compose.cli.validate_migration.repository.get_video_count") as mock_count:
            mock_count.return_value = 42
            count = await get_surrealdb_count()
            assert count == 42


class TestEmbeddingValidation:
    """Test embedding validation logic."""

    @pytest.mark.asyncio
    async def test_validate_video_with_valid_embedding(self, mock_video_records):
        """Test validating a video with correct embedding."""
        from compose.cli.validate_migration import validate_video_embedding

        video = mock_video_records[0]
        with patch("compose.cli.validate_migration.repository.get_video") as mock_get:
            mock_get.return_value = MagicMock(**video)

            result = await validate_video_embedding("test_video_0")
            assert result["has_embedding"] is True
            assert result["embedding_dimension"] == 1024
            assert result["dimension_correct"] is True

    @pytest.mark.asyncio
    async def test_validate_video_missing_embedding(self):
        """Test validating a video without embedding."""
        from compose.cli.validate_migration import validate_video_embedding

        video = {
            "video_id": "test_video_0",
            "embedding": None,
        }
        with patch("compose.cli.validate_migration.repository.get_video") as mock_get:
            mock_get.return_value = MagicMock(**video)

            result = await validate_video_embedding("test_video_0")
            assert result["has_embedding"] is False
            assert result["embedding_dimension"] is None
            assert result["dimension_correct"] is False

    @pytest.mark.asyncio
    async def test_validate_video_wrong_dimension(self):
        """Test validating a video with wrong embedding dimension."""
        from compose.cli.validate_migration import validate_video_embedding

        video = {
            "video_id": "test_video_0",
            "embedding": [0.1] * 512,  # Wrong dimension
        }
        with patch("compose.cli.validate_migration.repository.get_video") as mock_get:
            mock_get.return_value = MagicMock(**video)

            result = await validate_video_embedding("test_video_0")
            assert result["has_embedding"] is True
            assert result["embedding_dimension"] == 512
            assert result["dimension_correct"] is False


class TestMetadataValidation:
    """Test metadata field validation."""

    @pytest.mark.asyncio
    async def test_validate_complete_metadata(self, mock_video_records):
        """Test validating video with complete metadata."""
        from compose.cli.validate_migration import validate_video_metadata

        video = mock_video_records[0]
        with patch("compose.cli.validate_migration.repository.get_video") as mock_get:
            mock_get.return_value = MagicMock(**video)

            result = await validate_video_metadata("test_video_0")
            assert result["has_video_id"] is True
            assert result["has_title"] is True
            assert result["has_url"] is True
            assert result["has_channel_name"] is True
            assert result["has_archive_path"] is True
            assert result["missing_fields"] == []

    @pytest.mark.asyncio
    async def test_validate_incomplete_metadata(self):
        """Test validating video with missing metadata fields."""
        from compose.cli.validate_migration import validate_video_metadata

        video = {
            "video_id": "test_video_0",
            "url": "https://youtube.com/watch?v=test_video_0",
            "title": None,  # Missing
            "channel_name": None,  # Missing
            "archive_path": None,  # Missing
        }
        with patch("compose.cli.validate_migration.repository.get_video") as mock_get:
            mock_get.return_value = MagicMock(**video)

            result = await validate_video_metadata("test_video_0")
            assert result["has_video_id"] is True
            assert result["has_title"] is False
            assert result["has_url"] is True
            assert result["has_channel_name"] is False
            assert result["has_archive_path"] is False
            assert set(result["missing_fields"]) == {"title", "channel_name", "archive_path"}


class TestRandomSampling:
    """Test random video sampling."""

    @pytest.mark.asyncio
    async def test_get_random_video_ids(self):
        """Test getting random video IDs from SurrealDB."""
        from compose.cli.validate_migration import get_random_video_ids

        mock_ids = ["video_1", "video_2", "video_3"]
        with patch("compose.cli.validate_migration.repository.get_random_video_ids") as mock_random:
            mock_random.return_value = mock_ids

            result = await get_random_video_ids(3)
            assert result == mock_ids
            mock_random.assert_called_once_with(3)


class TestReportGeneration:
    """Test validation report generation."""

    def test_generate_report_all_valid(self):
        """Test report generation with all valid videos."""
        from compose.cli.validate_migration import generate_validation_report

        validation_results = {
            "archive_count": 100,
            "surrealdb_count": 100,
            "missing_videos": [],
            "videos_without_embeddings": [],
            "videos_with_wrong_dimension": [],
            "videos_with_missing_metadata": [],
        }

        report = generate_validation_report(validation_results)

        assert report["total_archives"] == 100
        assert report["total_surrealdb"] == 100
        assert report["count_match"] is True
        assert report["missing_count"] == 0
        assert report["embedding_issues"] == 0
        assert report["metadata_issues"] == 0
        assert report["health_percentage"] == 100.0

    def test_generate_report_with_issues(self):
        """Test report generation with validation issues."""
        from compose.cli.validate_migration import generate_validation_report

        validation_results = {
            "archive_count": 100,
            "surrealdb_count": 95,
            "missing_videos": ["video_1", "video_2", "video_3", "video_4", "video_5"],
            "videos_without_embeddings": ["video_6", "video_7"],
            "videos_with_wrong_dimension": ["video_8"],
            "videos_with_missing_metadata": ["video_9", "video_10"],
        }

        report = generate_validation_report(validation_results)

        assert report["total_archives"] == 100
        assert report["total_surrealdb"] == 95
        assert report["count_match"] is False
        assert report["missing_count"] == 5
        assert report["embedding_issues"] == 3  # 2 without + 1 wrong dimension
        assert report["metadata_issues"] == 2
        assert report["health_percentage"] < 100.0


class TestCLICommands:
    """Test CLI command interface."""

    @pytest.mark.asyncio
    async def test_quick_command(self):
        """Test quick validation command."""
        from compose.cli.validate_migration import quick_validate

        with patch("compose.cli.validate_migration.count_archive_files") as mock_count_archive, \
             patch("compose.cli.validate_migration.get_surrealdb_count") as mock_count_db:

            mock_count_archive.return_value = 100
            mock_count_db.return_value = 100

            await quick_validate()

            mock_count_archive.assert_called_once()
            mock_count_db.assert_called_once()

    @pytest.mark.asyncio
    async def test_sample_command(self, mock_video_records):
        """Test sample validation command."""
        from compose.cli.validate_migration import sample_validate

        mock_ids = ["test_video_0", "test_video_1", "test_video_2"]

        with patch("compose.cli.validate_migration.get_random_video_ids") as mock_random, \
             patch("compose.cli.validate_migration.validate_video_embedding") as mock_embedding, \
             patch("compose.cli.validate_migration.validate_video_metadata") as mock_metadata:

            mock_random.return_value = mock_ids
            mock_embedding.return_value = {
                "has_embedding": True,
                "embedding_dimension": 1024,
                "dimension_correct": True,
            }
            mock_metadata.return_value = {
                "has_video_id": True,
                "has_title": True,
                "has_url": True,
                "has_channel_name": True,
                "has_archive_path": True,
                "missing_fields": [],
            }

            await sample_validate(3)

            mock_random.assert_called_once_with(3)
            assert mock_embedding.call_count == 3
            assert mock_metadata.call_count == 3
