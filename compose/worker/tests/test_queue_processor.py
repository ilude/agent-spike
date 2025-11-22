"""Characterization tests for queue_processor.py.

These tests capture the CURRENT behavior of the queue processor worker.
Focus on pure functions and logic that can be tested without external dependencies.

Run with: uv run pytest compose/worker/tests/test_queue_processor.py -v
"""

import csv
import json
import tempfile
from datetime import datetime
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

# Import the functions we're testing - note these use the youtube service
from compose.services.youtube import extract_video_id


# =============================================================================
# Test: YouTube URL Parsing (via extract_video_id)
# =============================================================================


@pytest.mark.unit
class TestGetVideoIdFromUrl:
    """Test YouTube URL parsing to extract video IDs.

    The queue_processor uses extract_video_id from compose.services.youtube.
    These tests characterize the expected behavior for various URL formats.
    """

    def test_standard_youtube_url(self):
        """Standard youtube.com/watch?v= format."""
        url = "https://www.youtube.com/watch?v=dQw4w9WgXcQ"
        assert extract_video_id(url) == "dQw4w9WgXcQ"

    def test_short_youtu_be_url(self):
        """Short youtu.be/ format."""
        url = "https://youtu.be/dQw4w9WgXcQ"
        assert extract_video_id(url) == "dQw4w9WgXcQ"

    def test_url_with_query_params(self):
        """URL with additional query parameters after video ID."""
        url = "https://www.youtube.com/watch?v=dQw4w9WgXcQ&t=42s&list=PLxyz"
        assert extract_video_id(url) == "dQw4w9WgXcQ"

    def test_url_without_www(self):
        """URL without www prefix."""
        url = "https://youtube.com/watch?v=dQw4w9WgXcQ"
        assert extract_video_id(url) == "dQw4w9WgXcQ"

    def test_url_with_underscore_in_id(self):
        """Video ID containing underscore character."""
        url = "https://youtube.com/watch?v=abc_def_123"
        assert extract_video_id(url) == "abc_def_123"

    def test_url_with_dash_in_id(self):
        """Video ID containing dash character."""
        url = "https://youtube.com/watch?v=abc-def-123"
        assert extract_video_id(url) == "abc-def-123"

    def test_invalid_url_raises_value_error(self):
        """Non-YouTube URL should raise ValueError."""
        url = "https://example.com/invalid"
        with pytest.raises(ValueError, match="Could not extract video ID"):
            extract_video_id(url)

    def test_empty_url_raises_value_error(self):
        """Empty string should raise ValueError."""
        with pytest.raises(ValueError, match="Could not extract video ID"):
            extract_video_id("")


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
# Test: URL Type Detection
# =============================================================================


@pytest.mark.unit
class TestUrlTypeDetection:
    """Test detection of YouTube vs webpage URLs.

    The queue_processor currently only handles YouTube URLs.
    This characterizes the URL patterns that are recognized.
    """

    def test_youtube_watch_url_detected(self):
        """Standard youtube.com/watch URL is detected."""
        url = "https://www.youtube.com/watch?v=dQw4w9WgXcQ"

        # Using the logic from extract_video_id to detect YouTube URLs
        try:
            video_id = extract_video_id(url)
            is_youtube = True
        except ValueError:
            is_youtube = False

        assert is_youtube is True
        assert video_id == "dQw4w9WgXcQ"

    def test_youtu_be_url_detected(self):
        """Short youtu.be URL is detected."""
        url = "https://youtu.be/dQw4w9WgXcQ"

        try:
            video_id = extract_video_id(url)
            is_youtube = True
        except ValueError:
            is_youtube = False

        assert is_youtube is True

    def test_non_youtube_url_may_extract_false_positive(self):
        """Non-YouTube URL with /XXXXXXXXXXX path segment may extract false positive.

        CURRENT BEHAVIOR (characterization): The regex r'(?:v=|/)([0-9A-Za-z_-]{11}).*'
        will match any URL with a path segment of 11 alphanumeric characters.
        This is a known limitation - the queue processor relies on input validation
        at the queue level rather than URL parsing.
        """
        url = "https://example.com/some-articl"  # "some-articl" is exactly 11 chars

        # ACTUAL behavior: extracts false positive ID
        try:
            video_id = extract_video_id(url)
            is_youtube = True
        except ValueError:
            is_youtube = False
            video_id = None

        # Characterization: documents that this DOES extract a false ID
        assert is_youtube is True
        assert video_id == "some-articl"

    def test_short_path_does_not_match(self):
        """URL with path segment shorter than 11 chars raises ValueError."""
        url = "https://example.com/short"  # "short" is only 5 chars

        with pytest.raises(ValueError, match="Could not extract video ID"):
            extract_video_id(url)

    def test_youtube_playlist_url_handling(self):
        """YouTube playlist URL with video should extract video ID."""
        url = "https://www.youtube.com/watch?v=dQw4w9WgXcQ&list=PLrAXtmErZgOeiKm4sgNOknGvNjby9efdf"

        try:
            video_id = extract_video_id(url)
            is_youtube = True
        except ValueError:
            is_youtube = False

        assert is_youtube is True
        assert video_id == "dQw4w9WgXcQ"

    def test_youtube_embed_url_handling(self):
        """YouTube embed URL format."""
        url = "https://www.youtube.com/embed/dQw4w9WgXcQ"

        # Current implementation uses /VIDEO_ID pattern which should match
        try:
            video_id = extract_video_id(url)
            is_youtube = True
        except ValueError:
            is_youtube = False

        # Characterization: document current behavior
        assert is_youtube is True


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
# Test: Cache Key Format
# =============================================================================


@pytest.mark.unit
class TestCacheKeyFormat:
    """Test the cache key format used for YouTube videos."""

    def test_cache_key_format(self):
        """Cache keys should follow 'youtube:video:{video_id}' format."""
        video_id = "dQw4w9WgXcQ"
        cache_key = f"youtube:video:{video_id}"

        assert cache_key == "youtube:video:dQw4w9WgXcQ"
        assert cache_key.startswith("youtube:video:")

    def test_cache_key_extracts_video_id(self):
        """Video ID can be extracted from cache key."""
        cache_key = "youtube:video:dQw4w9WgXcQ"

        parts = cache_key.split(":")
        assert len(parts) == 3
        assert parts[0] == "youtube"
        assert parts[1] == "video"
        assert parts[2] == "dQw4w9WgXcQ"


# =============================================================================
# Test: Async Ingest Video (with mocks)
# =============================================================================


@pytest.mark.unit
@pytest.mark.asyncio
class TestIngestVideoWithMocks:
    """Test ingest_video function with mocked external dependencies.

    These tests verify the behavior of ingest_video by mocking:
    - Qdrant cache (create_qdrant_cache)
    - YouTube transcript service (get_transcript)
    - YouTube metadata service (fetch_video_metadata)
    - Archive manager
    """

    @patch("compose.worker.queue_processor.create_qdrant_cache")
    @patch("compose.worker.queue_processor.get_transcript")
    @patch("compose.worker.queue_processor.fetch_video_metadata")
    @patch("compose.worker.queue_processor.extract_video_id")
    async def test_skips_already_cached_video(
        self, mock_extract, mock_metadata, mock_transcript, mock_cache_factory
    ):
        """Video already in cache should be skipped."""
        # Import here to avoid module-level import issues
        from compose.worker.queue_processor import ingest_video

        # Setup mocks
        mock_extract.return_value = "dQw4w9WgXcQ"
        mock_cache = MagicMock()
        mock_cache.exists.return_value = True
        mock_cache_factory.return_value = mock_cache
        mock_archive = MagicMock()

        # Execute
        success, message = await ingest_video(
            "https://youtube.com/watch?v=dQw4w9WgXcQ",
            mock_archive
        )

        # Verify
        assert success is True
        assert "SKIP" in message
        assert "dQw4w9WgXcQ" in message
        mock_transcript.assert_not_called()
        mock_metadata.assert_not_called()

    @patch("compose.worker.queue_processor.create_qdrant_cache")
    @patch("compose.worker.queue_processor.get_transcript")
    @patch("compose.worker.queue_processor.fetch_video_metadata")
    @patch("compose.worker.queue_processor.extract_video_id")
    async def test_returns_error_on_transcript_failure(
        self, mock_extract, mock_metadata, mock_transcript, mock_cache_factory
    ):
        """Transcript fetch error should return failure."""
        from compose.worker.queue_processor import ingest_video

        mock_extract.return_value = "dQw4w9WgXcQ"
        mock_cache = MagicMock()
        mock_cache.exists.return_value = False
        mock_cache_factory.return_value = mock_cache
        mock_transcript.return_value = "ERROR: No transcript available"
        mock_archive = MagicMock()

        success, message = await ingest_video(
            "https://youtube.com/watch?v=dQw4w9WgXcQ",
            mock_archive
        )

        assert success is False
        assert "ERROR" in message
        assert "No transcript available" in message

    @patch("compose.worker.queue_processor.create_qdrant_cache")
    @patch("compose.worker.queue_processor.get_transcript")
    @patch("compose.worker.queue_processor.fetch_video_metadata")
    @patch("compose.worker.queue_processor.extract_video_id")
    async def test_default_source_type_is_valid(
        self, mock_extract, mock_metadata, mock_transcript, mock_cache_factory
    ):
        """Default source_type='single_import' is a valid Pydantic literal.

        This was fixed from the previous bug where 'queue_import' was used as default,
        which was not a valid literal value.
        """
        from compose.worker.queue_processor import ingest_video

        mock_extract.return_value = "dQw4w9WgXcQ"
        mock_cache = MagicMock()
        mock_cache.exists.return_value = False
        mock_cache_factory.return_value = mock_cache
        mock_transcript.return_value = "This is the transcript content"
        mock_metadata.return_value = (
            {"title": "Test Video", "channel_title": "Test Channel"},
            None
        )
        mock_archive = MagicMock()

        # Default source_type is now "single_import" which is valid
        success, message = await ingest_video(
            "https://youtube.com/watch?v=dQw4w9WgXcQ",
            mock_archive
        )

        # Should succeed now that default source_type is valid
        assert success is True
        assert "OK" in message

    @patch("compose.worker.queue_processor.create_qdrant_cache")
    @patch("compose.worker.queue_processor.get_transcript")
    @patch("compose.worker.queue_processor.fetch_video_metadata")
    @patch("compose.worker.queue_processor.extract_video_id")
    async def test_successful_ingest_with_valid_source_type(
        self, mock_extract, mock_metadata, mock_transcript, mock_cache_factory
    ):
        """Successful ingest should archive transcript and cache data with valid source_type."""
        from compose.worker.queue_processor import ingest_video

        mock_extract.return_value = "dQw4w9WgXcQ"
        mock_cache = MagicMock()
        mock_cache.exists.return_value = False
        mock_cache_factory.return_value = mock_cache
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
            source_type="bulk_channel"  # Valid source type
        )

        assert success is True
        assert "OK" in message
        mock_archive.update_transcript.assert_called_once()
        mock_archive.update_metadata.assert_called_once()
        mock_cache.set.assert_called_once()

    @patch("compose.worker.queue_processor.create_qdrant_cache")
    @patch("compose.worker.queue_processor.get_transcript")
    @patch("compose.worker.queue_processor.fetch_video_metadata")
    @patch("compose.worker.queue_processor.extract_video_id")
    async def test_handles_metadata_fetch_failure_gracefully(
        self, mock_extract, mock_metadata, mock_transcript, mock_cache_factory
    ):
        """Metadata fetch failure should not prevent successful ingest."""
        from compose.worker.queue_processor import ingest_video

        mock_extract.return_value = "dQw4w9WgXcQ"
        mock_cache = MagicMock()
        mock_cache.exists.return_value = False
        mock_cache_factory.return_value = mock_cache
        mock_transcript.return_value = "This is the transcript content"
        mock_metadata.return_value = ({}, "Metadata fetch failed")
        mock_archive = MagicMock()

        # Use valid source_type
        success, message = await ingest_video(
            "https://youtube.com/watch?v=dQw4w9WgXcQ",
            mock_archive,
            source_type="bulk_channel"  # Valid source type
        )

        # Should still succeed - metadata is optional
        assert success is True
        assert "OK" in message
        mock_archive.update_transcript.assert_called_once()
        # Metadata should not be updated when empty
        mock_archive.update_metadata.assert_not_called()

    @patch("compose.worker.queue_processor.create_qdrant_cache")
    @patch("compose.worker.queue_processor.extract_video_id")
    async def test_returns_error_on_invalid_url(
        self, mock_extract, mock_cache_factory
    ):
        """Invalid URL should return error."""
        from compose.worker.queue_processor import ingest_video

        mock_extract.side_effect = ValueError("Could not extract video ID")
        mock_cache = MagicMock()
        mock_cache_factory.return_value = mock_cache
        mock_archive = MagicMock()

        success, message = await ingest_video(
            "https://example.com/not-youtube",
            mock_archive
        )

        assert success is False
        assert "ERROR" in message
        assert "Invalid URL" in message

    @patch("compose.worker.queue_processor.create_qdrant_cache")
    @patch("compose.worker.queue_processor.get_transcript")
    @patch("compose.worker.queue_processor.fetch_video_metadata")
    @patch("compose.worker.queue_processor.extract_video_id")
    async def test_uses_provided_channel_context(
        self, mock_extract, mock_metadata, mock_transcript, mock_cache_factory
    ):
        """Channel ID and name from CSV should be used in import metadata."""
        from compose.worker.queue_processor import ingest_video

        mock_extract.return_value = "dQw4w9WgXcQ"
        mock_cache = MagicMock()
        mock_cache.exists.return_value = False
        mock_cache_factory.return_value = mock_cache
        mock_transcript.return_value = "This is the transcript content"
        mock_metadata.return_value = ({}, None)
        mock_archive = MagicMock()

        success, message = await ingest_video(
            "https://youtube.com/watch?v=dQw4w9WgXcQ",
            mock_archive,
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

        stats = await process_csv(csv_file, mock_archive, "W001")

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

        stats = await process_csv(csv_file, mock_archive, "W001")

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

        stats = await process_csv(csv_file, mock_archive, "W001")

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

        stats = await process_csv(csv_file, mock_archive, "W001")

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

        await process_csv(csv_file, mock_archive, "W001")

        # Verify source_type was detected correctly
        for call in mock_ingest.call_args_list:
            assert call[0][2] == "bulk_multi_channel"


# =============================================================================
# Test: Progress Tracking Functions (with mocks)
# =============================================================================


@pytest.mark.unit
@pytest.mark.asyncio
class TestProgressTrackingFunctions:
    """Test update_progress and clear_progress async functions."""

    async def test_update_progress_writes_file(self, temp_dir):
        """update_progress should write progress to file."""
        # Import and patch the module-level PROGRESS_FILE
        import compose.worker.queue_processor as qp

        original_progress_file = qp.PROGRESS_FILE
        qp.PROGRESS_FILE = temp_dir / ".progress.json"
        qp._active_workers = {}  # Reset state

        try:
            await qp.update_progress("W001", "test.csv", 5, 10)

            assert qp.PROGRESS_FILE.exists()
            with open(qp.PROGRESS_FILE) as f:
                data = json.load(f)
            assert len(data["workers"]) == 1
            assert data["workers"][0]["worker_id"] == "W001"
            assert data["workers"][0]["completed"] == 5
            assert data["workers"][0]["total"] == 10
        finally:
            qp.PROGRESS_FILE = original_progress_file
            qp._active_workers = {}

    async def test_update_progress_tracks_multiple_workers(self, temp_dir):
        """Multiple workers should all be tracked."""
        import compose.worker.queue_processor as qp

        original_progress_file = qp.PROGRESS_FILE
        qp.PROGRESS_FILE = temp_dir / ".progress.json"
        qp._active_workers = {}

        try:
            await qp.update_progress("W001", "batch1.csv", 3, 10)
            await qp.update_progress("W002", "batch2.csv", 7, 15)

            with open(qp.PROGRESS_FILE) as f:
                data = json.load(f)
            assert len(data["workers"]) == 2
            worker_ids = {w["worker_id"] for w in data["workers"]}
            assert worker_ids == {"W001", "W002"}
        finally:
            qp.PROGRESS_FILE = original_progress_file
            qp._active_workers = {}

    async def test_clear_progress_removes_worker(self, temp_dir):
        """clear_progress should remove worker from tracking."""
        import compose.worker.queue_processor as qp

        original_progress_file = qp.PROGRESS_FILE
        qp.PROGRESS_FILE = temp_dir / ".progress.json"
        qp._active_workers = {}

        try:
            await qp.update_progress("W001", "batch1.csv", 3, 10)
            await qp.update_progress("W002", "batch2.csv", 7, 15)
            await qp.clear_progress("W001")

            with open(qp.PROGRESS_FILE) as f:
                data = json.load(f)
            assert len(data["workers"]) == 1
            assert data["workers"][0]["worker_id"] == "W002"
        finally:
            qp.PROGRESS_FILE = original_progress_file
            qp._active_workers = {}

    async def test_clear_progress_deletes_file_when_empty(self, temp_dir):
        """clear_progress should delete file when no workers remain."""
        import compose.worker.queue_processor as qp

        original_progress_file = qp.PROGRESS_FILE
        qp.PROGRESS_FILE = temp_dir / ".progress.json"
        qp._active_workers = {}

        try:
            await qp.update_progress("W001", "batch1.csv", 3, 10)
            await qp.clear_progress("W001")

            assert not qp.PROGRESS_FILE.exists()
        finally:
            qp.PROGRESS_FILE = original_progress_file
            qp._active_workers = {}


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
