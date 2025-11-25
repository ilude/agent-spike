"""Tests for SSE streaming video ingestion.

Tests verify:
- All progress events arrive in correct sequence
- Event payloads match expected schema
- Complete event includes video metadata
- Error events are emitted on failure
- Skip events for duplicate videos
- Cleanup happens on success/error
"""

import json
import pytest
from datetime import datetime
from unittest.mock import patch, MagicMock, AsyncMock

from compose.api.routers.ingest import _stream_video_ingest


# ============ Markers ============

pytestmark = [pytest.mark.sse, pytest.mark.ingestion]


# ============ Successful Ingestion Tests ============


@pytest.mark.asyncio
async def test_video_ingest_complete_event_sequence(
    mock_youtube_service,
    mock_surrealdb_repository,
    mock_minio_archive,
):
    """Test complete SSE event sequence for successful video ingestion."""
    url = "https://youtube.com/watch?v=test_vid123"

    # Collect all SSE events
    events = []
    async for event_str in _stream_video_ingest(url):
        # Parse SSE format: "event: TYPE\ndata: JSON\n\n"
        lines = event_str.strip().split("\n")
        event_type = lines[0].split(": ", 1)[1]
        event_data = json.loads(lines[1].split(": ", 1)[1])
        events.append({"type": event_type, "data": event_data})

    # Verify event sequence
    expected_steps = [
        "extracting_id",
        "extracted_id",
        "checking_cache",
        "fetching_transcript",
        "transcript_fetched",
        "archiving",
        "archived",
        "storing",
        "stored",
    ]

    progress_events = [e for e in events if e["type"] == "progress"]
    actual_steps = [e["data"]["step"] for e in progress_events]

    assert actual_steps == expected_steps, f"Expected {expected_steps}, got {actual_steps}"

    # Verify complete event
    complete_events = [e for e in events if e["type"] == "complete"]
    assert len(complete_events) == 1, "Should have exactly one complete event"

    complete_data = complete_events[0]["data"]
    assert complete_data["type"] == "video"
    assert complete_data["status"] == "success"
    assert "test_vid123" in complete_data["message"]
    assert "video_id" in complete_data["details"]
    assert "transcript_length" in complete_data["details"]


@pytest.mark.asyncio
async def test_video_ingest_event_payloads(
    mock_youtube_service,
    mock_surrealdb_repository,
    mock_minio_archive,
):
    """Test that event payloads match expected schema."""
    url = "https://youtube.com/watch?v=test_vid123"

    events = []
    async for event_str in _stream_video_ingest(url):
        lines = event_str.strip().split("\n")
        event_type = lines[0].split(": ", 1)[1]
        event_data = json.loads(lines[1].split(": ", 1)[1])
        events.append({"type": event_type, "data": event_data})

    # Check specific event payloads
    progress_events = {e["data"]["step"]: e["data"] for e in events if e["type"] == "progress"}

    # extracted_id event should include video_id
    assert "video_id" in progress_events["extracted_id"]
    assert progress_events["extracted_id"]["video_id"] == "test_vid123"

    # transcript_fetched event should include transcript_length
    assert "transcript_length" in progress_events["transcript_fetched"]
    assert isinstance(progress_events["transcript_fetched"]["transcript_length"], int)

    # All progress events should have step and message
    for step, data in progress_events.items():
        assert "step" in data, f"Event {step} missing 'step' field"
        assert "message" in data, f"Event {step} missing 'message' field"


# ============ Duplicate Video Tests ============


@pytest.mark.asyncio
async def test_video_ingest_skips_duplicate(
    mock_youtube_service,
    mock_surrealdb_repository,
    mock_minio_archive,
):
    """Test that duplicate videos emit skip event."""
    # Mock video already exists
    mock_surrealdb_repository["get_video"].return_value = {
        "video_id": "test_vid123",
        "title": "Existing Video",
    }

    url = "https://youtube.com/watch?v=test_vid123"

    events = []
    async for event_str in _stream_video_ingest(url):
        lines = event_str.strip().split("\n")
        event_type = lines[0].split(": ", 1)[1]
        event_data = json.loads(lines[1].split(": ", 1)[1])
        events.append({"type": event_type, "data": event_data})

    # Should complete early with skipped status
    complete_events = [e for e in events if e["type"] == "complete"]
    assert len(complete_events) == 1

    complete_data = complete_events[0]["data"]
    assert complete_data["status"] == "skipped"
    assert "already cached" in complete_data["message"].lower()

    # Should NOT attempt to archive or store
    progress_events = [e for e in events if e["type"] == "progress"]
    steps = [e["data"]["step"] for e in progress_events]
    assert "archiving" not in steps
    assert "storing" not in steps


# ============ Error Handling Tests ============


@pytest.mark.asyncio
async def test_video_ingest_transcript_error(
    mock_surrealdb_repository,
    mock_minio_archive,
):
    """Test error event when transcript fetch fails."""
    # Mock transcript error
    with patch("compose.services.youtube.get_transcript") as mock_get_transcript:
        mock_get_transcript.return_value = "ERROR: Transcript not available"

        url = "https://youtube.com/watch?v=test_vid123"

        events = []
        async for event_str in _stream_video_ingest(url):
            lines = event_str.strip().split("\n")
            event_type = lines[0].split(": ", 1)[1]
            event_data = json.loads(lines[1].split(": ", 1)[1])
            events.append({"type": event_type, "data": event_data})

        # Should complete with error status
        complete_events = [e for e in events if e["type"] == "complete"]
        assert len(complete_events) == 1

        complete_data = complete_events[0]["data"]
        assert complete_data["status"] == "error"
        assert "ERROR:" in complete_data["message"]


@pytest.mark.asyncio
async def test_video_ingest_exception_handling(
    mock_youtube_service,
    mock_surrealdb_repository,
    mock_minio_archive,
):
    """Test that unexpected exceptions emit error event."""
    # Mock database operation to raise exception
    mock_surrealdb_repository["upsert_video"].side_effect = Exception("Database connection failed")

    url = "https://youtube.com/watch?v=test_vid123"

    events = []
    async for event_str in _stream_video_ingest(url):
        lines = event_str.strip().split("\n")
        event_type = lines[0].split(": ", 1)[1]
        event_data = json.loads(lines[1].split(": ", 1)[1])
        events.append({"type": event_type, "data": event_data})

    # Should complete with error status
    complete_events = [e for e in events if e["type"] == "complete"]
    assert len(complete_events) == 1

    complete_data = complete_events[0]["data"]
    assert complete_data["status"] == "error"
    assert "Failed to ingest video" in complete_data["message"]


# ============ Cleanup Tests ============


@pytest.mark.asyncio
async def test_video_ingest_cleanup_on_success(
    mock_youtube_service,
    mock_surrealdb_repository,
    mock_minio_archive,
):
    """Test that active ingest tracking is cleaned up on success."""
    from compose.api.routers.ingest import _active_ingests

    url = "https://youtube.com/watch?v=test_vid123"

    # Consume all events
    async for _ in _stream_video_ingest(url):
        pass

    # Active ingest should be removed
    assert "test_vid123" not in _active_ingests


@pytest.mark.asyncio
async def test_video_ingest_cleanup_on_error(
    mock_youtube_service,
    mock_surrealdb_repository,
    mock_minio_archive,
):
    """Test that active ingest tracking is cleaned up on error."""
    from compose.api.routers.ingest import _active_ingests

    # Mock error
    mock_surrealdb_repository["upsert_video"].side_effect = Exception("Test error")

    url = "https://youtube.com/watch?v=test_vid123"

    # Consume all events
    async for _ in _stream_video_ingest(url):
        pass

    # Active ingest should be removed even on error
    assert "test_vid123" not in _active_ingests


# ============ Service Integration Tests ============


@pytest.mark.asyncio
async def test_video_ingest_calls_services_correctly(
    mock_youtube_service,
    mock_surrealdb_repository,
    mock_minio_archive,
):
    """Test that ingestion calls all services with correct arguments."""
    url = "https://youtube.com/watch?v=test_vid123"

    # Consume all events
    async for _ in _stream_video_ingest(url):
        pass

    # Verify YouTube service was called
    mock_youtube_service.assert_called_once()

    # Verify database operations
    mock_surrealdb_repository["get_video"].assert_called_once()
    mock_surrealdb_repository["upsert_video"].assert_called_once()

    # Verify MinIO archive was called
    mock_minio_archive.archive_youtube_video.assert_called_once()

    # Verify archive was called with correct video_id
    call_args = mock_minio_archive.archive_youtube_video.call_args
    assert call_args.kwargs["video_id"] == "test_vid123"
    assert call_args.kwargs["url"] == url


# ============ Event Format Tests ============


@pytest.mark.asyncio
async def test_video_ingest_sse_format(
    mock_youtube_service,
    mock_surrealdb_repository,
    mock_minio_archive,
):
    """Test that events are properly formatted as SSE."""
    url = "https://youtube.com/watch?v=test_vid123"

    async for event_str in _stream_video_ingest(url):
        # Should be valid SSE format: "event: TYPE\ndata: JSON\n\n"
        assert event_str.startswith("event: ")
        assert "\ndata: " in event_str
        assert event_str.endswith("\n\n")

        # Should have exactly 2 lines (event and data)
        lines = event_str.strip().split("\n")
        assert len(lines) == 2

        # Event type should be "progress" or "complete"
        event_type = lines[0].split(": ", 1)[1]
        assert event_type in ["progress", "complete"]

        # Data should be valid JSON
        data_str = lines[1].split(": ", 1)[1]
        try:
            json.loads(data_str)
        except json.JSONDecodeError:
            pytest.fail(f"Invalid JSON in event data: {data_str}")
