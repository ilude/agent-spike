"""Tests for stats router endpoints and stat-gathering functions.

Run with: uv run pytest compose/api/routers/tests/test_stats_endpoints.py
"""

import pytest
from unittest.mock import patch, AsyncMock
from datetime import datetime

from compose.api.routers.stats import (
    get_queue_stats,
    get_cache_stats,
    get_archive_stats,
    get_recent_activity,
    get_stats,
)


# -----------------------------------------------------------------------------
# get_queue_stats Tests
# -----------------------------------------------------------------------------


@pytest.mark.unit
class TestGetQueueStats:
    """Test get_queue_stats helper function."""

    @pytest.mark.asyncio
    async def test_empty_directories(self, tmp_path):
        """Empty queue directories return zero counts."""
        pending_dir = tmp_path / "pending"
        processing_dir = tmp_path / "processing"
        completed_dir = tmp_path / "completed"
        pending_dir.mkdir()
        processing_dir.mkdir()
        completed_dir.mkdir()

        with (
            patch("compose.api.routers.stats.QUEUE_BASE", tmp_path),
            patch(
                "compose.services.surrealdb.driver.execute_query",
                new_callable=AsyncMock,
                return_value=[],
            ),
        ):
            result = await get_queue_stats()

        assert result["pending_count"] == 0
        assert result["pending_files"] == []
        assert result["processing_count"] == 0
        assert result["processing_files"] == []
        assert result["completed_count"] == 0
        assert result["completed_files"] == []
        assert result["active_workers"] == []

    @pytest.mark.asyncio
    async def test_nonexistent_directories(self, tmp_path):
        """Non-existent directories return zero counts."""
        with (
            patch("compose.api.routers.stats.QUEUE_BASE", tmp_path),
            patch(
                "compose.services.surrealdb.driver.execute_query",
                new_callable=AsyncMock,
                return_value=[],
            ),
        ):
            result = await get_queue_stats()

        assert result["pending_count"] == 0
        assert result["processing_count"] == 0
        assert result["completed_count"] == 0

    @pytest.mark.asyncio
    async def test_with_csv_files(self, tmp_path):
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

        with (
            patch("compose.api.routers.stats.QUEUE_BASE", tmp_path),
            patch(
                "compose.services.surrealdb.driver.execute_query",
                new_callable=AsyncMock,
                return_value=[],
            ),
        ):
            result = await get_queue_stats()

        assert result["pending_count"] == 2
        assert set(result["pending_files"]) == {"batch1.csv", "batch2.csv"}
        assert result["processing_count"] == 1
        assert result["processing_files"] == ["current.csv"]
        assert result["completed_count"] == 3

    @pytest.mark.asyncio
    async def test_with_active_workers_from_surrealdb(self, tmp_path):
        """Worker progress from SurrealDB is included."""
        pending_dir = tmp_path / "pending"
        pending_dir.mkdir()

        mock_workers = [
            {"worker_id": "w1", "filename": "batch1.csv", "completed": 5, "total": 10},
            {"worker_id": "w2", "filename": "batch2.csv", "completed": 3, "total": 8},
        ]

        with (
            patch("compose.api.routers.stats.QUEUE_BASE", tmp_path),
            patch(
                "compose.services.surrealdb.driver.execute_query",
                new_callable=AsyncMock,
                return_value=mock_workers,
            ),
        ):
            result = await get_queue_stats()

        assert len(result["active_workers"]) == 2
        assert result["active_workers"][0]["filename"] == "batch1.csv"
        assert result["active_workers"][1]["completed"] == 3

    @pytest.mark.asyncio
    async def test_completed_files_limited_to_five(self, tmp_path):
        """Completed files list is limited to last 5."""
        completed_dir = tmp_path / "completed"
        completed_dir.mkdir()

        # Create more than 5 completed files
        for i in range(10):
            (completed_dir / f"batch{i:02d}.csv").write_text("url\nhttp://example.com")

        with (
            patch("compose.api.routers.stats.QUEUE_BASE", tmp_path),
            patch(
                "compose.services.surrealdb.driver.execute_query",
                new_callable=AsyncMock,
                return_value=[],
            ),
        ):
            result = await get_queue_stats()

        assert result["completed_count"] == 10
        assert len(result["completed_files"]) <= 5


# -----------------------------------------------------------------------------
# get_cache_stats Tests
# -----------------------------------------------------------------------------


@pytest.mark.unit
class TestGetCacheStats:
    """Test get_cache_stats helper function."""

    @pytest.mark.asyncio
    async def test_success_returns_counts(self):
        """Successful SurrealDB query returns video counts."""
        with patch(
            "compose.services.surrealdb.get_video_count",
            new_callable=AsyncMock,
            return_value=150,
        ):
            result = await get_cache_stats()

        assert result["status"] == "ok"
        assert result["total"] == 150
        assert result["videos"] == 150
        assert result["articles"] == 0

    @pytest.mark.asyncio
    async def test_error_returns_error_status(self):
        """Connection error returns error status."""
        with patch(
            "compose.services.surrealdb.get_video_count",
            new_callable=AsyncMock,
            side_effect=Exception("Connection refused"),
        ):
            result = await get_cache_stats()

        assert result["status"] == "error"
        assert "Connection refused" in result["message"]
        assert result["total"] == 0
        assert result["videos"] == 0
        assert result["articles"] == 0


# -----------------------------------------------------------------------------
# get_archive_stats Tests
# -----------------------------------------------------------------------------


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
                new_callable=AsyncMock,
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
                new_callable=AsyncMock,
                return_value={
                    "status": "ok",
                    "total": 100,
                    "videos": 80,
                    "articles": 20,
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
                    "surrealdb": {"ok": True, "local": True},
                    "minio": {"ok": True, "local": True},
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
            patch("compose.api.routers.stats.get_queue_stats", new_callable=AsyncMock, return_value=expected_queue),
            patch(
                "compose.api.routers.stats.get_cache_stats",
                new_callable=AsyncMock,
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
        }

        with (
            patch(
                "compose.api.routers.stats.get_queue_stats",
                new_callable=AsyncMock,
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
            patch("compose.api.routers.stats.get_cache_stats", new_callable=AsyncMock, return_value=expected_cache),
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
                new_callable=AsyncMock,
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
                new_callable=AsyncMock,
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
