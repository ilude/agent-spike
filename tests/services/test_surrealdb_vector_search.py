"""Test SurrealDB vector search functionality.

Test coverage:
- Vector similarity search (cosine distance)
- Top-K results with pagination
- Metadata filtering (by channel_name, date range)
- Empty results handling
- Invalid input handling
- Embedding dimension validation
- Text-to-embedding search integration with Infinity
"""

import os
import sys
from datetime import datetime, timedelta

import pytest

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

from compose.lib.env_loader import load_root_env
from compose.services.surrealdb.repository import (
    search_videos_by_embedding,
    search_videos_by_text,
)

# Load environment variables
load_root_env()


@pytest.fixture(autouse=True)
async def reset_db_connection():
    """Reset DB connection between tests to avoid event loop issues."""
    from compose.services.surrealdb.driver import reset_db, close_db

    # Reset before test
    reset_db()
    yield
    # Clean up after test
    await close_db()
    reset_db()


@pytest.fixture
def sample_embedding():
    """Generate a sample 1024-dimensional embedding vector."""
    # Create a simple embedding with some variance
    import random

    random.seed(42)  # Reproducible results
    return [random.random() for _ in range(1024)]


@pytest.fixture
def zero_embedding():
    """Generate a zero vector (edge case)."""
    return [0.0] * 1024


class TestVectorSimilaritySearch:
    """Test vector similarity search with embeddings."""

    @pytest.mark.asyncio
    async def test_basic_search(self, sample_embedding):
        """Test basic vector similarity search returns results."""
        results = await search_videos_by_embedding(
            query_embedding=sample_embedding, limit=5
        )

        assert isinstance(results, list)
        # We have 1,390 videos with embeddings, should get results
        assert len(results) > 0
        assert len(results) <= 5

        # Verify result structure
        for result in results:
            assert "video_id" in result
            assert "title" in result
            assert "url" in result
            assert "score" in result
            assert isinstance(result["score"], (int, float))
            # Score should be between -1 and 1 for cosine similarity
            assert -1.0 <= result["score"] <= 1.0

    @pytest.mark.asyncio
    async def test_top_k_limit(self, sample_embedding):
        """Test that limit parameter controls result count."""
        # Test different limits
        for limit in [1, 5, 10, 20]:
            results = await search_videos_by_embedding(
                query_embedding=sample_embedding, limit=limit
            )
            assert len(results) <= limit

    @pytest.mark.asyncio
    async def test_pagination(self, sample_embedding):
        """Test pagination with offset parameter."""
        # Get first page
        page1 = await search_videos_by_embedding(
            query_embedding=sample_embedding, limit=5, offset=0
        )

        # Get second page
        page2 = await search_videos_by_embedding(
            query_embedding=sample_embedding, limit=5, offset=5
        )

        assert len(page1) > 0
        assert len(page2) > 0

        # Ensure pages don't overlap
        page1_ids = {r["video_id"] for r in page1}
        page2_ids = {r["video_id"] for r in page2}
        assert len(page1_ids.intersection(page2_ids)) == 0

    @pytest.mark.asyncio
    async def test_zero_embedding(self, zero_embedding):
        """Test search with zero vector (edge case)."""
        results = await search_videos_by_embedding(
            query_embedding=zero_embedding, limit=5
        )

        # Should still return results (with low scores)
        assert isinstance(results, list)
        # May or may not have results depending on data
        for result in results:
            assert "score" in result


class TestMetadataFiltering:
    """Test search with metadata filters."""

    @pytest.mark.asyncio
    async def test_channel_filter(self, sample_embedding):
        """Test filtering by channel_name."""
        # First get all results to find a channel
        all_results = await search_videos_by_embedding(
            query_embedding=sample_embedding, limit=50
        )

        # Find a channel name from results
        channels = [r.get("channel_name") for r in all_results if r.get("channel_name")]
        if not channels:
            pytest.skip("No videos with channel_name found")

        test_channel = channels[0]

        # Search with channel filter
        filtered_results = await search_videos_by_embedding(
            query_embedding=sample_embedding, limit=10, channel_filter=test_channel
        )

        assert len(filtered_results) > 0
        # All results should be from the specified channel
        for result in filtered_results:
            assert result.get("channel_name") == test_channel

    @pytest.mark.asyncio
    async def test_date_range_filter(self, sample_embedding):
        """Test filtering by date range."""
        # Search for videos from the last year
        max_date = datetime.now()
        min_date = max_date - timedelta(days=365)

        results = await search_videos_by_embedding(
            query_embedding=sample_embedding,
            limit=10,
            min_date=min_date,
            max_date=max_date,
        )

        assert isinstance(results, list)
        # Verify dates are within range (if created_at is returned)
        for result in results:
            if "created_at" in result:
                created = result["created_at"]
                if isinstance(created, str):
                    created = datetime.fromisoformat(created.replace("Z", "+00:00"))
                assert min_date <= created <= max_date

    @pytest.mark.asyncio
    async def test_combined_filters(self, sample_embedding):
        """Test combining multiple filters."""
        # Get sample data first
        all_results = await search_videos_by_embedding(
            query_embedding=sample_embedding, limit=50
        )

        channels = [r.get("channel_name") for r in all_results if r.get("channel_name")]
        if not channels:
            pytest.skip("No videos with channel_name found")

        test_channel = channels[0]
        max_date = datetime.now()
        min_date = max_date - timedelta(days=730)  # 2 years

        results = await search_videos_by_embedding(
            query_embedding=sample_embedding,
            limit=10,
            channel_filter=test_channel,
            min_date=min_date,
            max_date=max_date,
        )

        # Results should satisfy all filters
        for result in results:
            if result.get("channel_name"):
                assert result["channel_name"] == test_channel


class TestEmptyResults:
    """Test handling of empty result sets."""

    @pytest.mark.asyncio
    async def test_nonexistent_channel(self, sample_embedding):
        """Test search with non-existent channel returns empty."""
        results = await search_videos_by_embedding(
            query_embedding=sample_embedding,
            limit=10,
            channel_filter="ThisChannelDoesNotExist12345",
        )

        assert isinstance(results, list)
        assert len(results) == 0

    @pytest.mark.asyncio
    async def test_future_date_range(self, sample_embedding):
        """Test search with future date range returns empty."""
        future_date = datetime.now() + timedelta(days=365)

        results = await search_videos_by_embedding(
            query_embedding=sample_embedding,
            limit=10,
            min_date=future_date,
        )

        assert isinstance(results, list)
        assert len(results) == 0

    @pytest.mark.asyncio
    async def test_zero_limit(self, sample_embedding):
        """Test search with limit=0 returns empty."""
        results = await search_videos_by_embedding(
            query_embedding=sample_embedding, limit=0
        )

        assert isinstance(results, list)
        assert len(results) == 0


class TestInvalidInput:
    """Test handling of invalid input."""

    @pytest.mark.asyncio
    async def test_wrong_embedding_dimension(self):
        """Test search with wrong embedding dimension."""
        # 512 dimensions instead of 1024
        wrong_dim_embedding = [0.5] * 512

        with pytest.raises(ValueError, match="dimension"):
            await search_videos_by_embedding(
                query_embedding=wrong_dim_embedding, limit=10
            )

    @pytest.mark.asyncio
    async def test_empty_embedding(self):
        """Test search with empty embedding."""
        with pytest.raises(ValueError, match="dimension"):
            await search_videos_by_embedding(query_embedding=[], limit=10)

    @pytest.mark.asyncio
    async def test_negative_limit(self, sample_embedding):
        """Test search with negative limit."""
        with pytest.raises(ValueError, match="limit"):
            await search_videos_by_embedding(
                query_embedding=sample_embedding, limit=-1
            )

    @pytest.mark.asyncio
    async def test_negative_offset(self, sample_embedding):
        """Test search with negative offset."""
        with pytest.raises(ValueError, match="offset"):
            await search_videos_by_embedding(
                query_embedding=sample_embedding, limit=10, offset=-1
            )

    @pytest.mark.asyncio
    async def test_invalid_date_range(self, sample_embedding):
        """Test search where min_date > max_date."""
        min_date = datetime.now()
        max_date = min_date - timedelta(days=30)

        with pytest.raises(ValueError, match="min_date.*max_date"):
            await search_videos_by_embedding(
                query_embedding=sample_embedding,
                limit=10,
                min_date=min_date,
                max_date=max_date,
            )


class TestTextToEmbeddingSearch:
    """Test text-based search (integrates with Infinity API)."""

    @pytest.mark.asyncio
    async def test_text_search(self):
        """Test text-based search generates embedding and searches."""
        results = await search_videos_by_text(
            query_text="machine learning tutorial", limit=5
        )

        assert isinstance(results, list)
        assert len(results) > 0
        assert len(results) <= 5

        for result in results:
            assert "video_id" in result
            assert "title" in result
            assert "score" in result

    @pytest.mark.asyncio
    async def test_text_search_with_channel_filter(self):
        """Test text search with channel filter."""
        # First get a channel name
        all_results = await search_videos_by_text(
            query_text="programming", limit=50
        )

        channels = [r.get("channel_name") for r in all_results if r.get("channel_name")]
        if not channels:
            pytest.skip("No videos with channel_name found")

        test_channel = channels[0]

        # Search with filter
        results = await search_videos_by_text(
            query_text="programming", limit=10, channel_filter=test_channel
        )

        assert len(results) > 0
        for result in results:
            if result.get("channel_name"):
                assert result["channel_name"] == test_channel

    @pytest.mark.asyncio
    async def test_empty_text_search(self):
        """Test search with empty text."""
        with pytest.raises(ValueError, match="query_text"):
            await search_videos_by_text(query_text="", limit=10)

    @pytest.mark.asyncio
    async def test_text_search_pagination(self):
        """Test text search with pagination."""
        page1 = await search_videos_by_text(
            query_text="python programming", limit=5, offset=0
        )

        page2 = await search_videos_by_text(
            query_text="python programming", limit=5, offset=5
        )

        # Should get different results
        if len(page1) > 0 and len(page2) > 0:
            page1_ids = {r["video_id"] for r in page1}
            page2_ids = {r["video_id"] for r in page2}
            assert len(page1_ids.intersection(page2_ids)) == 0


class TestScoreOrdering:
    """Test that results are properly ordered by similarity score."""

    @pytest.mark.asyncio
    async def test_results_ordered_by_score(self, sample_embedding):
        """Test that results are in descending order by score."""
        results = await search_videos_by_embedding(
            query_embedding=sample_embedding, limit=10
        )

        if len(results) > 1:
            scores = [r["score"] for r in results]
            # Check descending order
            for i in range(len(scores) - 1):
                assert scores[i] >= scores[i + 1], "Scores should be in descending order"

    @pytest.mark.asyncio
    async def test_text_results_ordered_by_score(self):
        """Test that text search results are in descending order."""
        results = await search_videos_by_text(
            query_text="artificial intelligence", limit=10
        )

        if len(results) > 1:
            scores = [r["score"] for r in results]
            for i in range(len(scores) - 1):
                assert scores[i] >= scores[i + 1], "Scores should be in descending order"


if __name__ == "__main__":
    # Run tests with pytest
    pytest.main([__file__, "-v", "--tb=short"])
