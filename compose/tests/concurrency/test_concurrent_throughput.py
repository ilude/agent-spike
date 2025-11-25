"""Tests for concurrent video ingestion throughput and resource management.

Tests verify:
- Multiple concurrent video ingestions complete successfully
- Active ingest tracking handles concurrent operations
- No race conditions in shared state (_active_ingests)
- Resource cleanup happens correctly under concurrent load
- Error in one ingestion doesn't affect others
"""

import asyncio
import json
import pytest
from unittest.mock import patch, MagicMock, AsyncMock

from compose.api.routers.ingest import _stream_video_ingest, _active_ingests


# ============ Markers ============

pytestmark = [pytest.mark.concurrency, pytest.mark.ingestion]


# ============ Concurrent Ingestion Tests ============


@pytest.mark.asyncio
async def test_concurrent_video_ingestions_complete_successfully(
    mock_youtube_service,
    mock_surrealdb_repository,
    mock_minio_archive,
):
    """Test that multiple concurrent video ingestions all complete successfully."""
    # Create 5 concurrent ingestions
    urls = [
        "https://youtube.com/watch?v=video_00001",
        "https://youtube.com/watch?v=video_00002",
        "https://youtube.com/watch?v=video_00003",
        "https://youtube.com/watch?v=video_00004",
        "https://youtube.com/watch?v=video_00005",
    ]

    async def ingest_and_collect(url):
        """Helper to ingest a video and collect completion event."""
        events = []
        async for event_str in _stream_video_ingest(url):
            lines = event_str.strip().split("\n")
            event_type = lines[0].split(": ", 1)[1]
            event_data = json.loads(lines[1].split(": ", 1)[1])
            events.append({"type": event_type, "data": event_data})

        # Return complete event
        complete_events = [e for e in events if e["type"] == "complete"]
        assert len(complete_events) == 1
        return complete_events[0]["data"]

    # Run all ingestions concurrently
    results = await asyncio.gather(*[ingest_and_collect(url) for url in urls])

    # All should complete successfully
    assert len(results) == 5
    for result in results:
        assert result["status"] == "success"
        assert result["type"] == "video"

    # All should be cleaned up
    assert len(_active_ingests) == 0


@pytest.mark.asyncio
async def test_concurrent_ingestions_track_separately(
    mock_youtube_service,
    mock_surrealdb_repository,
    mock_minio_archive,
):
    """Test that concurrent ingestions are tracked separately in _active_ingests."""
    urls = [
        "https://youtube.com/watch?v=video_00001",
        "https://youtube.com/watch?v=video_00002",
        "https://youtube.com/watch?v=video_00003",
    ]

    max_concurrent = 0
    concurrent_count_samples = []

    async def ingest_and_track(url):
        """Helper to track concurrent ingestions."""
        nonlocal max_concurrent
        async for event_str in _stream_video_ingest(url):
            # Sample concurrent count during ingestion
            current_count = len(_active_ingests)
            concurrent_count_samples.append(current_count)
            max_concurrent = max(max_concurrent, current_count)

    # Run all ingestions concurrently
    await asyncio.gather(*[ingest_and_track(url) for url in urls])

    # Should have seen multiple concurrent ingestions
    assert max_concurrent >= 2, f"Expected at least 2 concurrent ingestions, got {max_concurrent}"

    # All should be cleaned up
    assert len(_active_ingests) == 0


@pytest.mark.asyncio
async def test_high_concurrency_throughput(
    mock_youtube_service,
    mock_surrealdb_repository,
    mock_minio_archive,
):
    """Test throughput with higher concurrency (10 simultaneous ingestions)."""
    # Create 10 concurrent ingestions
    urls = [f"https://youtube.com/watch?v=vid_{i:05d}" for i in range(10)]

    async def ingest_video(url):
        """Helper to fully ingest a video."""
        events = []
        async for event_str in _stream_video_ingest(url):
            lines = event_str.strip().split("\n")
            event_type = lines[0].split(": ", 1)[1]
            events.append(event_type)
        return events

    # Run all ingestions concurrently
    import time
    start_time = time.time()
    results = await asyncio.gather(*[ingest_video(url) for url in urls])
    elapsed = time.time() - start_time

    # All should complete
    assert len(results) == 10
    for events in results:
        assert "complete" in events

    # Should complete reasonably fast (< 30 seconds for 10 mocked ingestions)
    assert elapsed < 30, f"Concurrent ingestions too slow: {elapsed:.2f}s"

    # All should be cleaned up
    assert len(_active_ingests) == 0


# ============ Error Handling Under Concurrency ============


@pytest.mark.asyncio
async def test_error_in_one_ingestion_doesnt_affect_others():
    """Test that an error in one ingestion doesn't affect concurrent ones."""
    # Create separate mocks with different behaviors
    with patch("compose.services.youtube.get_transcript") as mock_transcript, \
         patch("compose.services.surrealdb.get_video") as mock_get, \
         patch("compose.services.surrealdb.upsert_video") as mock_upsert, \
         patch("compose.services.archive.create_local_archive_writer") as mock_archive:

        # Mock get_video to return None (doesn't exist)
        async def get_video_none(*args, **kwargs):
            return None
        mock_get.side_effect = get_video_none

        # Mock transcript to succeed
        mock_transcript.return_value = "Test transcript"

        # Mock archive to succeed
        mock_archive.return_value = MagicMock(
            archive_youtube_video=MagicMock(return_value="archive/test.json")
        )

        # Track which video IDs have been seen
        call_count = {"count": 0}

        async def selective_upsert(video_record):
            """Fail for video_00002, succeed for others."""
            call_count["count"] += 1
            if video_record.video_id == "video_00002":
                raise Exception("Database error for video_00002")
            return {"video_id": video_record.video_id}

        mock_upsert.side_effect = selective_upsert

        urls = [
            "https://youtube.com/watch?v=video_00001",  # Should succeed
            "https://youtube.com/watch?v=video_00002",  # Will fail
            "https://youtube.com/watch?v=video_00003",  # Should succeed
        ]

        async def ingest_and_get_status(url):
            """Helper to get final status."""
            events = []
            async for event_str in _stream_video_ingest(url):
                lines = event_str.strip().split("\n")
                event_type = lines[0].split(": ", 1)[1]
                event_data = json.loads(lines[1].split(": ", 1)[1])
                events.append({"type": event_type, "data": event_data})

            complete_events = [e for e in events if e["type"] == "complete"]
            return complete_events[0]["data"]["status"]

        # Run all ingestions concurrently
        results = await asyncio.gather(*[ingest_and_get_status(url) for url in urls])

        # First and third should succeed, second should fail
        assert results[0] == "success"
        assert results[1] == "error"
        assert results[2] == "success"

        # All should be cleaned up
        assert len(_active_ingests) == 0


@pytest.mark.asyncio
async def test_concurrent_duplicate_video_requests(
    mock_youtube_service,
    mock_surrealdb_repository,
    mock_minio_archive,
):
    """Test concurrent requests for the same video (race condition test).

    NOTE: Without locking, both requests will succeed because both check the
    cache before either completes. This is a known race condition but is
    acceptable for the current use case (duplicate ingests are idempotent).
    """
    # Both requests for the same video
    url = "https://youtube.com/watch?v=test_vid123"

    async def ingest_and_get_status(url):
        """Helper to get final status."""
        events = []
        async for event_str in _stream_video_ingest(url):
            lines = event_str.strip().split("\n")
            event_type = lines[0].split(": ", 1)[1]
            event_data = json.loads(lines[1].split(": ", 1)[1])
            events.append({"type": event_type, "data": event_data})

        complete_events = [e for e in events if e["type"] == "complete"]
        return complete_events[0]["data"]["status"]

    # Run both ingestions concurrently
    results = await asyncio.gather(
        ingest_and_get_status(url),
        ingest_and_get_status(url),
    )

    # Both should complete (race condition - no locking)
    assert len(results) == 2

    # Depending on timing and mock interactions, various outcomes are possible:
    # 1. Both succeed (both check cache before either completes)
    # 2. One succeeds, one skipped (first completes before second checks)
    # 3. One succeeds, one errors (mock state conflicts)
    # The important thing is at least one completes
    success_count = sum(1 for s in results if s == "success")
    skipped_count = sum(1 for s in results if s == "skipped")
    error_count = sum(1 for s in results if s == "error")

    assert success_count >= 1, "At least one ingestion should succeed"
    assert success_count + skipped_count + error_count == 2, f"Unexpected statuses: {results}"

    # All should be cleaned up
    assert len(_active_ingests) == 0


# ============ Resource Cleanup Tests ============


@pytest.mark.asyncio
async def test_cleanup_with_concurrent_errors():
    """Test that cleanup happens correctly when multiple ingestions fail concurrently."""
    # Mock all services to fail
    with patch("compose.services.youtube.get_transcript") as mock_transcript, \
         patch("compose.services.surrealdb.get_video") as mock_get, \
         patch("compose.services.surrealdb.upsert_video") as mock_upsert, \
         patch("compose.services.archive.create_local_archive_writer") as mock_archive:

        mock_get.return_value = AsyncMock(return_value=None)
        mock_upsert.side_effect = AsyncMock(side_effect=Exception("Database down"))
        mock_transcript.return_value = "Test transcript"
        mock_archive.return_value = MagicMock(
            archive_youtube_video=MagicMock(return_value="archive/test.json")
        )

        urls = [
            "https://youtube.com/watch?v=video_00001",
            "https://youtube.com/watch?v=video_00002",
            "https://youtube.com/watch?v=video_00003",
        ]

        async def ingest_video(url):
            """Helper to fully ingest a video (will fail)."""
            async for event_str in _stream_video_ingest(url):
                pass  # Consume all events

        # Run all ingestions concurrently (all will fail)
        await asyncio.gather(*[ingest_video(url) for url in urls], return_exceptions=True)

        # All should be cleaned up even though they failed
        assert len(_active_ingests) == 0


@pytest.mark.asyncio
async def test_active_ingests_state_consistency():
    """Test that _active_ingests state remains consistent under concurrent access."""
    from compose.api.routers.ingest import _active_ingests

    # Mock services
    with patch("compose.services.youtube.get_transcript") as mock_transcript, \
         patch("compose.services.surrealdb.get_video") as mock_get, \
         patch("compose.services.surrealdb.upsert_video") as mock_upsert, \
         patch("compose.services.archive.create_local_archive_writer") as mock_archive:

        mock_get.return_value = AsyncMock(return_value=None)
        mock_upsert.return_value = AsyncMock(return_value={"video_id": "test"})
        mock_transcript.return_value = "Test transcript"
        mock_archive.return_value = MagicMock(
            archive_youtube_video=MagicMock(return_value="archive/test.json")
        )

        # Sample _active_ingests state during concurrent operations
        state_samples = []

        async def ingest_and_sample(url):
            """Ingest video and sample state."""
            async for event_str in _stream_video_ingest(url):
                # Sample state during each event
                state_samples.append(dict(_active_ingests))

        urls = [f"https://youtube.com/watch?v=vid_{i:05d}" for i in range(5)]

        # Run concurrent ingestions
        await asyncio.gather(*[ingest_and_sample(url) for url in urls])

        # Final state should be empty
        assert len(_active_ingests) == 0

        # All intermediate states should have been valid (no corrupted video_ids)
        for state in state_samples:
            for video_id, info in state.items():
                assert "started_at" in info
                assert "step" in info
                assert len(video_id) >= 11  # Valid video ID length
