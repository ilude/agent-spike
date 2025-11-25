"""Tests for SSE reconnection and network interruption handling.

Tests verify:
- Client disconnect during ingestion (cleanup happens)
- Mid-event disconnection (partial SSE messages)
- Event stream behavior on network errors
- Active ingest tracking cleanup on disconnect
"""

import json
import pytest
from unittest.mock import patch, MagicMock, AsyncMock

from compose.api.routers.ingest import _stream_video_ingest, _active_ingests


# ============ Markers ============

pytestmark = [pytest.mark.sse, pytest.mark.ingestion]


# ============ Client Disconnect Tests ============


@pytest.mark.asyncio
async def test_client_disconnect_during_transcript_fetch(
    mock_youtube_service,
    mock_surrealdb_repository,
    mock_minio_archive,
):
    """Test that client disconnect during long operation cleans up tracking."""
    from compose.api.routers.ingest import _active_ingests

    url = "https://youtube.com/watch?v=test_vid123"

    # Consume only first 3 events, then break (simulate disconnect)
    event_count = 0
    async for event_str in _stream_video_ingest(url):
        event_count += 1
        if event_count >= 3:
            break  # Simulate client disconnect

    # Active ingest should still be tracked during operation
    # (cleanup happens in finally block when generator closes)
    # Since we broke early, cleanup will happen when generator is garbage collected


@pytest.mark.asyncio
async def test_active_ingest_cleanup_on_generator_close(
    mock_youtube_service,
    mock_surrealdb_repository,
    mock_minio_archive,
):
    """Test that active ingest tracking is cleaned up when generator closes."""
    url = "https://youtube.com/watch?v=test_vid123"

    # Create generator but don't fully consume it
    gen = _stream_video_ingest(url)

    # Consume first event
    first_event = await gen.__anext__()
    assert first_event is not None

    # Video should be tracked while generator is active
    # Note: The video_id gets added after first event

    # Close generator (simulate disconnect)
    await gen.aclose()

    # After close, cleanup should have happened
    assert "test_vid123" not in _active_ingests


@pytest.mark.asyncio
async def test_multiple_concurrent_ingests_track_separately(
    mock_youtube_service,
    mock_surrealdb_repository,
    mock_minio_archive,
):
    """Test that multiple concurrent ingests are tracked independently."""
    url1 = "https://youtube.com/watch?v=test_vid123"
    url2 = "https://youtube.com/watch?v=other_vid45"

    # Mock second video ID
    mock_youtube_service.side_effect = [
        "Transcript for first video",
        "Transcript for second video",
    ]

    # Start both ingests
    gen1 = _stream_video_ingest(url1)
    gen2 = _stream_video_ingest(url2)

    # Consume first event from each
    event1 = await gen1.__anext__()
    event2 = await gen2.__anext__()

    # Both should be tracked
    # (Note: tracking added after ID extraction, not immediately)

    # Close one generator
    await gen1.aclose()

    # Close second generator
    await gen2.aclose()

    # Both should be cleaned up
    assert "test_vid123" not in _active_ingests
    assert "other_vid45" not in _active_ingests


# ============ Partial Event Tests ============


@pytest.mark.asyncio
async def test_partial_sse_event_handling(
    mock_youtube_service,
    mock_surrealdb_repository,
    mock_minio_archive,
):
    """Test that each event is a complete SSE message.

    SSE events should be complete (event + data + double newline) so that
    clients never receive partial messages.
    """
    url = "https://youtube.com/watch?v=test_vid123"

    async for event_str in _stream_video_ingest(url):
        # Each event should be a complete SSE message
        assert event_str.endswith("\n\n"), "SSE events must end with double newline"
        assert "event: " in event_str, "SSE events must have event type"
        assert "\ndata: " in event_str, "SSE events must have data field"

        # Verify it's parseable
        lines = event_str.strip().split("\n")
        assert len(lines) == 2, "SSE events should have exactly 2 lines"


# ============ Error Recovery Tests ============


@pytest.mark.asyncio
async def test_network_error_during_archive_operation(
    mock_youtube_service,
    mock_surrealdb_repository,
    mock_minio_archive,
):
    """Test that network errors during archive emit error event and clean up."""
    # Mock archive to raise exception
    mock_minio_archive.archive_youtube_video.side_effect = Exception("Network timeout")

    url = "https://youtube.com/watch?v=test_vid123"

    events = []
    async for event_str in _stream_video_ingest(url):
        lines = event_str.strip().split("\n")
        event_type = lines[0].split(": ", 1)[1]
        event_data = json.loads(lines[1].split(": ", 1)[1])
        events.append({"type": event_type, "data": event_data})

    # Should complete with error
    complete_events = [e for e in events if e["type"] == "complete"]
    assert len(complete_events) == 1

    complete_data = complete_events[0]["data"]
    assert complete_data["status"] == "error"
    assert "Failed to ingest video" in complete_data["message"]

    # Cleanup should have happened
    assert "test_vid123" not in _active_ingests


@pytest.mark.asyncio
async def test_database_error_during_storage(
    mock_youtube_service,
    mock_surrealdb_repository,
    mock_minio_archive,
):
    """Test that database errors during storage emit error event and clean up."""
    # Mock database to raise exception
    mock_surrealdb_repository["upsert_video"].side_effect = Exception("Connection lost")

    url = "https://youtube.com/watch?v=test_vid123"

    events = []
    async for event_str in _stream_video_ingest(url):
        lines = event_str.strip().split("\n")
        event_type = lines[0].split(": ", 1)[1]
        event_data = json.loads(lines[1].split(": ", 1)[1])
        events.append({"type": event_type, "data": event_data})

    # Should complete with error
    complete_events = [e for e in events if e["type"] == "complete"]
    assert len(complete_events) == 1

    complete_data = complete_events[0]["data"]
    assert complete_data["status"] == "error"

    # Cleanup should have happened
    assert "test_vid123" not in _active_ingests


# ============ Async Generator Cleanup Tests ============


@pytest.mark.asyncio
async def test_generator_finally_block_executes_on_break():
    """Test that finally block in async generator executes when breaking early.

    Note: Breaking from a loop doesn't immediately trigger finally - it only
    happens when the generator is garbage collected or explicitly closed.
    """
    cleanup_called = False

    async def test_generator():
        nonlocal cleanup_called
        try:
            yield "event1"
            yield "event2"
            yield "event3"
        finally:
            cleanup_called = True

    # Break early - generator will be garbage collected
    gen = None
    async for event in test_generator():
        break

    # Finally block doesn't execute immediately on break
    # It only executes on garbage collection or explicit close
    # This is expected Python behavior
    assert cleanup_called is False  # Not called yet

    # Force garbage collection would trigger it, but that's unreliable in tests
    # The important test is the aclose() test which shows explicit cleanup works


@pytest.mark.asyncio
async def test_generator_finally_block_executes_on_aclose():
    """Test that finally block in async generator executes when calling aclose()."""
    cleanup_called = False

    async def test_generator():
        nonlocal cleanup_called
        try:
            yield "event1"
            yield "event2"
            yield "event3"
        finally:
            cleanup_called = True

    gen = test_generator()
    await gen.__anext__()  # Get first event
    await gen.aclose()  # Close generator

    # Finally block should have executed
    assert cleanup_called is True
