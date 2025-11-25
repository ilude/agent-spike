"""Tests for ingestion cancellation and cleanup verification.

Tests verify:
- Cleanup happens when client cancels mid-ingestion
- Active ingest tracking is properly cleaned up on cancellation
- Resources are released on cancellation
- No lingering state after cancellation
"""

import asyncio
import json
import pytest
from unittest.mock import patch, MagicMock, AsyncMock

from compose.api.routers.ingest import _stream_video_ingest, _active_ingests


# ============ Markers ============

pytestmark = [pytest.mark.sse, pytest.mark.ingestion]


# ============ Cancellation Tests ============


@pytest.mark.asyncio
async def test_cancellation_during_transcript_fetch(
    mock_youtube_service,
    mock_surrealdb_repository,
    mock_minio_archive,
):
    """Test cancellation during transcript fetching cleans up properly."""
    url = "https://youtube.com/watch?v=test_vid123"

    # Create a task for the ingestion
    async def consume_events():
        event_count = 0
        async for event_str in _stream_video_ingest(url):
            event_count += 1
            if event_count >= 3:  # Consume a few events then cancel
                raise asyncio.CancelledError()
        return event_count

    # Run and expect cancellation
    with pytest.raises(asyncio.CancelledError):
        await consume_events()

    # Give cleanup a moment to run
    await asyncio.sleep(0.1)

    # Active ingest should be cleaned up
    assert "test_vid123" not in _active_ingests


@pytest.mark.asyncio
async def test_cancellation_during_archiving(
    mock_youtube_service,
    mock_surrealdb_repository,
    mock_minio_archive,
):
    """Test cancellation by closing generator mid-stream."""
    url = "https://youtube.com/watch?v=test_vid123"

    # Create generator
    gen = _stream_video_ingest(url)

    # Consume a few events
    event_count = 0
    async for event_str in gen:
        event_count += 1
        if event_count >= 5:  # After archiving step starts
            break

    # Close generator (simulate cancellation)
    await gen.aclose()

    # Give cleanup a moment
    await asyncio.sleep(0.1)

    # Active ingest should be cleaned up
    assert "test_vid123" not in _active_ingests


@pytest.mark.asyncio
async def test_multiple_cancellations_cleanup_independently(
    mock_youtube_service,
    mock_surrealdb_repository,
    mock_minio_archive,
):
    """Test that multiple concurrent cancellations clean up independently."""
    urls = [
        "https://youtube.com/watch?v=video_00001",
        "https://youtube.com/watch?v=video_00002",
        "https://youtube.com/watch?v=video_00003",
    ]

    # Create tasks for all ingestions
    tasks = [asyncio.create_task(_consume_all_events(url)) for url in urls]

    # Wait a bit for them to start
    await asyncio.sleep(0.1)

    # Cancel all tasks
    for task in tasks:
        task.cancel()

    # Wait for cancellations
    for task in tasks:
        try:
            await task
        except asyncio.CancelledError:
            pass

    # Give cleanup a moment
    await asyncio.sleep(0.1)

    # All should be cleaned up
    assert len(_active_ingests) == 0


# ============ Resource Cleanup Tests ============


@pytest.mark.asyncio
async def test_cleanup_happens_even_with_exception_during_cancellation(
    mock_youtube_service,
    mock_surrealdb_repository,
    mock_minio_archive,
):
    """Test that cleanup happens even if an exception occurs during cancellation."""
    # Mock archive to raise exception during cancellation
    call_count = {"count": 0}

    def failing_archive(*args, **kwargs):
        call_count["count"] += 1
        if call_count["count"] == 1:
            raise Exception("Archive failure during cancellation")
        return "archive/test.json"

    mock_minio_archive.archive_youtube_video.side_effect = failing_archive

    url = "https://youtube.com/watch?v=test_vid123"

    # Create task
    task = asyncio.create_task(_consume_all_events(url))

    # Wait for it to hit the archive step
    await asyncio.sleep(0.1)

    # Cancel
    task.cancel()

    # Should still complete cleanup despite exception
    try:
        await task
    except (asyncio.CancelledError, Exception):
        pass

    # Give cleanup a moment
    await asyncio.sleep(0.1)

    # Should still be cleaned up
    assert "test_vid123" not in _active_ingests


@pytest.mark.asyncio
async def test_cancellation_before_video_id_extraction():
    """Test cancellation before video ID is even extracted."""
    url = "https://youtube.com/watch?v=test_vid123"

    # Create generator but cancel immediately
    gen = _stream_video_ingest(url)

    # Close before consuming any events
    await gen.aclose()

    # Nothing should be tracked (ID not yet extracted)
    assert "test_vid123" not in _active_ingests


@pytest.mark.asyncio
async def test_cancellation_after_cache_check(
    mock_youtube_service,
    mock_surrealdb_repository,
    mock_minio_archive,
):
    """Test cancellation after cache check by closing generator early."""
    url = "https://youtube.com/watch?v=test_vid123"

    # Create generator
    gen = _stream_video_ingest(url)

    # Consume events up to cache check (first 3 events)
    event_count = 0
    async for event_str in gen:
        event_count += 1
        if event_count >= 3:  # After cache check
            break

    # Close generator
    await gen.aclose()

    # Give cleanup a moment
    await asyncio.sleep(0.1)

    # Should be cleaned up
    assert "test_vid123" not in _active_ingests


# ============ Helper Functions ============


async def _consume_all_events(url: str) -> int:
    """Helper to consume all events from an ingestion stream."""
    event_count = 0
    async for event_str in _stream_video_ingest(url):
        event_count += 1
    return event_count
