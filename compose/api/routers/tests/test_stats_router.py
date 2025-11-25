"""Tests for stats router.

Run with: uv run pytest compose/api/routers/tests/test_stats_router.py
"""

import pytest
from unittest.mock import patch, MagicMock, AsyncMock
from pathlib import Path
import json
from datetime import datetime

from compose.api.routers.stats import (
    is_local_url,
    get_queue_stats,
    get_cache_stats,
    get_archive_stats,
    get_recent_activity,
    get_stats,
)


# -----------------------------------------------------------------------------
# is_local_url Tests
# -----------------------------------------------------------------------------


@pytest.mark.unit
class TestIsLocalUrl:
    """Test is_local_url helper function."""

    def test_localhost_returns_true(self):
        """localhost URLs should be considered local."""
        assert is_local_url("http://localhost:8080") is True
        assert is_local_url("https://localhost/api") is True
        assert is_local_url("http://localhost") is True

    def test_127_0_0_1_returns_true(self):
        """127.0.0.1 URLs should be considered local."""
        assert is_local_url("http://127.0.0.1:6333") is True
        assert is_local_url("https://127.0.0.1/health") is True

    def test_0_0_0_0_returns_true(self):
        """0.0.0.0 URLs should be considered local."""
        assert is_local_url("http://0.0.0.0:8000") is True

    def test_host_docker_internal_returns_true(self):
        """host.docker.internal URLs should be considered local."""
        assert is_local_url("http://host.docker.internal:5432") is True

    def test_docker_service_names_return_true(self):
        """Docker service names should be considered local."""
        assert is_local_url("http://qdrant:6333") is True
        assert is_local_url("http://infinity:7997") is True
        assert is_local_url("http://api:8000") is True
        assert is_local_url("http://frontend:3000") is True
        assert is_local_url("http://docling:5001") is True

    def test_external_urls_return_false(self):
        """External URLs should not be considered local."""
        assert is_local_url("http://google.com") is False
        assert is_local_url("https://openai.com") is False
        assert is_local_url("http://192.168.1.100:8080") is False
        assert is_local_url("https://example.com/endpoint") is False

    def test_case_insensitive(self):
        """URL check should be case insensitive."""
        assert is_local_url("http://LOCALHOST:8080") is True
        assert is_local_url("http://Qdrant:6333") is True


# -----------------------------------------------------------------------------
# get_queue_stats Tests
# -----------------------------------------------------------------------------


@pytest.mark.unit
class TestGetQueueStats:
    """Test get_queue_stats helper function."""

    def test_empty_directories(self, tmp_path):
        """Empty queue directories return zero counts."""
        pending_dir = tmp_path / "pending"
        processing_dir = tmp_path / "processing"
        completed_dir = tmp_path / "completed"
        pending_dir.mkdir()
        processing_dir.mkdir()
        completed_dir.mkdir()

        with patch("compose.api.routers.stats.QUEUE_BASE", tmp_path):
            result = get_queue_stats()

        assert result["pending_count"] == 0
        assert result["pending_files"] == []
        assert result["processing_count"] == 0
        assert result["processing_files"] == []
        assert result["completed_count"] == 0
        assert result["completed_files"] == []
        assert result["active_workers"] == []

    def test_nonexistent_directories(self, tmp_path):
        """Non-existent directories return zero counts."""
        with patch("compose.api.routers.stats.QUEUE_BASE", tmp_path):
            result = get_queue_stats()

        assert result["pending_count"] == 0
        assert result["processing_count"] == 0
        assert result["completed_count"] == 0

    def test_with_csv_files(self, tmp_path):
        """CSV files in directories are counted correctly."""
        pending_dir = tmp_path / "pending"
        processing_dir = tmp_path / "processing"
        completed_dir = tmp_path / "completed"
        pending_dir.mkdir()
        processing_dir.mkdir()
        completed_dir.mkdir()

        # Create CSV files
        (pending_dir / "batch1.csv").write_text("url\nhttp://example.com")
        (pending_dir / "batch2.csv").write_text("url\nhttp://example2.com")
        (processing_dir / "current.csv").write_text("url\nhttp://example3.com")
        (completed_dir / "done1.csv").write_text("url\nhttp://example4.com")
        (completed_dir / "done2.csv").write_text("url\nhttp://example5.com")
        (completed_dir / "done3.csv").write_text("url\nhttp://example6.com")

        with patch("compose.api.routers.stats.QUEUE_BASE", tmp_path):
            result = get_queue_stats()

        assert result["pending_count"] == 2
        assert set(result["pending_files"]) == {"batch1.csv", "batch2.csv"}
        assert result["processing_count"] == 1
        assert result["processing_files"] == ["current.csv"]
        assert result["completed_count"] == 3

    def test_with_progress_file_new_format(self, tmp_path):
        """Progress file with new workers format is parsed."""
        pending_dir = tmp_path / "pending"
        pending_dir.mkdir()

        progress_data = {
            "workers": [
                {"filename": "batch1.csv", "completed": 5, "total": 10},
                {"filename": "batch2.csv", "completed": 3, "total": 8},
            ]
        }
        progress_file = tmp_path / ".progress.json"
        progress_file.write_text(json.dumps(progress_data))

        with patch("compose.api.routers.stats.QUEUE_BASE", tmp_path):
            result = get_queue_stats()

        assert len(result["active_workers"]) == 2
        assert result["active_workers"][0]["filename"] == "batch1.csv"
        assert result["active_workers"][1]["completed"] == 3

    def test_with_progress_file_old_format(self, tmp_path):
        """Progress file with old single-object format is parsed."""
        pending_dir = tmp_path / "pending"
        pending_dir.mkdir()

        progress_data = {"filename": "batch1.csv", "completed": 5, "total": 10}
        progress_file = tmp_path / ".progress.json"
        progress_file.write_text(json.dumps(progress_data))

        with patch("compose.api.routers.stats.QUEUE_BASE", tmp_path):
            result = get_queue_stats()

        assert len(result["active_workers"]) == 1
        assert result["active_workers"][0]["filename"] == "batch1.csv"

    def test_with_invalid_progress_file(self, tmp_path):
        """Invalid progress file is handled gracefully."""
        pending_dir = tmp_path / "pending"
        pending_dir.mkdir()

        progress_file = tmp_path / ".progress.json"
        progress_file.write_text("invalid json{{{")

        with patch("compose.api.routers.stats.QUEUE_BASE", tmp_path):
            result = get_queue_stats()

        assert result["active_workers"] == []

    def test_completed_files_limited_to_five(self, tmp_path):
        """Completed files list is limited to last 5."""
        completed_dir = tmp_path / "completed"
        completed_dir.mkdir()

        # Create more than 5 completed files
        for i in range(10):
            (completed_dir / f"batch{i:02d}.csv").write_text("url\nhttp://example.com")

        with patch("compose.api.routers.stats.QUEUE_BASE", tmp_path):
            result = get_queue_stats()

        assert result["completed_count"] == 10
        assert len(result["completed_files"]) <= 5


# -----------------------------------------------------------------------------
# get_cache_stats Tests
# -----------------------------------------------------------------------------


@pytest.mark.unit
class TestGetCacheStats:
    """Test get_cache_stats helper function."""

    def test_success_returns_counts(self):
        """Successful Qdrant query returns video and article counts."""
        mock_collection = MagicMock()
        mock_collection.points_count = 150

        mock_videos_result = MagicMock()
        mock_videos_result.count = 100

        mock_articles_result = MagicMock()
        mock_articles_result.count = 50

        mock_client = MagicMock()
        mock_client.get_collection.return_value = mock_collection
        mock_client.count.side_effect = [mock_videos_result, mock_articles_result]

        assert result["status"] == "error"
        assert "Connection refused" in result["message"]
        assert result["total"] == 0
        assert result["videos"] == 0
        assert result["articles"] == 0

    def test_count_filter_failure_uses_total(self):
        """When count filters fail, falls back to total for videos."""
        mock_collection = MagicMock()
        mock_collection.points_count = 100

        mock_client = MagicMock()
        mock_client.get_collection.return_value = mock_collection
        mock_client.count.side_effect = Exception("Filter not supported")


@pytest.mark.unit
class TestGetArchiveStats:
    """Test get_archive_stats helper function."""

    def test_nonexistent_directory(self, tmp_path):
        """Non-existent youtube directory returns empty stats."""
        with patch("compose.api.routers.stats.ARCHIVE_BASE", tmp_path):
            result = get_archive_stats()

        assert result["total_videos"] == 0
        assert result["by_month"] == {}

    def test_empty_youtube_directory(self, tmp_path):
        """Empty youtube directory returns zero counts."""
        youtube_dir = tmp_path / "youtube"
        youtube_dir.mkdir()

        with patch("compose.api.routers.stats.ARCHIVE_BASE", tmp_path):
            result = get_archive_stats()

        assert result["total_videos"] == 0
        assert result["by_month"] == {}

    def test_with_monthly_directories(self, tmp_path):
        """Monthly directories with JSON files are counted correctly."""
        youtube_dir = tmp_path / "youtube"
        youtube_dir.mkdir()

        # Create monthly directories with JSON files
        jan_dir = youtube_dir / "2024-01"
        jan_dir.mkdir()
        (jan_dir / "video1.json").write_text('{"id": "abc"}')
        (jan_dir / "video2.json").write_text('{"id": "def"}')

        feb_dir = youtube_dir / "2024-02"
        feb_dir.mkdir()
        (feb_dir / "video3.json").write_text('{"id": "ghi"}')

        with patch("compose.api.routers.stats.ARCHIVE_BASE", tmp_path):
            result = get_archive_stats()

        assert result["total_videos"] == 3
        assert result["by_month"]["2024-01"] == 2
        assert result["by_month"]["2024-02"] == 1

    def test_months_sorted_descending(self, tmp_path):
        """Monthly stats are sorted in descending order."""
        youtube_dir = tmp_path / "youtube"
        youtube_dir.mkdir()

        # Create directories in non-sorted order
        for month in ["2024-01", "2024-03", "2024-02"]:
            month_dir = youtube_dir / month
            month_dir.mkdir()
            (month_dir / "video.json").write_text('{"id": "test"}')

        with patch("compose.api.routers.stats.ARCHIVE_BASE", tmp_path):
            result = get_archive_stats()

        month_keys = list(result["by_month"].keys())
        assert month_keys == ["2024-03", "2024-02", "2024-01"]


# -----------------------------------------------------------------------------
# get_recent_activity Tests
# -----------------------------------------------------------------------------


@pytest.mark.unit
class TestGetRecentActivity:
    """Test get_recent_activity helper function."""

    def test_nonexistent_directory(self, tmp_path):
        """Non-existent completed directory returns empty list."""
        with patch("compose.api.routers.stats.QUEUE_BASE", tmp_path):
            result = get_recent_activity()

        assert result == []

    def test_empty_directory(self, tmp_path):
        """Empty completed directory returns empty list."""
        completed_dir = tmp_path / "completed"
        completed_dir.mkdir()

        with patch("compose.api.routers.stats.QUEUE_BASE", tmp_path):
            result = get_recent_activity()

        assert result == []

    def test_returns_recent_files(self, tmp_path):
        """Returns activity for recent completed files."""
        completed_dir = tmp_path / "completed"
        completed_dir.mkdir()

        # Create completed files
        (completed_dir / "batch1.csv").write_text("url\nhttp://example.com")
        (completed_dir / "batch2.csv").write_text("url\nhttp://example2.com")

        with patch("compose.api.routers.stats.QUEUE_BASE", tmp_path):
            result = get_recent_activity()

        assert len(result) == 2
        assert all(item["type"] == "queue_completed" for item in result)
        assert all("timestamp" in item for item in result)
        assert all("file" in item for item in result)

    def test_limited_to_three_files(self, tmp_path):
        """Activity is limited to 3 most recent files."""
        completed_dir = tmp_path / "completed"
        completed_dir.mkdir()

        # Create more than 3 files
        for i in range(5):
            (completed_dir / f"batch{i}.csv").write_text("url\nhttp://example.com")

        with patch("compose.api.routers.stats.QUEUE_BASE", tmp_path):
            result = get_recent_activity()

        assert len(result) == 3


# -----------------------------------------------------------------------------
# get_stats Endpoint Tests
# -----------------------------------------------------------------------------


@pytest.mark.unit
class TestGetStatsEndpoint:
    """Test get_stats endpoint."""

    @pytest.mark.asyncio
    async def test_returns_expected_structure(self):
        """Endpoint returns dict with all expected keys."""
        with (
            patch(
                "compose.api.routers.stats.get_queue_stats",
                return_value={
                    "pending_count": 0,
                    "pending_files": [],
                    "processing_count": 0,
                    "processing_files": [],
                    "completed_count": 0,
                    "completed_files": [],
                    "active_workers": [],
                },
            ),
            patch(
                "compose.api.routers.stats.get_cache_stats",
                return_value={
                    "status": "ok",
                    "total": 100,
                    "videos": 80,
                    "articles": 20,
                    "collection_name": "content",
                },
            ),
            patch(
                "compose.api.routers.stats.get_archive_stats",
                return_value={"total_videos": 50, "by_month": {"2024-01": 50}},
            ),
            patch(
                "compose.api.routers.stats.get_service_health",
                new_callable=AsyncMock,
                return_value={
                    "qdrant": {"ok": True, "local": True},
                    "infinity": {"ok": True, "local": True},
                    "ollama": {"ok": False, "local": False},
                    "queue_worker": {"ok": True, "local": True},
                    "n8n": {"ok": False, "local": False},
                    "docling": {"ok": False, "local": False},
                },
            ),
            patch(
                "compose.api.routers.stats.get_recent_activity",
                return_value=[],
            ),
            patch(
                "compose.api.routers.stats.get_webshare_stats",
                new_callable=AsyncMock,
                return_value={"status": "unavailable", "message": "API token not configured"},
            ),
        ):
            result = await get_stats()

        assert "timestamp" in result
        assert "queue" in result
        assert "cache" in result
        assert "archive" in result
        assert "health" in result
        assert "recent_activity" in result
        assert "webshare" in result

    @pytest.mark.asyncio
    async def test_queue_stats_included(self):
        """Queue stats are included in response."""
        expected_queue = {
            "pending_count": 5,
            "pending_files": ["a.csv", "b.csv"],
            "processing_count": 1,
            "processing_files": ["c.csv"],
            "completed_count": 10,
            "completed_files": ["d.csv"],
            "active_workers": [],
        }

        with (
            patch("compose.api.routers.stats.get_queue_stats", return_value=expected_queue),
            patch(
                "compose.api.routers.stats.get_cache_stats",
                return_value={"status": "ok", "total": 0, "videos": 0, "articles": 0},
            ),
            patch(
                "compose.api.routers.stats.get_archive_stats",
                return_value={"total_videos": 0, "by_month": {}},
            ),
            patch(
                "compose.api.routers.stats.get_service_health",
                new_callable=AsyncMock,
                return_value={},
            ),
            patch("compose.api.routers.stats.get_recent_activity", return_value=[]),
            patch(
                "compose.api.routers.stats.get_webshare_stats",
                new_callable=AsyncMock,
                return_value={},
            ),
        ):
            result = await get_stats()

        assert result["queue"] == expected_queue

    @pytest.mark.asyncio
    async def test_cache_stats_included(self):
        """Cache stats are included in response."""
        expected_cache = {
            "status": "ok",
            "total": 200,
            "videos": 150,
            "articles": 50,
            "collection_name": "content",
        }

        with (
            patch(
                "compose.api.routers.stats.get_queue_stats",
                return_value={
                    "pending_count": 0,
                    "pending_files": [],
                    "processing_count": 0,
                    "processing_files": [],
                    "completed_count": 0,
                    "completed_files": [],
                    "active_workers": [],
                },
            ),
            patch("compose.api.routers.stats.get_cache_stats", return_value=expected_cache),
            patch(
                "compose.api.routers.stats.get_archive_stats",
                return_value={"total_videos": 0, "by_month": {}},
            ),
            patch(
                "compose.api.routers.stats.get_service_health",
                new_callable=AsyncMock,
                return_value={},
            ),
            patch("compose.api.routers.stats.get_recent_activity", return_value=[]),
            patch(
                "compose.api.routers.stats.get_webshare_stats",
                new_callable=AsyncMock,
                return_value={},
            ),
        ):
            result = await get_stats()

        assert result["cache"] == expected_cache

    @pytest.mark.asyncio
    async def test_timestamp_is_iso_format(self):
        """Timestamp is in ISO format."""
        with (
            patch(
                "compose.api.routers.stats.get_queue_stats",
                return_value={
                    "pending_count": 0,
                    "pending_files": [],
                    "processing_count": 0,
                    "processing_files": [],
                    "completed_count": 0,
                    "completed_files": [],
                    "active_workers": [],
                },
            ),
            patch(
                "compose.api.routers.stats.get_cache_stats",
                return_value={"status": "ok", "total": 0, "videos": 0, "articles": 0},
            ),
            patch(
                "compose.api.routers.stats.get_archive_stats",
                return_value={"total_videos": 0, "by_month": {}},
            ),
            patch(
                "compose.api.routers.stats.get_service_health",
                new_callable=AsyncMock,
                return_value={},
            ),
            patch("compose.api.routers.stats.get_recent_activity", return_value=[]),
            patch(
                "compose.api.routers.stats.get_webshare_stats",
                new_callable=AsyncMock,
                return_value={},
            ),
        ):
            result = await get_stats()

        # Should not raise - valid ISO format
        datetime.fromisoformat(result["timestamp"].replace("Z", "+00:00"))
