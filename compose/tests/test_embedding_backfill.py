"""Tests for embedding backfill worker functions."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch


class TestTimestampFormatting:
    """Tests for timestamp formatting helper."""

    def test_format_seconds_only(self):
        """Format time under 1 minute."""
        from compose.api.routers.cache import _format_timestamp

        assert _format_timestamp(45) == "0:45"
        assert _format_timestamp(5) == "0:05"
        assert _format_timestamp(0) == "0:00"

    def test_format_minutes_seconds(self):
        """Format time under 1 hour."""
        from compose.api.routers.cache import _format_timestamp

        assert _format_timestamp(65) == "1:05"
        assert _format_timestamp(600) == "10:00"
        assert _format_timestamp(3599) == "59:59"

    def test_format_hours(self):
        """Format time 1 hour or more."""
        from compose.api.routers.cache import _format_timestamp

        assert _format_timestamp(3600) == "1:00:00"
        assert _format_timestamp(3665) == "1:01:05"
        assert _format_timestamp(7200) == "2:00:00"
        assert _format_timestamp(36000) == "10:00:00"


class TestBackfillQueries:
    """Tests for backfill query functions."""

    @pytest.mark.asyncio
    async def test_get_videos_needing_chunks_query(self):
        """Verify query structure for videos needing chunks."""
        with patch("compose.worker.embedding_backfill.execute_query") as mock_query:
            mock_query.return_value = [
                {"video_id": "abc123", "title": "Test Video", "archive_path": "/path"}
            ]

            from compose.worker.embedding_backfill import get_videos_needing_chunks

            result = await get_videos_needing_chunks(limit=10)

            # Verify query was called
            mock_query.assert_called_once()
            query = mock_query.call_args[0][0]

            # Verify query structure
            assert "FROM video" in query
            assert "archive_path IS NOT NONE" in query
            assert "pipeline_state['chunk_transcript'] IS NONE" in query
            assert "LIMIT 10" in query

            assert len(result) == 1
            assert result[0]["video_id"] == "abc123"

    @pytest.mark.asyncio
    async def test_get_videos_needing_embeddings_query(self):
        """Verify query structure for videos needing embeddings."""
        with patch("compose.worker.embedding_backfill.execute_query") as mock_query:
            mock_query.return_value = []

            from compose.worker.embedding_backfill import get_videos_needing_embeddings

            await get_videos_needing_embeddings(limit=50)

            query = mock_query.call_args[0][0]

            assert "pipeline_state['chunk_transcript'] IS NOT NONE" in query
            assert "pipeline_state['embed_chunks'] IS NONE" in query
            assert "LIMIT 50" in query

    @pytest.mark.asyncio
    async def test_update_pipeline_state(self):
        """Verify pipeline state update query."""
        with patch("compose.worker.embedding_backfill.execute_query") as mock_query:
            mock_query.return_value = []

            from compose.worker.embedding_backfill import update_pipeline_state

            await update_pipeline_state("video123", "chunk_transcript", "v1.0")

            query = mock_query.call_args[0][0]
            params = mock_query.call_args[0][1]

            assert "UPDATE" in query
            assert "pipeline_state[$step]" in query
            assert params["video_id"] == "video123"
            assert params["step"] == "chunk_transcript"
            assert params["version"] == "v1.0"


class TestProcessChunkVideo:
    """Tests for video chunking process."""

    @pytest.mark.asyncio
    async def test_archive_not_found(self):
        """Return failure if archive doesn't exist."""
        mock_minio = MagicMock()
        mock_minio.exists.return_value = False

        from compose.worker.embedding_backfill import process_chunk_video

        success, msg, count = await process_chunk_video("video123", mock_minio)

        assert success is False
        assert "Archive not found" in msg
        assert count == 0
        mock_minio.exists.assert_called_with("youtube:video:video123")

    @pytest.mark.asyncio
    async def test_no_timed_transcript(self):
        """Return failure if archive has no timed_transcript."""
        mock_minio = MagicMock()
        mock_minio.exists.return_value = True
        mock_minio.get_json.return_value = {"transcript": "text only"}

        from compose.worker.embedding_backfill import process_chunk_video

        success, msg, count = await process_chunk_video("video123", mock_minio)

        assert success is False
        assert "No timed_transcript" in msg
        assert count == 0


class TestChunkSearchModels:
    """Tests for chunk search API models."""

    def test_chunk_search_result_model(self):
        """Verify ChunkSearchResult model structure."""
        from compose.api.models import ChunkSearchResult

        result = ChunkSearchResult(
            chunk_id="video123:0",
            video_id="video123",
            chunk_index=0,
            text="Sample chunk text",
            start_time=0.0,
            end_time=30.5,
            timestamp_range="0:00 - 0:30",
            score=0.95,
            video_title="Test Video",
            video_url="https://youtube.com/watch?v=video123",
        )

        assert result.chunk_id == "video123:0"
        assert result.start_time == 0.0
        assert result.score == 0.95

    def test_chunk_search_response_model(self):
        """Verify ChunkSearchResponse model structure."""
        from compose.api.models import ChunkSearchResponse, ChunkSearchResult

        response = ChunkSearchResponse(
            query="test query",
            results=[
                ChunkSearchResult(
                    chunk_id="v1:0",
                    video_id="v1",
                    chunk_index=0,
                    text="text",
                    start_time=0,
                    end_time=10,
                    timestamp_range="0:00 - 0:10",
                    score=0.9,
                )
            ],
            total_found=1,
        )

        assert response.query == "test query"
        assert len(response.results) == 1
        assert response.total_found == 1
