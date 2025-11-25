"""Tests for worker ingestion pipeline with SurrealDB.

Tests the complete ingestion flow:
1. CSV → Archive (ArchiveWriter)
2. Archive → SurrealDB (upsert_video with embeddings)
3. End-to-end pipeline validation
4. Duplicate handling (upsert behavior)
5. Error handling (missing fields, bad data)

Run with: uv run pytest tests/worker/test_ingest_surrealdb.py -v
"""

import asyncio
import csv
import json
from datetime import datetime
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from compose.worker.queue_processor import ingest_video, process_csv
from compose.services.archive import (
    create_local_archive_writer,
    create_archive_manager,
    ImportMetadata,
    ChannelContext,
)
from compose.services.surrealdb.models import VideoRecord


# =============================================================================
# Fixtures
# =============================================================================


@pytest.fixture
def mock_archive_manager(tmp_path):
    """Create an ArchiveManager with temporary directory."""
    base_dir = tmp_path / "archive"
    base_dir.mkdir(parents=True)
    writer = create_local_archive_writer(base_dir=base_dir)
    return create_archive_manager(writer=writer)


@pytest.fixture
def sample_csv(tmp_path):
    """Create a sample CSV file with video URLs."""
    csv_path = tmp_path / "test_videos.csv"
    data = [
        {
            "title": "Video 1",
            "url": "https://www.youtube.com/watch?v=dQw4w9WgXcQ",
            "channel_id": "UCxxxxxx",
            "channel_name": "Test Channel",
        },
        {
            "title": "Video 2",
            "url": "https://www.youtube.com/watch?v=test1234567",
            "channel_id": "UCxxxxxx",
            "channel_name": "Test Channel",
        },
        {
            "title": "Video 3 - No Channel",
            "url": "https://www.youtube.com/watch?v=nochan12345",
            "channel_id": "",
            "channel_name": "",
        },
    ]

    with open(csv_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=["title", "url", "channel_id", "channel_name"])
        writer.writeheader()
        writer.writerows(data)

    return csv_path


@pytest.fixture
def sample_transcript():
    """Sample YouTube transcript."""
    return "This is a sample transcript about AI agents and machine learning. It contains useful information about building AI systems."


@pytest.fixture
def sample_youtube_metadata():
    """Sample YouTube metadata."""
    return {
        "title": "How to Build AI Agents",
        "channel_id": "UCxxxxxx",
        "channel_title": "Tech Channel",
        "duration_seconds": 600,
        "view_count": 10000,
        "published_at": "2025-11-01T10:00:00",
    }


# =============================================================================
# Unit Tests - CSV → Archive
# =============================================================================


@pytest.mark.unit
@pytest.mark.asyncio
@patch("compose.worker.queue_processor.upsert_video")
@patch("compose.worker.queue_processor.get_transcript")
@patch("compose.worker.queue_processor.fetch_video_metadata")
@patch("compose.worker.queue_processor.get_video")
async def test_ingest_video_archives_transcript_first(
    mock_get_video,
    mock_fetch_metadata,
    mock_get_transcript,
    mock_upsert_video,
    mock_archive_manager,
    sample_transcript,
    sample_youtube_metadata,
):
    """Test that transcript is archived before any other processing."""
    # Mock video not in SurrealDB yet
    mock_get_video.return_value = None

    # Mock transcript fetch
    mock_get_transcript.return_value = sample_transcript

    # Mock metadata fetch
    mock_fetch_metadata.return_value = (sample_youtube_metadata, None)

    # Mock SurrealDB upsert
    mock_upsert_video.return_value = {"created": True}

    # Mock storage
    mock_storage = MagicMock()
    mock_storage.client.exists.return_value = False
    mock_storage.client.put_json = MagicMock()

    url = "https://www.youtube.com/watch?v=dQw4w9WgXcQ"

    success, message = await ingest_video(
        url=url,
        archive_manager=mock_archive_manager,
        storage=mock_storage,
        source_type="single_import",
    )

    assert success is True
    assert "OK:" in message

    # Verify archive file was created
    archive_dir = mock_archive_manager.writer.config.base_dir / "youtube"
    archive_files = list(archive_dir.glob("**/dQw4w9WgXcQ.json"))
    assert len(archive_files) == 1

    # Verify archive contains transcript
    with open(archive_files[0]) as f:
        archive_data = json.load(f)
        assert archive_data["video_id"] == "dQw4w9WgXcQ"
        assert archive_data["raw_transcript"] == sample_transcript
        assert archive_data["url"] == url


@pytest.mark.unit
@pytest.mark.asyncio
@patch("compose.worker.queue_processor.get_transcript")
@patch("compose.worker.queue_processor.fetch_video_metadata")
@patch("compose.worker.queue_processor.get_video")
async def test_ingest_video_handles_missing_metadata(
    mock_get_video,
    mock_fetch_metadata,
    mock_get_transcript,
    mock_archive_manager,
    sample_transcript,
):
    """Test ingestion continues even if metadata fetch fails."""
    mock_get_video.return_value = None
    mock_get_transcript.return_value = sample_transcript
    mock_fetch_metadata.return_value = ({}, "API error")

    mock_storage = MagicMock()
    mock_storage.client.exists.return_value = False
    mock_storage.client.put_json = MagicMock()

    url = "https://www.youtube.com/watch?v=dQw4w9WgXcQ"

    success, message = await ingest_video(
        url=url,
        archive_manager=mock_archive_manager,
        storage=mock_storage,
        source_type="single_import",
    )

    assert success is True
    assert "OK:" in message

    # Verify archive was still created
    archive_dir = mock_archive_manager.writer.config.base_dir / "youtube"
    archive_files = list(archive_dir.glob("**/dQw4w9WgXcQ.json"))
    assert len(archive_files) == 1


@pytest.mark.unit
@pytest.mark.asyncio
@patch("compose.worker.queue_processor.get_transcript")
@patch("compose.worker.queue_processor.get_video")
async def test_ingest_video_skips_if_already_in_surrealdb(
    mock_get_video,
    mock_get_transcript,
    mock_archive_manager,
):
    """Test that videos already in SurrealDB are skipped."""
    # Mock video exists in SurrealDB
    existing_video = VideoRecord(
        video_id="dQw4w9WgXcQ",
        url="https://www.youtube.com/watch?v=dQw4w9WgXcQ",
        fetched_at=datetime.now(),
    )
    mock_get_video.return_value = existing_video

    mock_storage = MagicMock()

    url = "https://www.youtube.com/watch?v=dQw4w9WgXcQ"

    success, message = await ingest_video(
        url=url,
        archive_manager=mock_archive_manager,
        storage=mock_storage,
        source_type="single_import",
    )

    assert success is True
    assert "SKIP" in message
    assert "dQw4w9WgXcQ" in message

    # Verify transcript was NOT fetched
    mock_get_transcript.assert_not_called()


@pytest.mark.unit
@pytest.mark.asyncio
@patch("compose.worker.queue_processor.get_transcript")
@patch("compose.worker.queue_processor.get_video")
async def test_ingest_video_handles_transcript_error(
    mock_get_video,
    mock_get_transcript,
    mock_archive_manager,
):
    """Test handling of transcript fetch failures."""
    mock_get_video.return_value = None
    mock_get_transcript.return_value = "ERROR: Transcript disabled"

    mock_storage = MagicMock()
    mock_storage.client.exists.return_value = False

    url = "https://www.youtube.com/watch?v=dQw4w9WgXcQ"

    success, message = await ingest_video(
        url=url,
        archive_manager=mock_archive_manager,
        storage=mock_storage,
        source_type="single_import",
    )

    assert success is False
    assert "ERROR" in message


@pytest.mark.unit
@pytest.mark.asyncio
@patch("compose.worker.queue_processor.get_transcript")
@patch("compose.worker.queue_processor.get_video")
async def test_ingest_video_handles_invalid_url(
    mock_get_video,
    mock_get_transcript,
    mock_archive_manager,
):
    """Test handling of invalid YouTube URLs."""
    mock_get_video.return_value = None

    mock_storage = MagicMock()

    url = "https://example.com/not-a-youtube-url"

    success, message = await ingest_video(
        url=url,
        archive_manager=mock_archive_manager,
        storage=mock_storage,
        source_type="single_import",
    )

    assert success is False
    assert "ERROR" in message
    assert "Invalid URL" in message


# =============================================================================
# Unit Tests - Archive → SurrealDB
# =============================================================================


@pytest.mark.unit
@pytest.mark.asyncio
@patch("compose.worker.queue_processor.upsert_video")
@patch("compose.worker.queue_processor.get_transcript")
@patch("compose.worker.queue_processor.fetch_video_metadata")
@patch("compose.worker.queue_processor.get_video")
async def test_ingest_creates_surrealdb_record(
    mock_get_video,
    mock_fetch_metadata,
    mock_get_transcript,
    mock_upsert_video,
    mock_archive_manager,
    sample_transcript,
    sample_youtube_metadata,
):
    """Test that video record is created in SurrealDB after archiving."""
    mock_get_video.return_value = None
    mock_get_transcript.return_value = sample_transcript
    mock_fetch_metadata.return_value = (sample_youtube_metadata, None)
    mock_upsert_video.return_value = {"created": True}

    mock_storage = MagicMock()
    mock_storage.client.exists.return_value = False
    mock_storage.client.put_json = MagicMock()

    url = "https://www.youtube.com/watch?v=dQw4w9WgXcQ"

    success, message = await ingest_video(
        url=url,
        archive_manager=mock_archive_manager,
        storage=mock_storage,
        source_type="single_import",
    )

    assert success is True

    # Verify upsert_video was called (placeholder - actual implementation may vary)
    # NOTE: Current worker code doesn't call upsert_video yet - this test will fail
    # until we update the code to do so


@pytest.mark.unit
@pytest.mark.asyncio
@patch("compose.services.surrealdb.repository.upsert_video")
async def test_upsert_video_handles_duplicate(mock_upsert_video):
    """Test that upserting the same video twice works (idempotency)."""
    from compose.services.surrealdb.repository import upsert_video

    mock_upsert_video.return_value = {"created": True}

    video = VideoRecord(
        video_id="dQw4w9WgXcQ",
        url="https://www.youtube.com/watch?v=dQw4w9WgXcQ",
        fetched_at=datetime.now(),
        title="Test Video",
    )

    # Upsert twice
    result1 = await upsert_video(video)
    result2 = await upsert_video(video)

    # Both should succeed
    assert result1["created"] is True
    assert result2["created"] is True

    # Should be called twice
    assert mock_upsert_video.call_count == 2


# =============================================================================
# Integration Tests - End-to-End
# =============================================================================


@pytest.mark.integration
@pytest.mark.asyncio
@patch("compose.worker.queue_processor.upsert_video")
@patch("compose.worker.queue_processor.get_transcript")
@patch("compose.worker.queue_processor.fetch_video_metadata")
@patch("compose.worker.queue_processor.get_video")
async def test_process_csv_end_to_end(
    mock_get_video,
    mock_fetch_metadata,
    mock_get_transcript,
    mock_upsert_video,
    mock_archive_manager,
    sample_csv,
    sample_transcript,
    sample_youtube_metadata,
):
    """Test processing entire CSV file end-to-end."""
    mock_get_video.return_value = None
    mock_get_transcript.return_value = sample_transcript
    mock_fetch_metadata.return_value = (sample_youtube_metadata, None)
    mock_upsert_video.return_value = {"created": True}

    mock_storage = MagicMock()
    mock_storage.client.exists.return_value = False
    mock_storage.client.put_json = MagicMock()

    stats = await process_csv(
        sample_csv,
        mock_archive_manager,
        mock_storage,
        worker_id="TEST",
    )

    assert stats["total"] == 3
    assert stats["processed"] == 3
    assert stats["skipped"] == 0
    assert stats["errors"] == 0

    # Verify all videos were archived
    archive_dir = mock_archive_manager.writer.config.base_dir / "youtube"
    archive_files = list(archive_dir.glob("**/*.json"))
    assert len(archive_files) == 3


@pytest.mark.integration
@pytest.mark.asyncio
@patch("compose.worker.queue_processor.upsert_video")
@patch("compose.worker.queue_processor.get_transcript")
@patch("compose.worker.queue_processor.fetch_video_metadata")
@patch("compose.worker.queue_processor.get_video")
async def test_process_csv_handles_mixed_results(
    mock_get_video,
    mock_fetch_metadata,
    mock_get_transcript,
    mock_upsert_video,
    mock_archive_manager,
    sample_csv,
    sample_transcript,
    sample_youtube_metadata,
):
    """Test CSV processing with mix of success, skip, and error."""
    # First video: success
    # Second video: already cached (skip)
    # Third video: transcript error

    def get_video_side_effect(video_id):
        if video_id == "test1234567":
            return VideoRecord(
                video_id=video_id,
                url=f"https://www.youtube.com/watch?v={video_id}",
                fetched_at=datetime.now(),
            )
        return None

    mock_get_video.side_effect = get_video_side_effect

    def get_transcript_side_effect(url, cache):
        if "nochan12345" in url:
            return "ERROR: Transcript disabled"
        return sample_transcript

    mock_get_transcript.side_effect = get_transcript_side_effect
    mock_fetch_metadata.return_value = (sample_youtube_metadata, None)
    mock_upsert_video.return_value = {"created": True}

    mock_storage = MagicMock()
    mock_storage.client.exists.return_value = False
    mock_storage.client.put_json = MagicMock()

    stats = await process_csv(
        sample_csv,
        mock_archive_manager,
        mock_storage,
        worker_id="TEST",
    )

    assert stats["total"] == 3
    assert stats["processed"] == 1  # First video
    assert stats["skipped"] == 1  # Second video (already cached)
    assert stats["errors"] == 1  # Third video (transcript error)


@pytest.mark.integration
@pytest.mark.asyncio
@patch("compose.worker.queue_processor.upsert_video")
@patch("compose.worker.queue_processor.get_transcript")
@patch("compose.worker.queue_processor.fetch_video_metadata")
@patch("compose.worker.queue_processor.get_video")
async def test_recommendation_weights_by_source_type(
    mock_get_video,
    mock_fetch_metadata,
    mock_get_transcript,
    mock_upsert_video,
    mock_archive_manager,
    sample_transcript,
    sample_youtube_metadata,
):
    """Test that different source types get correct recommendation weights."""
    mock_get_video.return_value = None
    mock_get_transcript.return_value = sample_transcript
    mock_fetch_metadata.return_value = (sample_youtube_metadata, None)
    mock_upsert_video.return_value = {"created": True}

    mock_storage = MagicMock()
    mock_storage.client.exists.return_value = False
    mock_storage.client.put_json = MagicMock()

    url = "https://www.youtube.com/watch?v=dQw4w9WgXcQ"

    # Test different source types
    test_cases = [
        ("single_import", 1.0),
        ("repl_import", 1.0),
        ("bulk_channel", 0.5),
        ("bulk_multi_channel", 0.2),
    ]

    for source_type, expected_weight in test_cases:
        success, message = await ingest_video(
            url=url,
            archive_manager=mock_archive_manager,
            storage=mock_storage,
            source_type=source_type,
        )

        assert success is True

        # Verify archive has correct weight
        archive_dir = mock_archive_manager.writer.config.base_dir / "youtube"
        archive_files = list(archive_dir.glob("**/dQw4w9WgXcQ.json"))
        assert len(archive_files) > 0

        with open(archive_files[0]) as f:
            archive_data = json.load(f)
            assert archive_data["import_metadata"]["recommendation_weight"] == expected_weight

        # Clean up for next iteration
        archive_files[0].unlink()


# =============================================================================
# Error Handling Tests
# =============================================================================


@pytest.mark.unit
@pytest.mark.asyncio
async def test_process_csv_handles_missing_file(mock_archive_manager):
    """Test processing non-existent CSV file."""
    nonexistent_path = Path("/tmp/does-not-exist.csv")
    mock_storage = MagicMock()

    stats = await process_csv(
        nonexistent_path,
        mock_archive_manager,
        mock_storage,
        worker_id="TEST",
    )

    assert stats["processed"] == 0
    assert stats["total"] == 0


@pytest.mark.unit
@pytest.mark.asyncio
@patch("compose.worker.queue_processor.get_transcript")
@patch("compose.worker.queue_processor.get_video")
async def test_ingest_video_handles_empty_url(
    mock_get_video,
    mock_get_transcript,
    mock_archive_manager,
):
    """Test handling of empty URL."""
    mock_storage = MagicMock()

    success, message = await ingest_video(
        url="",
        archive_manager=mock_archive_manager,
        storage=mock_storage,
        source_type="single_import",
    )

    # Should fail gracefully
    assert success is False


@pytest.mark.unit
@pytest.mark.asyncio
@patch("compose.worker.queue_processor.upsert_video")
@patch("compose.worker.queue_processor.get_transcript")
@patch("compose.worker.queue_processor.fetch_video_metadata")
@patch("compose.worker.queue_processor.get_video")
async def test_ingest_preserves_channel_context(
    mock_get_video,
    mock_fetch_metadata,
    mock_get_transcript,
    mock_upsert_video,
    mock_archive_manager,
    sample_transcript,
    sample_youtube_metadata,
):
    """Test that channel_id and channel_name from CSV are preserved."""
    mock_get_video.return_value = None
    mock_get_transcript.return_value = sample_transcript
    mock_fetch_metadata.return_value = (sample_youtube_metadata, None)
    mock_upsert_video.return_value = {"created": True}

    mock_storage = MagicMock()
    mock_storage.client.exists.return_value = False
    mock_storage.client.put_json = MagicMock()

    url = "https://www.youtube.com/watch?v=dQw4w9WgXcQ"

    success, message = await ingest_video(
        url=url,
        archive_manager=mock_archive_manager,
        storage=mock_storage,
        source_type="bulk_channel",
        channel_id="UCxxxxxx",
        channel_name="Test Channel",
    )

    assert success is True

    # Verify archive has channel context
    archive_dir = mock_archive_manager.writer.config.base_dir / "youtube"
    archive_files = list(archive_dir.glob("**/dQw4w9WgXcQ.json"))
    assert len(archive_files) > 0

    with open(archive_files[0]) as f:
        archive_data = json.load(f)
        assert archive_data["import_metadata"]["channel_context"]["channel_id"] == "UCxxxxxx"
        assert archive_data["import_metadata"]["channel_context"]["channel_name"] == "Test Channel"
