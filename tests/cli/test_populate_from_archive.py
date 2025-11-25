"""Tests for populate_surrealdb_from_archive.py

Run with: uv run pytest tests/cli/test_populate_from_archive.py -v
"""

import json
from datetime import datetime
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from compose.cli.populate_surrealdb_from_archive import (
    find_archive_files,
    parse_archive,
    generate_metadata_text,
    generate_embedding,
    populate_single_video,
)
from compose.services.surrealdb.models import VideoRecord


@pytest.fixture
def sample_archive_data():
    """Sample archive JSON matching the actual format."""
    return {
        "video_id": "dQw4w9WgXcQ",
        "url": "https://www.youtube.com/watch?v=dQw4w9WgXcQ",
        "fetched_at": "2025-11-24T12:00:00",
        "raw_transcript": "This is a sample transcript about AI agents.",
        "youtube_metadata": {
            "title": "How to Build AI Agents",
            "channel_id": "UCxxxxxx",
            "channel_title": "Tech Channel",
            "duration_seconds": 600,
            "view_count": 10000,
            "published_at": "2025-11-01T10:00:00",
        },
        "llm_outputs": [
            {
                "output_type": "metadata",
                "output_value": {
                    "title": "How to Build AI Agents",
                    "summary": "A comprehensive guide to building AI agents",
                    "subject_matter": ["ai", "agents", "tutorial"],
                },
                "model": "claude-3-5-haiku-20241022",
                "cost_usd": 0.0012,
            }
        ],
        "processing_records": [],
        "import_metadata": {
            "source_type": "youtube_channel",
            "import_method": "api",
            "recommendation_weight": 1.0,
        },
    }


@pytest.fixture
def temp_archive_dir(tmp_path):
    """Create temporary archive directory with sample files."""
    archive_dir = tmp_path / "archive" / "youtube" / "2025-11"
    archive_dir.mkdir(parents=True)

    # Create sample archive file
    archive_data = {
        "video_id": "test123",
        "url": "https://www.youtube.com/watch?v=test123",
        "fetched_at": "2025-11-24T12:00:00",
        "raw_transcript": "Test transcript",
        "youtube_metadata": {
            "title": "Test Video",
            "channel_title": "Test Channel",
        },
        "llm_outputs": [],
    }

    archive_file = archive_dir / "test123.json"
    with open(archive_file, "w") as f:
        json.dump(archive_data, f)

    return tmp_path / "archive" / "youtube"


@pytest.mark.unit
def test_find_archive_files(temp_archive_dir):
    """Test finding archive JSON files in month directories."""
    files = find_archive_files(temp_archive_dir)

    assert len(files) == 1
    assert files[0].name == "test123.json"
    assert files[0].parent.name == "2025-11"


@pytest.mark.unit
def test_find_archive_files_empty_dir(tmp_path):
    """Test find_archive_files with empty directory."""
    empty_dir = tmp_path / "empty"
    empty_dir.mkdir()

    files = find_archive_files(empty_dir)
    assert len(files) == 0


@pytest.mark.unit
def test_parse_archive(temp_archive_dir):
    """Test parsing archive JSON file."""
    files = find_archive_files(temp_archive_dir)
    archive_data = parse_archive(files[0])

    assert archive_data["video_id"] == "test123"
    assert archive_data["url"] == "https://www.youtube.com/watch?v=test123"
    assert "youtube_metadata" in archive_data


@pytest.mark.unit
def test_generate_metadata_text(sample_archive_data):
    """Test generating metadata text for embedding."""
    text = generate_metadata_text(sample_archive_data)

    assert "Video ID: dQw4w9WgXcQ" in text
    assert "Channel: Tech Channel" in text
    assert "Title: How to Build AI Agents" in text
    assert "Summary: A comprehensive guide to building AI agents" in text
    assert "Topics: ai agents tutorial" in text


@pytest.mark.unit
def test_generate_metadata_text_minimal():
    """Test metadata text generation with minimal data."""
    minimal_data = {
        "video_id": "test123",
        "youtube_metadata": {
            "title": "Test Video",
            "channel_title": "Test Channel",
        },
        "llm_outputs": [],
    }

    text = generate_metadata_text(minimal_data)

    assert "Video ID: test123" in text
    assert "Channel: Test Channel" in text
    assert "Title: Test Video" in text
    # Summary and Topics should be empty but present
    assert "Summary:" in text
    assert "Topics:" in text


@pytest.mark.unit
def test_generate_metadata_text_truncation():
    """Test that very long text gets truncated."""
    long_data = {
        "video_id": "test123",
        "youtube_metadata": {
            "title": "A" * 10000,  # Very long title
            "channel_title": "Test Channel",
        },
        "llm_outputs": [],
    }

    text = generate_metadata_text(long_data, max_chars=500)

    assert len(text) <= 500


@pytest.mark.unit
@patch("compose.cli.populate_surrealdb_from_archive.httpx.post")
def test_generate_embedding(mock_post):
    """Test embedding generation via Infinity API."""
    # Mock Infinity API response
    mock_response = MagicMock()
    mock_response.json.return_value = {
        "data": [{"embedding": [0.1] * 1024}]
    }
    mock_response.raise_for_status = MagicMock()
    mock_post.return_value = mock_response

    text = "Test video about AI"
    embedding = generate_embedding(text, infinity_url="http://test:7997")

    assert len(embedding) == 1024
    assert all(isinstance(x, float) for x in embedding)

    # Verify API call
    mock_post.assert_called_once()
    call_args = mock_post.call_args
    assert "http://test:7997/embeddings" in call_args[0]
    assert call_args[1]["json"]["model"] == "Alibaba-NLP/gte-large-en-v1.5"
    assert call_args[1]["json"]["input"] == [text]


@pytest.mark.unit
@patch("compose.cli.populate_surrealdb_from_archive.httpx.post")
def test_generate_embedding_api_failure(mock_post):
    """Test embedding generation handles API failures."""
    # Mock API failure
    mock_post.side_effect = Exception("API connection failed")

    with pytest.raises(Exception, match="API connection failed"):
        generate_embedding("Test text", infinity_url="http://test:7997")


@pytest.mark.unit
@pytest.mark.asyncio
@patch("compose.cli.populate_surrealdb_from_archive.generate_embedding")
@patch("compose.cli.populate_surrealdb_from_archive.upsert_video")
async def test_populate_single_video(mock_upsert, mock_generate_embedding, sample_archive_data):
    """Test populating a single video to SurrealDB."""
    # Mock embedding generation
    mock_generate_embedding.return_value = [0.1] * 1024

    # Mock upsert_video
    mock_upsert.return_value = {"created": True}

    # Call populate function
    result = await populate_single_video(
        sample_archive_data,
        month="2025-11",
        infinity_url="http://test:7997",
        dry_run=False,
    )

    assert result is True

    # Verify embedding was generated
    mock_generate_embedding.assert_called_once()

    # Verify upsert_video was called
    mock_upsert.assert_called_once()

    # Check the VideoRecord passed to upsert
    call_args = mock_upsert.call_args[0][0]
    assert isinstance(call_args, VideoRecord)
    assert call_args.video_id == "dQw4w9WgXcQ"
    assert call_args.title == "How to Build AI Agents"
    assert call_args.channel_name == "Tech Channel"
    assert call_args.embedding is not None
    assert len(call_args.embedding) == 1024
    assert call_args.archive_path == "archives/youtube/2025-11/dQw4w9WgXcQ.json"


@pytest.mark.unit
@pytest.mark.asyncio
@patch("compose.cli.populate_surrealdb_from_archive.generate_embedding")
@patch("compose.cli.populate_surrealdb_from_archive.upsert_video")
async def test_populate_single_video_dry_run(mock_upsert, mock_generate_embedding, sample_archive_data):
    """Test dry run doesn't write to database."""
    # Mock embedding generation
    mock_generate_embedding.return_value = [0.1] * 1024

    # Call populate function with dry_run=True
    result = await populate_single_video(
        sample_archive_data,
        month="2025-11",
        infinity_url="http://test:7997",
        dry_run=True,
    )

    assert result is True

    # Verify embedding was still generated (for validation)
    mock_generate_embedding.assert_called_once()

    # Verify upsert_video was NOT called
    mock_upsert.assert_not_called()


@pytest.mark.unit
@pytest.mark.asyncio
@patch("compose.cli.populate_surrealdb_from_archive.generate_embedding")
@patch("compose.cli.populate_surrealdb_from_archive.upsert_video")
async def test_populate_single_video_handles_missing_metadata(mock_upsert, mock_generate_embedding):
    """Test handling archives with minimal metadata."""
    minimal_archive = {
        "video_id": "test123",
        "url": "https://www.youtube.com/watch?v=test123",
        "fetched_at": "2025-11-24T12:00:00",
        "raw_transcript": "Test",
        "youtube_metadata": {},  # Empty metadata
        "llm_outputs": [],
    }

    mock_generate_embedding.return_value = [0.1] * 1024
    mock_upsert.return_value = {"created": True}

    result = await populate_single_video(
        minimal_archive,
        month="2025-11",
        infinity_url="http://test:7997",
        dry_run=False,
    )

    assert result is True

    # Verify upsert was called with None values for missing fields
    call_args = mock_upsert.call_args[0][0]
    assert call_args.title is None
    assert call_args.channel_name is None


@pytest.mark.unit
@pytest.mark.asyncio
@patch("compose.cli.populate_surrealdb_from_archive.generate_embedding")
@patch("compose.cli.populate_surrealdb_from_archive.upsert_video")
async def test_populate_single_video_handles_embedding_failure(mock_upsert, mock_generate_embedding, sample_archive_data):
    """Test handling embedding generation failures."""
    # Mock embedding failure
    mock_generate_embedding.side_effect = Exception("Infinity API failed")

    result = await populate_single_video(
        sample_archive_data,
        month="2025-11",
        infinity_url="http://test:7997",
        dry_run=False,
    )

    assert result is False

    # Verify upsert was not called
    mock_upsert.assert_not_called()


@pytest.mark.unit
@pytest.mark.asyncio
@patch("compose.cli.populate_surrealdb_from_archive.generate_embedding")
@patch("compose.cli.populate_surrealdb_from_archive.upsert_video")
async def test_populate_single_video_handles_upsert_failure(mock_upsert, mock_generate_embedding, sample_archive_data):
    """Test handling SurrealDB upsert failures."""
    mock_generate_embedding.return_value = [0.1] * 1024

    # Mock upsert failure
    mock_upsert.side_effect = Exception("SurrealDB connection failed")

    result = await populate_single_video(
        sample_archive_data,
        month="2025-11",
        infinity_url="http://test:7997",
        dry_run=False,
    )

    assert result is False


@pytest.mark.unit
@pytest.mark.asyncio
@patch("compose.cli.populate_surrealdb_from_archive.generate_embedding")
@patch("compose.cli.populate_surrealdb_from_archive.upsert_video")
async def test_populate_idempotency(mock_upsert, mock_generate_embedding, sample_archive_data):
    """Test that running populate multiple times is idempotent."""
    mock_generate_embedding.return_value = [0.1] * 1024
    mock_upsert.return_value = {"created": True}

    # Run twice
    result1 = await populate_single_video(
        sample_archive_data,
        month="2025-11",
        infinity_url="http://test:7997",
        dry_run=False,
    )

    result2 = await populate_single_video(
        sample_archive_data,
        month="2025-11",
        infinity_url="http://test:7997",
        dry_run=False,
    )

    assert result1 is True
    assert result2 is True

    # upsert_video should be called twice (UPSERT handles duplicates)
    assert mock_upsert.call_count == 2
