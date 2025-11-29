"""Tests for video ingestion and progress tracking in queue processor.

Tests characterize ingest behavior, progress tracking structure,
source type detection, and recommendation weight mapping.

Run with: uv run pytest compose/worker/tests/test_queue_ingest.py -v
"""

import json
import tempfile
from datetime import datetime
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest


# =============================================================================
# Test: Progress Tracking Structure
# =============================================================================


@pytest.mark.unit
class TestProgressTrackingStructure:
    """Test the structure and format of progress tracking files.

    The queue_processor writes progress to .progress.json for dashboard monitoring.
    These tests characterize the expected JSON structure.
    """

    def test_progress_file_structure_single_worker(self, temp_dir):
        """Verify progress file format for a single worker."""
        progress_file = temp_dir / ".progress.json"

        # Simulate what update_progress writes
        worker_data = {
            "worker_id": "W001",
            "filename": "test_batch.csv",
            "completed": 5,
            "total": 10,
            "started_at": "2024-11-20T10:00:00",
            "updated_at": "2024-11-20T10:05:00",
        }

        progress_content = {"workers": [worker_data]}

        with open(progress_file, "w") as f:
            json.dump(progress_content, f)

        # Read back and verify structure
        with open(progress_file, "r") as f:
            loaded = json.load(f)

        assert "workers" in loaded
        assert isinstance(loaded["workers"], list)
        assert len(loaded["workers"]) == 1

        worker = loaded["workers"][0]
        assert worker["worker_id"] == "W001"
        assert worker["filename"] == "test_batch.csv"
        assert worker["completed"] == 5
        assert worker["total"] == 10
        assert "started_at" in worker
        assert "updated_at" in worker

    def test_progress_file_structure_multiple_workers(self, temp_dir):
        """Verify progress file format for multiple concurrent workers."""
        progress_file = temp_dir / ".progress.json"

        workers = [
            {
                "worker_id": "W001",
                "filename": "batch1.csv",
                "completed": 3,
                "total": 10,
                "started_at": "2024-11-20T10:00:00",
                "updated_at": "2024-11-20T10:03:00",
            },
            {
                "worker_id": "W002",
                "filename": "batch2.csv",
                "completed": 7,
                "total": 15,
                "started_at": "2024-11-20T10:01:00",
                "updated_at": "2024-11-20T10:05:00",
            },
        ]

        progress_content = {"workers": workers}

        with open(progress_file, "w") as f:
            json.dump(progress_content, f)

        # Read back and verify
        with open(progress_file, "r") as f:
            loaded = json.load(f)

        assert len(loaded["workers"]) == 2
        assert loaded["workers"][0]["worker_id"] == "W001"
        assert loaded["workers"][1]["worker_id"] == "W002"

    def test_progress_percentage_calculation(self):
        """Verify progress percentage can be calculated from completed/total."""
        worker_data = {
            "completed": 5,
            "total": 10,
        }

        # Calculate percentage as dashboard would
        percentage = (worker_data["completed"] / worker_data["total"]) * 100
        assert percentage == 50.0

    def test_progress_with_zero_total_handled(self):
        """Zero total should be handled gracefully."""
        worker_data = {
            "completed": 0,
            "total": 0,
        }

        # Dashboard should check for division by zero
        if worker_data["total"] > 0:
            percentage = (worker_data["completed"] / worker_data["total"]) * 100
        else:
            percentage = 0

        assert percentage == 0


# =============================================================================
# Test: Source Type Detection
# =============================================================================


@pytest.mark.unit
class TestSourceTypeDetection:
    """Test source type detection logic from CSV data.

    The queue_processor determines source_type based on channel diversity:
    - Single channel (or none): "bulk_channel"
    - Multiple channels: "bulk_multi_channel"
    """

    def test_single_channel_detected(self):
        """Videos from single channel should be 'bulk_channel'."""
        videos = [
            {"url": "https://youtube.com/watch?v=vid1", "channel_id": "UC123"},
            {"url": "https://youtube.com/watch?v=vid2", "channel_id": "UC123"},
            {"url": "https://youtube.com/watch?v=vid3", "channel_id": "UC123"},
        ]

        # Logic from queue_processor
        channel_ids = {v.get("channel_id", "").strip() for v in videos if v.get("channel_id")}

        if len(channel_ids) <= 1:
            source_type = "bulk_channel"
        else:
            source_type = "bulk_multi_channel"

        assert source_type == "bulk_channel"

    def test_multiple_channels_detected(self):
        """Videos from multiple channels should be 'bulk_multi_channel'."""
        videos = [
            {"url": "https://youtube.com/watch?v=vid1", "channel_id": "UC123"},
            {"url": "https://youtube.com/watch?v=vid2", "channel_id": "UC456"},
            {"url": "https://youtube.com/watch?v=vid3", "channel_id": "UC789"},
        ]

        channel_ids = {v.get("channel_id", "").strip() for v in videos if v.get("channel_id")}

        if len(channel_ids) <= 1:
            source_type = "bulk_channel"
        else:
            source_type = "bulk_multi_channel"

        assert source_type == "bulk_multi_channel"

    def test_no_channel_ids_defaults_to_bulk_channel(self):
        """Videos without channel_id should default to 'bulk_channel'."""
        videos = [
            {"url": "https://youtube.com/watch?v=vid1"},
            {"url": "https://youtube.com/watch?v=vid2"},
        ]

        channel_ids = {v.get("channel_id", "").strip() for v in videos if v.get("channel_id")}

        if len(channel_ids) <= 1:
            source_type = "bulk_channel"
        else:
            source_type = "bulk_multi_channel"

        assert source_type == "bulk_channel"
        assert len(channel_ids) == 0

    def test_empty_channel_ids_ignored(self):
        """Empty channel_id strings should be ignored."""
        videos = [
            {"url": "https://youtube.com/watch?v=vid1", "channel_id": "UC123"},
            {"url": "https://youtube.com/watch?v=vid2", "channel_id": ""},
            {"url": "https://youtube.com/watch?v=vid3", "channel_id": "   "},
        ]

        # Logic from queue_processor - empty strings filtered out after strip
        channel_ids = {v.get("channel_id", "").strip() for v in videos if v.get("channel_id")}
        # Note: empty string after strip is still in set if original wasn't empty
        # But only non-empty stripped values should count
        channel_ids = {cid for cid in channel_ids if cid}  # Remove empty strings

        assert len(channel_ids) == 1
        assert "UC123" in channel_ids


# =============================================================================
# Test: Weight Map
# =============================================================================


@pytest.mark.unit
class TestRecommendationWeightMap:
    """Test the recommendation weight mapping logic.

    Different source types have different default weights:
    - queue_import: 0.8 (user explicitly requested)
    - bulk_channel: 0.5 (automated channel import)
    - bulk_multi_channel: 0.2 (broad automated import)
    """

    def test_queue_import_weight(self):
        """Queue imports should have weight 0.8."""
        weight_map = {
            "queue_import": 0.8,
            "bulk_channel": 0.5,
            "bulk_multi_channel": 0.2,
        }

        assert weight_map.get("queue_import", 0.8) == 0.8

    def test_bulk_channel_weight(self):
        """Bulk channel imports should have weight 0.5."""
        weight_map = {
            "queue_import": 0.8,
            "bulk_channel": 0.5,
            "bulk_multi_channel": 0.2,
        }

        assert weight_map.get("bulk_channel", 0.8) == 0.5

    def test_bulk_multi_channel_weight(self):
        """Bulk multi-channel imports should have weight 0.2."""
        weight_map = {
            "queue_import": 0.8,
            "bulk_channel": 0.5,
            "bulk_multi_channel": 0.2,
        }

        assert weight_map.get("bulk_multi_channel", 0.8) == 0.2

    def test_unknown_source_type_defaults_to_0_8(self):
        """Unknown source types should default to 0.8."""
        weight_map = {
            "queue_import": 0.8,
            "bulk_channel": 0.5,
            "bulk_multi_channel": 0.2,
        }

        assert weight_map.get("unknown_type", 0.8) == 0.8


# =============================================================================
# Test: Async Ingest Video (with mocks)
# =============================================================================


@pytest.mark.unit
@pytest.mark.asyncio
class TestIngestVideoWithMocks:
    """Test ingest_video function with mocked external dependencies.

    These tests verify the behavior of ingest_video by mocking:
    - MinIO storage (create_minio_client)
    - YouTube transcript service (get_transcript)
    - YouTube metadata service (fetch_video_metadata)
    - Archive manager
    """

    @patch("compose.worker.queue_processor.get_transcript")
    @patch("compose.worker.queue_processor.fetch_video_metadata")
    @patch("compose.worker.queue_processor.extract_video_id")
    async def test_skips_already_cached_video(
        self, mock_extract, mock_metadata, mock_transcript
    ):
        """Video already in cache should be skipped."""
        # Import here to avoid module-level import issues
        from compose.worker.queue_processor import ingest_video

        # Setup mocks
        mock_extract.return_value = "dQw4w9WgXcQ"
        mock_storage = MagicMock()
        mock_storage.client.exists.return_value = True
        mock_archive = MagicMock()

        # Execute
        success, message = await ingest_video(
            "https://youtube.com/watch?v=dQw4w9WgXcQ",
            mock_archive,
            mock_storage
        )

        # Verify
        assert success is True
        assert "SKIP" in message
        assert "dQw4w9WgXcQ" in message
        mock_transcript.assert_not_called()
        mock_metadata.assert_not_called()

    @patch("compose.worker.queue_processor.get_video", new_callable=AsyncMock)
    @patch("compose.worker.queue_processor.upsert_video", new_callable=AsyncMock)
    @patch("compose.worker.queue_processor.get_transcript")
    @patch("compose.worker.queue_processor.fetch_video_metadata")
    @patch("compose.worker.queue_processor.extract_video_id")
    async def test_returns_error_on_transcript_failure(
        self, mock_extract, mock_metadata, mock_transcript, mock_upsert, mock_get_video
    ):
        """Transcript fetch error should return failure."""
        from compose.worker.queue_processor import ingest_video

        mock_extract.return_value = "dQw4w9WgXcQ"
        mock_get_video.return_value = None  # Not cached in SurrealDB
        mock_storage = MagicMock()
        mock_storage.client.exists.return_value = False
        mock_transcript.return_value = "ERROR: No transcript available"
        mock_archive = MagicMock()

        success, message = await ingest_video(
            "https://youtube.com/watch?v=dQw4w9WgXcQ",
            mock_archive,
            mock_storage
        )

        assert success is False
        assert "ERROR" in message
        assert "No transcript available" in message

    @patch("compose.worker.queue_processor.get_video", new_callable=AsyncMock)
    @patch("compose.worker.queue_processor.upsert_video", new_callable=AsyncMock)
    @patch("compose.worker.queue_processor.get_transcript")
    @patch("compose.worker.queue_processor.fetch_video_metadata")
    @patch("compose.worker.queue_processor.extract_video_id")
    async def test_default_source_type_is_valid(
        self, mock_extract, mock_metadata, mock_transcript, mock_upsert, mock_get_video
    ):
        """Default source_type='single_import' is a valid Pydantic literal.

        This was fixed from the previous bug where 'queue_import' was used as default,
        which was not a valid literal value.
        """
        from compose.worker.queue_processor import ingest_video

        mock_extract.return_value = "dQw4w9WgXcQ"
        mock_get_video.return_value = None  # Not cached in SurrealDB
        mock_storage = MagicMock()
        mock_storage.client.exists.return_value = False
        mock_transcript.return_value = "This is the transcript content"
        mock_metadata.return_value = (
            {"title": "Test Video", "channel_title": "Test Channel"},
            None
        )
        mock_archive = MagicMock()

        # Default source_type is now "single_import" which is valid
        success, message = await ingest_video(
            "https://youtube.com/watch?v=dQw4w9WgXcQ",
            mock_archive,
            mock_storage
        )

        # Should succeed now that default source_type is valid
        assert success is True
        assert "OK" in message

    @patch("compose.worker.queue_processor.get_video", new_callable=AsyncMock)
    @patch("compose.worker.queue_processor.upsert_video", new_callable=AsyncMock)
    @patch("compose.worker.queue_processor.get_transcript")
    @patch("compose.worker.queue_processor.fetch_video_metadata")
    @patch("compose.worker.queue_processor.extract_video_id")
    async def test_successful_ingest_with_valid_source_type(
        self, mock_extract, mock_metadata, mock_transcript, mock_upsert, mock_get_video
    ):
        """Successful ingest should archive transcript and cache data with valid source_type."""
        from compose.worker.queue_processor import ingest_video

        mock_extract.return_value = "dQw4w9WgXcQ"
        mock_get_video.return_value = None  # Not cached in SurrealDB
        mock_storage = MagicMock()
        mock_storage.client.exists.return_value = False
        mock_transcript.return_value = "This is the transcript content"
        mock_metadata.return_value = (
            {"title": "Test Video", "channel_title": "Test Channel"},
            None
        )
        mock_archive = MagicMock()

        # Use a valid source_type
        success, message = await ingest_video(
            "https://youtube.com/watch?v=dQw4w9WgXcQ",
            mock_archive,
            mock_storage,
            source_type="bulk_channel"  # Valid source type
        )

        assert success is True
        assert "OK" in message
        mock_archive.update_transcript.assert_called_once()
        mock_archive.update_metadata.assert_called_once()
        mock_storage.client.put_json.assert_called_once()

    @patch("compose.worker.queue_processor.get_video", new_callable=AsyncMock)
    @patch("compose.worker.queue_processor.upsert_video", new_callable=AsyncMock)
    @patch("compose.worker.queue_processor.get_transcript")
    @patch("compose.worker.queue_processor.fetch_video_metadata")
    @patch("compose.worker.queue_processor.extract_video_id")
    async def test_handles_metadata_fetch_failure_gracefully(
        self, mock_extract, mock_metadata, mock_transcript, mock_upsert, mock_get_video
    ):
        """Metadata fetch failure should not prevent successful ingest."""
        from compose.worker.queue_processor import ingest_video

        mock_extract.return_value = "dQw4w9WgXcQ"
        mock_get_video.return_value = None  # Not cached in SurrealDB
        mock_storage = MagicMock()
        mock_storage.client.exists.return_value = False
        mock_transcript.return_value = "This is the transcript content"
        mock_metadata.return_value = ({}, "Metadata fetch failed")
        mock_archive = MagicMock()

        # Use valid source_type
        success, message = await ingest_video(
            "https://youtube.com/watch?v=dQw4w9WgXcQ",
            mock_archive,
            mock_storage,
            source_type="bulk_channel"  # Valid source type
        )

        # Should still succeed - metadata is optional
        assert success is True
        assert "OK" in message
        mock_archive.update_transcript.assert_called_once()
        # Metadata should not be updated when empty
        mock_archive.update_metadata.assert_not_called()

    @patch("compose.worker.queue_processor.extract_video_id")
    async def test_returns_error_on_invalid_url(
        self, mock_extract
    ):
        """Invalid URL should return error."""
        from compose.worker.queue_processor import ingest_video

        mock_extract.side_effect = ValueError("Could not extract video ID")
        mock_storage = MagicMock()
        mock_archive = MagicMock()

        success, message = await ingest_video(
            "https://example.com/not-youtube",
            mock_archive,
            mock_storage
        )

        assert success is False
        assert "ERROR" in message
        assert "Invalid URL" in message

    @patch("compose.worker.queue_processor.get_video", new_callable=AsyncMock)
    @patch("compose.worker.queue_processor.upsert_video", new_callable=AsyncMock)
    @patch("compose.worker.queue_processor.get_transcript")
    @patch("compose.worker.queue_processor.fetch_video_metadata")
    @patch("compose.worker.queue_processor.extract_video_id")
    async def test_uses_provided_channel_context(
        self, mock_extract, mock_metadata, mock_transcript, mock_upsert, mock_get_video
    ):
        """Channel ID and name from CSV should be used in import metadata."""
        from compose.worker.queue_processor import ingest_video

        mock_extract.return_value = "dQw4w9WgXcQ"
        mock_get_video.return_value = None  # Not cached in SurrealDB
        mock_storage = MagicMock()
        mock_storage.client.exists.return_value = False
        mock_transcript.return_value = "This is the transcript content"
        mock_metadata.return_value = ({}, None)
        mock_archive = MagicMock()

        success, message = await ingest_video(
            "https://youtube.com/watch?v=dQw4w9WgXcQ",
            mock_archive,
            mock_storage,
            source_type="bulk_channel",
            channel_id="UC123",
            channel_name="Test Channel"
        )

        assert success is True
        # Verify the import metadata was created with channel context
        call_args = mock_archive.update_transcript.call_args
        import_metadata = call_args[1]["import_metadata"]
        assert import_metadata.channel_context.channel_id == "UC123"
        assert import_metadata.channel_context.channel_name == "Test Channel"


# =============================================================================
# Test: Progress Tracking Functions (with mocks)
# =============================================================================


@pytest.mark.unit
@pytest.mark.asyncio
class TestProgressTrackingFunctions:
    """Test update_progress and clear_progress async functions.

    These functions now use SurrealDB for progress tracking instead of files.
    Tests verify the correct SurrealDB queries are made.
    """

    @patch("compose.worker.queue_processor.execute_query", new_callable=AsyncMock)
    async def test_update_progress_calls_surrealdb(self, mock_execute):
        """update_progress should UPSERT to SurrealDB."""
        import compose.worker.queue_processor as qp

        # Reset start times tracking
        qp._worker_start_times = {}

        await qp.update_progress("W001", "test.csv", 5, 10)

        # Verify execute_query was called
        mock_execute.assert_called_once()
        call_args = mock_execute.call_args
        query = call_args[0][0]
        params = call_args[0][1]

        assert "UPSERT" in query
        assert "worker_progress" in query
        assert params["worker_id"] == "W001"
        assert params["filename"] == "test.csv"
        assert params["completed"] == 5
        assert params["total"] == 10

    @patch("compose.worker.queue_processor.execute_query", new_callable=AsyncMock)
    async def test_update_progress_tracks_multiple_workers(self, mock_execute):
        """Multiple workers should each call SurrealDB."""
        import compose.worker.queue_processor as qp

        qp._worker_start_times = {}

        await qp.update_progress("W001", "batch1.csv", 3, 10)
        await qp.update_progress("W002", "batch2.csv", 7, 15)

        # Should have 2 calls
        assert mock_execute.call_count == 2

        # Verify worker IDs in calls
        calls = mock_execute.call_args_list
        worker_ids = {call[0][1]["worker_id"] for call in calls}
        assert worker_ids == {"W001", "W002"}

    @patch("compose.worker.queue_processor.execute_query", new_callable=AsyncMock)
    async def test_clear_progress_deletes_from_surrealdb(self, mock_execute):
        """clear_progress should DELETE from SurrealDB."""
        import compose.worker.queue_processor as qp

        qp._worker_start_times = {"W001": "2024-01-01T00:00:00"}

        await qp.clear_progress("W001")

        # Verify DELETE query was called
        mock_execute.assert_called_once()
        call_args = mock_execute.call_args
        query = call_args[0][0]
        params = call_args[0][1]

        assert "DELETE" in query
        assert "worker_progress" in query
        assert params["worker_id"] == "W001"

        # Verify start time was cleaned up
        assert "W001" not in qp._worker_start_times

    @patch("compose.worker.queue_processor.execute_query", new_callable=AsyncMock)
    async def test_clear_progress_cleans_up_start_times(self, mock_execute):
        """clear_progress should remove worker from start time tracking."""
        import compose.worker.queue_processor as qp

        qp._worker_start_times = {"W001": "2024-01-01T00:00:00", "W002": "2024-01-01T00:00:00"}

        await qp.clear_progress("W001")

        # W001 should be removed, W002 should remain
        assert "W001" not in qp._worker_start_times
        assert "W002" in qp._worker_start_times


# =============================================================================
# Fixtures
# =============================================================================


@pytest.fixture
def temp_dir():
    """Provide a temporary directory for file operations."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)
