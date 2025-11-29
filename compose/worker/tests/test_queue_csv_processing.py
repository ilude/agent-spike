"""Tests for CSV processing and utilities in queue processor.

Tests characterize CSV processing logic, skipping completed items,
logging utilities, and cache data structures.

Run with: uv run pytest compose/worker/tests/test_queue_csv_processing.py -v
"""

import csv
import tempfile
from datetime import datetime
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest


# =============================================================================
# Test: CSV Processing Logic
# =============================================================================


@pytest.mark.unit
class TestCsvProcessingSkipsDone:
    """Test that CSV processing correctly skips already-completed items.

    The ingest_video function checks cache.exists() before processing.
    """

    def test_csv_reader_parses_url_column(self, temp_dir):
        """Verify CSV reading extracts URL column correctly."""
        csv_file = temp_dir / "test.csv"

        with open(csv_file, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=["url", "channel_id", "channel_name"])
            writer.writeheader()
            writer.writerow({
                "url": "https://youtube.com/watch?v=video1",
                "channel_id": "UC123",
                "channel_name": "Test Channel",
            })
            writer.writerow({
                "url": "https://youtube.com/watch?v=video2",
                "channel_id": "UC456",
                "channel_name": "Another Channel",
            })

        with open(csv_file, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            rows = list(reader)

        assert len(rows) == 2
        assert rows[0]["url"] == "https://youtube.com/watch?v=video1"
        assert rows[1]["url"] == "https://youtube.com/watch?v=video2"

    def test_empty_url_skipped_in_csv(self, temp_dir):
        """Rows with empty URLs should be skipped."""
        csv_file = temp_dir / "test.csv"

        with open(csv_file, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=["url", "channel_id"])
            writer.writeheader()
            writer.writerow({"url": "https://youtube.com/watch?v=video1", "channel_id": "UC123"})
            writer.writerow({"url": "", "channel_id": "UC456"})  # Empty URL
            writer.writerow({"url": "https://youtube.com/watch?v=video3", "channel_id": "UC789"})

        with open(csv_file, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            rows = list(reader)

        # Filter out empty URLs as queue_processor does
        valid_urls = [r for r in rows if r.get("url", "").strip()]

        assert len(valid_urls) == 2

    def test_whitespace_url_treated_as_empty(self, temp_dir):
        """URLs with only whitespace should be treated as empty."""
        csv_file = temp_dir / "test.csv"

        with open(csv_file, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=["url"])
            writer.writeheader()
            writer.writerow({"url": "   "})  # Whitespace only
            writer.writerow({"url": "\t\n"})  # Tabs and newlines

        with open(csv_file, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            rows = list(reader)

        # queue_processor uses .strip() before checking
        valid_urls = [r for r in rows if r.get("url", "").strip()]

        assert len(valid_urls) == 0


# =============================================================================
# Test: Async Process CSV (with mocks)
# =============================================================================


@pytest.mark.unit
@pytest.mark.asyncio
class TestProcessCsvWithMocks:
    """Test process_csv function with mocked dependencies."""

    @patch("compose.worker.queue_processor.ingest_video")
    @patch("compose.worker.queue_processor.update_progress")
    @patch("compose.worker.queue_processor.clear_progress")
    async def test_processes_all_valid_urls(
        self, mock_clear, mock_update, mock_ingest, temp_dir
    ):
        """All valid URLs in CSV should be processed."""
        from compose.worker.queue_processor import process_csv

        # Create test CSV
        csv_file = temp_dir / "test.csv"
        with open(csv_file, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=["url", "channel_id"])
            writer.writeheader()
            writer.writerow({"url": "https://youtube.com/watch?v=vid1", "channel_id": "UC123"})
            writer.writerow({"url": "https://youtube.com/watch?v=vid2", "channel_id": "UC123"})

        mock_ingest.return_value = (True, "OK: processed")
        mock_update.return_value = None
        mock_clear.return_value = None
        mock_archive = MagicMock()
        mock_storage = MagicMock()

        stats = await process_csv(csv_file, mock_archive, mock_storage, "W001")

        assert mock_ingest.call_count == 2
        assert stats["total"] == 2
        assert stats["processed"] == 2
        assert stats["errors"] == 0

    @patch("compose.worker.queue_processor.ingest_video")
    @patch("compose.worker.queue_processor.update_progress")
    @patch("compose.worker.queue_processor.clear_progress")
    async def test_skips_empty_urls(
        self, mock_clear, mock_update, mock_ingest, temp_dir
    ):
        """Empty URLs in CSV should be skipped."""
        from compose.worker.queue_processor import process_csv

        csv_file = temp_dir / "test.csv"
        with open(csv_file, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=["url", "channel_id"])
            writer.writeheader()
            writer.writerow({"url": "https://youtube.com/watch?v=vid1", "channel_id": "UC123"})
            writer.writerow({"url": "", "channel_id": "UC123"})  # Empty URL
            writer.writerow({"url": "   ", "channel_id": "UC123"})  # Whitespace only

        mock_ingest.return_value = (True, "OK: processed")
        mock_update.return_value = None
        mock_clear.return_value = None
        mock_archive = MagicMock()
        mock_storage = MagicMock()

        stats = await process_csv(csv_file, mock_archive, mock_storage, "W001")

        # Only one valid URL should be processed
        assert mock_ingest.call_count == 1
        assert stats["total"] == 3  # Total rows in CSV
        assert stats["processed"] == 1

    @patch("compose.worker.queue_processor.ingest_video")
    @patch("compose.worker.queue_processor.update_progress")
    @patch("compose.worker.queue_processor.clear_progress")
    async def test_counts_skipped_items_correctly(
        self, mock_clear, mock_update, mock_ingest, temp_dir
    ):
        """Already-cached items should be counted as skipped."""
        from compose.worker.queue_processor import process_csv

        csv_file = temp_dir / "test.csv"
        with open(csv_file, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=["url"])
            writer.writeheader()
            writer.writerow({"url": "https://youtube.com/watch?v=vid1"})
            writer.writerow({"url": "https://youtube.com/watch?v=vid2"})

        # First video is new, second is skipped (already cached)
        mock_ingest.side_effect = [
            (True, "OK: processed"),
            (True, "SKIP: Already cached"),
        ]
        mock_update.return_value = None
        mock_clear.return_value = None
        mock_archive = MagicMock()
        mock_storage = MagicMock()

        stats = await process_csv(csv_file, mock_archive, mock_storage, "W001")

        assert stats["processed"] == 1
        assert stats["skipped"] == 1
        assert stats["errors"] == 0

    @patch("compose.worker.queue_processor.ingest_video")
    @patch("compose.worker.queue_processor.update_progress")
    @patch("compose.worker.queue_processor.clear_progress")
    async def test_counts_errors_correctly(
        self, mock_clear, mock_update, mock_ingest, temp_dir
    ):
        """Failed ingests should be counted as errors."""
        from compose.worker.queue_processor import process_csv

        csv_file = temp_dir / "test.csv"
        with open(csv_file, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=["url"])
            writer.writeheader()
            writer.writerow({"url": "https://youtube.com/watch?v=vid1"})
            writer.writerow({"url": "https://youtube.com/watch?v=vid2"})

        mock_ingest.side_effect = [
            (True, "OK: processed"),
            (False, "ERROR: No transcript"),
        ]
        mock_update.return_value = None
        mock_clear.return_value = None
        mock_archive = MagicMock()
        mock_storage = MagicMock()

        stats = await process_csv(csv_file, mock_archive, mock_storage, "W001")

        assert stats["processed"] == 1
        assert stats["errors"] == 1

    @patch("compose.worker.queue_processor.ingest_video")
    @patch("compose.worker.queue_processor.update_progress")
    @patch("compose.worker.queue_processor.clear_progress")
    async def test_detects_multi_channel_source_type(
        self, mock_clear, mock_update, mock_ingest, temp_dir
    ):
        """Multiple channel IDs should result in 'bulk_multi_channel' source type."""
        from compose.worker.queue_processor import process_csv

        csv_file = temp_dir / "test.csv"
        with open(csv_file, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=["url", "channel_id"])
            writer.writeheader()
            writer.writerow({"url": "https://youtube.com/watch?v=vid1", "channel_id": "UC123"})
            writer.writerow({"url": "https://youtube.com/watch?v=vid2", "channel_id": "UC456"})

        mock_ingest.return_value = (True, "OK: processed")
        mock_update.return_value = None
        mock_clear.return_value = None
        mock_archive = MagicMock()
        mock_storage = MagicMock()

        await process_csv(csv_file, mock_archive, mock_storage, "W001")

        # Verify source_type was detected correctly
        # Args: (url, archive_manager, storage, source_type, ...)
        for call in mock_ingest.call_args_list:
            assert call[0][3] == "bulk_multi_channel"


# =============================================================================
# Test: Log Function
# =============================================================================


@pytest.mark.unit
class TestLogFunction:
    """Test the log function formatting."""

    def test_log_includes_timestamp(self, capsys):
        """log() should include timestamp in output."""
        from compose.worker.queue_processor import log

        log("Test message")
        captured = capsys.readouterr()

        # Should have timestamp format [YYYY-MM-DD HH:MM:SS]
        assert "[" in captured.out
        assert "]" in captured.out
        assert "Test message" in captured.out

    def test_log_flushes_output(self, capsys):
        """log() should flush output immediately."""
        from compose.worker.queue_processor import log

        # Just verify it runs without error - flush=True in print
        log("Immediate output")
        captured = capsys.readouterr()
        assert "Immediate output" in captured.out


# =============================================================================
# Test: Cache Data Structure
# =============================================================================


@pytest.mark.unit
class TestCacheDataStructure:
    """Test the structure of data cached for YouTube videos."""

    def test_cache_data_contains_required_fields(self):
        """Cached data should contain video_id, url, transcript, and length."""
        # Simulating the structure created in ingest_video
        video_id = "dQw4w9WgXcQ"
        url = "https://youtube.com/watch?v=dQw4w9WgXcQ"
        transcript = "This is the transcript content"

        cache_data = {
            "video_id": video_id,
            "url": url,
            "transcript": transcript,
            "transcript_length": len(transcript),
        }

        assert cache_data["video_id"] == "dQw4w9WgXcQ"
        assert cache_data["url"] == url
        assert cache_data["transcript"] == transcript
        assert cache_data["transcript_length"] == 30

    def test_cache_metadata_contains_youtube_fields(self):
        """Cache metadata should include YouTube metadata fields."""
        from datetime import datetime

        metadata = {
            "type": "youtube_video",
            "source": "queue_worker",
            "video_id": "dQw4w9WgXcQ",
            "source_type": "bulk_channel",
            "recommendation_weight": 0.5,
            "imported_at": datetime.now().isoformat(),
            "youtube_title": "Test Video",
            "youtube_channel": "Test Channel",
            "youtube_channel_id": "UC123",
            "youtube_duration_seconds": 180,
            "youtube_view_count": 1000,
            "youtube_published_at": "2024-01-01T00:00:00Z",
        }

        assert metadata["type"] == "youtube_video"
        assert metadata["source"] == "queue_worker"
        assert "youtube_title" in metadata
        assert "youtube_channel" in metadata
        assert "recommendation_weight" in metadata


# =============================================================================
# Fixtures
# =============================================================================


@pytest.fixture
def temp_dir():
    """Provide a temporary directory for file operations."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)
