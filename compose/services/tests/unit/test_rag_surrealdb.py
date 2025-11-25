"""Tests for SurrealDB-based RAG service.

Run with: uv run pytest compose/services/tests/unit/test_rag_surrealdb.py
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch


# Test fixtures
@pytest.fixture
def mock_search_results():
    """Mock SurrealDB search results."""
    return [
        {
            "video_id": "abc123",
            "title": "Introduction to AI Agents",
            "channel_name": "AI Explained",
            "url": "https://youtube.com/watch?v=abc123",
            "score": 0.92,
            "archive_path": "compose/data/archive/youtube/2025-11/abc123.json",
        },
        {
            "video_id": "def456",
            "title": "Building Multi-Agent Systems",
            "channel_name": "Tech Tutorial",
            "url": "https://youtube.com/watch?v=def456",
            "score": 0.88,
            "archive_path": "compose/data/archive/youtube/2025-11/def456.json",
        },
    ]


@pytest.fixture
def mock_transcript():
    """Mock transcript content."""
    return """This is a sample transcript about AI agents.
We'll discuss how to build and coordinate multiple agents.
Key concepts include agent communication and task delegation."""


# =============================================================================
# Context Retrieval Tests
# =============================================================================


@pytest.mark.asyncio
@pytest.mark.unit
class TestContextRetrieval:
    """Test RAG context retrieval from SurrealDB."""

    async def test_retrieve_context_basic_query(self, mock_search_results):
        """Retrieve context for a basic text query."""
        from compose.services.rag.surrealdb_rag import SurrealDBRAG

        with patch(
            "compose.services.rag.surrealdb_rag.search_videos_by_text"
        ) as mock_search:
            mock_search.return_value = mock_search_results

            rag = SurrealDBRAG()
            results = await rag.retrieve_context(
                query="What are AI agents?", limit=5
            )

            # Verify search was called
            mock_search.assert_called_once()
            call_args = mock_search.call_args
            assert call_args[1]["query_text"] == "What are AI agents?"
            assert call_args[1]["limit"] == 5

            # Verify results
            assert len(results) == 2
            assert results[0]["video_id"] == "abc123"
            assert results[0]["title"] == "Introduction to AI Agents"
            assert results[0]["score"] == 0.92

    async def test_retrieve_context_with_channel_filter(self, mock_search_results):
        """Retrieve context with channel filtering."""
        from compose.services.rag.surrealdb_rag import SurrealDBRAG

        with patch(
            "compose.services.rag.surrealdb_rag.search_videos_by_text"
        ) as mock_search:
            mock_search.return_value = mock_search_results

            rag = SurrealDBRAG()
            await rag.retrieve_context(
                query="AI agents", limit=10, channel_filter="AI Explained"
            )

            # Verify channel filter passed to search
            mock_search.assert_called_once()
            call_args = mock_search.call_args
            assert call_args[1]["channel_filter"] == "AI Explained"

    async def test_retrieve_context_empty_results(self):
        """Handle empty search results gracefully."""
        from compose.services.rag.surrealdb_rag import SurrealDBRAG

        with patch(
            "compose.services.rag.surrealdb_rag.search_videos_by_text"
        ) as mock_search:
            mock_search.return_value = []

            rag = SurrealDBRAG()
            results = await rag.retrieve_context(query="nonexistent query")

            assert results == []

    async def test_retrieve_context_with_min_score_threshold(self, mock_search_results):
        """Filter results by minimum score threshold."""
        from compose.services.rag.surrealdb_rag import SurrealDBRAG

        with patch(
            "compose.services.rag.surrealdb_rag.search_videos_by_text"
        ) as mock_search:
            mock_search.return_value = mock_search_results

            rag = SurrealDBRAG(min_score=0.90)
            results = await rag.retrieve_context(query="AI agents")

            # Should filter out results with score < 0.90
            assert len(results) == 1
            assert results[0]["score"] >= 0.90
            assert results[0]["video_id"] == "abc123"


# =============================================================================
# Context Formatting Tests
# =============================================================================


@pytest.mark.asyncio
@pytest.mark.unit
class TestContextFormatting:
    """Test formatting of retrieved context for LLM prompts."""

    async def test_format_context_basic(self, mock_search_results, mock_transcript):
        """Format basic context with video metadata."""
        from compose.services.rag.surrealdb_rag import SurrealDBRAG

        with patch(
            "compose.services.rag.surrealdb_rag.search_videos_by_text"
        ) as mock_search, patch(
            "compose.services.rag.surrealdb_rag.get_transcript_from_minio"
        ) as mock_transcript_fn:
            mock_search.return_value = mock_search_results[:1]
            mock_transcript_fn.return_value = mock_transcript

            rag = SurrealDBRAG()
            context = await rag.format_context_for_llm(query="AI agents")

            # Verify structure
            assert "Introduction to AI Agents" in context
            assert "AI Explained" in context
            assert "sample transcript about AI agents" in context
            assert "0.92" in context or "92%" in context  # Score formatting

    async def test_format_context_multiple_videos(
        self, mock_search_results, mock_transcript
    ):
        """Format context with multiple video sources."""
        from compose.services.rag.surrealdb_rag import SurrealDBRAG

        with patch(
            "compose.services.rag.surrealdb_rag.search_videos_by_text"
        ) as mock_search, patch(
            "compose.services.rag.surrealdb_rag.get_transcript_from_minio"
        ) as mock_transcript_fn:
            mock_search.return_value = mock_search_results
            mock_transcript_fn.return_value = mock_transcript

            rag = SurrealDBRAG()
            context = await rag.format_context_for_llm(query="AI agents")

            # Verify all videos included
            assert "Introduction to AI Agents" in context
            assert "Building Multi-Agent Systems" in context
            assert "AI Explained" in context
            assert "Tech Tutorial" in context

    async def test_format_context_missing_transcript(self, mock_search_results):
        """Handle missing transcripts gracefully."""
        from compose.services.rag.surrealdb_rag import SurrealDBRAG

        with patch(
            "compose.services.rag.surrealdb_rag.search_videos_by_text"
        ) as mock_search, patch(
            "compose.services.rag.surrealdb_rag.get_transcript_from_minio"
        ) as mock_transcript_fn:
            mock_search.return_value = mock_search_results[:1]
            mock_transcript_fn.return_value = None

            rag = SurrealDBRAG()
            context = await rag.format_context_for_llm(query="AI agents")

            # Should still include video metadata
            assert "Introduction to AI Agents" in context
            # Should indicate transcript unavailable
            assert "not available" in context.lower() or "unavailable" in context.lower()

    async def test_format_context_transcript_truncation(
        self, mock_search_results
    ):
        """Truncate long transcripts to fit context window."""
        from compose.services.rag.surrealdb_rag import SurrealDBRAG

        long_transcript = "word " * 5000  # Very long transcript
        truncated_transcript = long_transcript[:1000] + "\n\n[... transcript truncated ...]"

        with patch(
            "compose.services.rag.surrealdb_rag.search_videos_by_text"
        ) as mock_search, patch(
            "compose.services.rag.surrealdb_rag.get_transcript_from_minio"
        ) as mock_transcript_fn:
            mock_search.return_value = mock_search_results[:1]
            # Mock the function to actually truncate like the real one does
            mock_transcript_fn.return_value = truncated_transcript

            rag = SurrealDBRAG(max_transcript_chars=1000)
            context = await rag.format_context_for_llm(query="AI agents")

            # Context should be reasonable length
            # (Max chars per video + metadata overhead)
            assert len(context) < 2000
            assert "truncated" in context

    async def test_format_context_empty_results(self):
        """Format context when no results found."""
        from compose.services.rag.surrealdb_rag import SurrealDBRAG

        with patch(
            "compose.services.rag.surrealdb_rag.search_videos_by_text"
        ) as mock_search:
            mock_search.return_value = []

            rag = SurrealDBRAG()
            context = await rag.format_context_for_llm(query="nonexistent")

            # Should return empty or minimal context
            assert context == "" or "no relevant" in context.lower()


# =============================================================================
# Result Limiting and Thresholds
# =============================================================================


@pytest.mark.asyncio
@pytest.mark.unit
class TestResultLimitingAndThresholds:
    """Test result limiting and score thresholds."""

    async def test_default_limit(self, mock_search_results):
        """Use default result limit."""
        from compose.services.rag.surrealdb_rag import SurrealDBRAG

        with patch(
            "compose.services.rag.surrealdb_rag.search_videos_by_text"
        ) as mock_search:
            mock_search.return_value = mock_search_results

            rag = SurrealDBRAG()
            await rag.retrieve_context(query="test")

            # Verify default limit used
            call_args = mock_search.call_args
            assert call_args[1]["limit"] == 5

    async def test_custom_limit(self, mock_search_results):
        """Use custom result limit."""
        from compose.services.rag.surrealdb_rag import SurrealDBRAG

        with patch(
            "compose.services.rag.surrealdb_rag.search_videos_by_text"
        ) as mock_search:
            mock_search.return_value = mock_search_results

            rag = SurrealDBRAG(default_limit=10)
            await rag.retrieve_context(query="test")

            call_args = mock_search.call_args
            assert call_args[1]["limit"] == 10

    async def test_min_score_threshold(self):
        """Filter results below minimum score threshold."""
        from compose.services.rag.surrealdb_rag import SurrealDBRAG

        results_with_varying_scores = [
            {"video_id": "a", "score": 0.95, "title": "High", "url": "url1"},
            {"video_id": "b", "score": 0.75, "title": "Medium", "url": "url2"},
            {"video_id": "c", "score": 0.45, "title": "Low", "url": "url3"},
        ]

        with patch(
            "compose.services.rag.surrealdb_rag.search_videos_by_text"
        ) as mock_search:
            mock_search.return_value = results_with_varying_scores

            rag = SurrealDBRAG(min_score=0.70)
            results = await rag.retrieve_context(query="test")

            # Only results >= 0.70
            assert len(results) == 2
            assert all(r["score"] >= 0.70 for r in results)

    async def test_zero_min_score_returns_all(self, mock_search_results):
        """Min score of 0.0 returns all results."""
        from compose.services.rag.surrealdb_rag import SurrealDBRAG

        with patch(
            "compose.services.rag.surrealdb_rag.search_videos_by_text"
        ) as mock_search:
            mock_search.return_value = mock_search_results

            rag = SurrealDBRAG(min_score=0.0)
            results = await rag.retrieve_context(query="test")

            assert len(results) == len(mock_search_results)


# =============================================================================
# Error Handling Tests
# =============================================================================


@pytest.mark.asyncio
@pytest.mark.unit
class TestErrorHandling:
    """Test error handling for service failures."""

    async def test_search_service_unavailable(self):
        """Handle SurrealDB service unavailable."""
        from compose.services.rag.surrealdb_rag import SurrealDBRAG

        with patch(
            "compose.services.rag.surrealdb_rag.search_videos_by_text"
        ) as mock_search:
            mock_search.side_effect = ConnectionError("SurrealDB unavailable")

            rag = SurrealDBRAG()

            with pytest.raises(ConnectionError):
                await rag.retrieve_context(query="test")

    async def test_infinity_service_unavailable(self):
        """Handle Infinity embedding service unavailable."""
        from compose.services.rag.surrealdb_rag import SurrealDBRAG

        with patch(
            "compose.services.rag.surrealdb_rag.search_videos_by_text"
        ) as mock_search:
            mock_search.side_effect = Exception("Failed to generate embedding")

            rag = SurrealDBRAG()

            with pytest.raises(Exception) as exc_info:
                await rag.retrieve_context(query="test")
            assert "embedding" in str(exc_info.value).lower()

    async def test_minio_unavailable_partial_results(
        self, mock_search_results, mock_transcript
    ):
        """Continue with partial results when MinIO unavailable."""
        from compose.services.rag.surrealdb_rag import SurrealDBRAG

        with patch(
            "compose.services.rag.surrealdb_rag.search_videos_by_text"
        ) as mock_search, patch(
            "compose.services.rag.surrealdb_rag.get_transcript_from_minio"
        ) as mock_transcript_fn:
            mock_search.return_value = mock_search_results
            # First call succeeds, second returns None (error logged)
            mock_transcript_fn.side_effect = [mock_transcript, None]

            rag = SurrealDBRAG()
            context = await rag.format_context_for_llm(query="test")

            # Should still include first video with transcript
            assert "Introduction to AI Agents" in context
            # Should handle second video gracefully (no transcript)
            assert "Building Multi-Agent Systems" in context
            # Second video should have unavailable message
            assert context.count("not available") >= 1

    async def test_invalid_query_empty_string(self):
        """Reject empty query strings."""
        from compose.services.rag.surrealdb_rag import SurrealDBRAG

        rag = SurrealDBRAG()

        with pytest.raises(ValueError) as exc_info:
            await rag.retrieve_context(query="")
        assert "empty" in str(exc_info.value).lower()

    async def test_invalid_limit_negative(self):
        """Reject negative limit values."""
        from compose.services.rag.surrealdb_rag import SurrealDBRAG

        rag = SurrealDBRAG()

        with pytest.raises(ValueError) as exc_info:
            await rag.retrieve_context(query="test", limit=-1)
        assert "limit" in str(exc_info.value).lower()


# =============================================================================
# Integration-Style Tests (with mocked dependencies)
# =============================================================================


@pytest.mark.asyncio
@pytest.mark.unit
class TestRAGIntegration:
    """Test end-to-end RAG flow with mocked dependencies."""

    async def test_full_rag_flow(self, mock_search_results, mock_transcript):
        """Test complete RAG flow: retrieve -> format -> return."""
        from compose.services.rag.surrealdb_rag import SurrealDBRAG

        with patch(
            "compose.services.rag.surrealdb_rag.search_videos_by_text"
        ) as mock_search, patch(
            "compose.services.rag.surrealdb_rag.get_transcript_from_minio"
        ) as mock_transcript_fn:
            mock_search.return_value = mock_search_results
            mock_transcript_fn.return_value = mock_transcript

            rag = SurrealDBRAG()

            # Use get_context_and_sources convenience method
            context, sources = await rag.get_context_and_sources(
                query="How to build AI agents?", limit=5
            )

            # Verify context
            assert len(context) > 0
            assert "ai agents" in context.lower()

            # Verify sources
            assert len(sources) == 2
            assert sources[0]["video_id"] == "abc123"
            assert sources[1]["video_id"] == "def456"

    async def test_get_sources_from_results(self, mock_search_results):
        """Extract source citations from results."""
        from compose.services.rag.surrealdb_rag import SurrealDBRAG

        with patch(
            "compose.services.rag.surrealdb_rag.search_videos_by_text"
        ) as mock_search:
            mock_search.return_value = mock_search_results

            rag = SurrealDBRAG()
            results = await rag.retrieve_context(query="test")
            sources = rag.extract_sources(results)

            assert len(sources) == 2
            assert sources[0]["video_id"] == "abc123"
            assert sources[0]["title"] == "Introduction to AI Agents"
            assert sources[0]["url"] == "https://youtube.com/watch?v=abc123"

    async def test_no_qdrant_imports(self):
        """Verify no Qdrant imports in RAG service."""
        import inspect
        import compose.services.rag.surrealdb_rag as rag_module

        source = inspect.getsource(rag_module)
        # Convert to lowercase for case-insensitive search
        source_lower = source.lower()

        # Check for Qdrant imports or references
        assert "import qdrant" not in source_lower
        assert "from qdrant" not in source_lower
        assert "qdrant_cache" not in source_lower
        assert "qdrantcache" not in source_lower
