"""Tests for QdrantCache implementation.

Run with: uv run pytest tools/tests/unit/test_cache_qdrant.py
"""

import pytest
from pathlib import Path

# Import directly from modules to avoid lazy-loading issues in tests
from tools.services.cache.config import CacheConfig

try:
    from tools.services.cache.qdrant_cache import QdrantCache
    from tools.services.cache.factory import create_qdrant_cache
    QDRANT_AVAILABLE = True
except ImportError:
    QDRANT_AVAILABLE = False
    pytestmark = pytest.mark.skip("qdrant-client not installed")


@pytest.mark.unit
def test_qdrant_basic_operations(temp_dir):
    """Test basic cache operations: get, set, exists, delete."""
    config = CacheConfig(
        cache_dir=temp_dir / "qdrant",
        collection_name="test_basic",
    )
    cache = QdrantCache(config)

    try:
        # Clear cache to start fresh
        cache.clear()

        # Test set
        cache.set(
            "test:key1",
            {"data": "Hello, World!", "number": 42},
            metadata={"type": "test", "category": "greeting"}
        )

        # Test exists
        assert cache.exists("test:key1"), "Key should exist"
        assert not cache.exists("test:nonexistent"), "Key should not exist"

        # Test get
        result = cache.get("test:key1")
        assert result is not None, "Should retrieve data"
        assert result["data"] == "Hello, World!", "Data should match"
        assert result["number"] == 42, "Number should match"

        # Test delete
        success = cache.delete("test:key1")
        assert success, "Delete should succeed"
        assert not cache.exists("test:key1"), "Key should not exist after delete"
    finally:
        cache.close()


@pytest.mark.unit
def test_qdrant_semantic_search(temp_dir):
    """Test semantic search capabilities."""
    config = CacheConfig(
        cache_dir=temp_dir / "qdrant",
        collection_name="test_search",
    )
    cache = QdrantCache(config)

    try:
        cache.clear()

        # Add test documents
        docs = [
            {
                "key": "doc1",
                "value": {"text": "How to build multi-agent AI systems with Python"},
                "metadata": {"type": "article", "topic": "ai"}
            },
            {
                "key": "doc2",
                "value": {"text": "Introduction to machine learning algorithms"},
                "metadata": {"type": "article", "topic": "ml"}
            },
            {
                "key": "doc3",
                "value": {"text": "Coordinating multiple AI agents in production"},
                "metadata": {"type": "article", "topic": "ai"}
            },
            {
                "key": "doc4",
                "value": {"text": "Best practices for Python web development"},
                "metadata": {"type": "article", "topic": "web"}
            },
        ]

        for doc in docs:
            cache.set(doc["key"], doc["value"], doc["metadata"])

        # Test semantic search
        results = cache.search("agent orchestration", limit=3)

        assert len(results) > 0, "Should find results"

        # First result should be about agents (semantic match)
        assert "agent" in results[0]["text"].lower(), "Top result should be about agents"
    finally:
        cache.close()


@pytest.mark.unit
def test_qdrant_metadata_filtering(temp_dir):
    """Test metadata filtering."""
    config = CacheConfig(
        cache_dir=temp_dir / "qdrant",
        collection_name="test_filter",
    )
    cache = QdrantCache(config)

    try:
        cache.clear()

        # Add documents with different types
        cache.set("youtube1", {"title": "AI Tutorial"}, {"type": "youtube", "year": "2024"})
        cache.set("youtube2", {"title": "Python Guide"}, {"type": "youtube", "year": "2023"})
        cache.set("webpage1", {"title": "AI Blog"}, {"type": "webpage", "year": "2024"})

        # Filter by type
        youtube_results = cache.filter({"type": "youtube"}, limit=10)
        assert len(youtube_results) == 2, "Should find 2 YouTube items"

        # Filter by year
        year_results = cache.filter({"year": "2024"}, limit=10)
        assert len(year_results) == 2, "Should find 2 items from 2024"
    finally:
        cache.close()


@pytest.mark.unit
def test_qdrant_count_and_clear(temp_dir):
    """Test count and clear operations."""
    config = CacheConfig(
        cache_dir=temp_dir / "qdrant",
        collection_name="test_count",
    )
    cache = QdrantCache(config)

    try:
        cache.clear()

        # Add items
        for i in range(5):
            cache.set(f"item{i}", {"index": i})

        # Test count
        assert cache.count() == 5, "Should have 5 items"

        # Test clear - close and reopen to ensure clean state
        cache.clear()
        cache.close()

        # Reopen to verify clear worked
        cache2 = QdrantCache(config)
        try:
            assert cache2.count() == 0, "Should have 0 items after clear"
        finally:
            cache2.close()
    finally:
        if hasattr(cache, 'client'):
            cache.close()


@pytest.mark.unit
def test_factory_function(temp_dir):
    """Test factory function creates working cache."""
    cache = create_qdrant_cache(
        cache_dir=temp_dir / "qdrant",
        collection_name="test_factory"
    )

    try:
        cache.set("test", {"data": "value"})
        result = cache.get("test")

        assert result is not None
        assert result["data"] == "value"
    finally:
        cache.close()


@pytest.mark.unit
def test_searchable_text_extraction(temp_dir):
    """Test that cache extracts text for embedding correctly."""
    config = CacheConfig(
        cache_dir=temp_dir / "qdrant",
        collection_name="test_extraction",
    )
    cache = QdrantCache(config)

    try:
        cache.clear()

        # Test with different text fields
        cache.set("doc1", {"transcript": "This is a transcript"})
        cache.set("doc2", {"markdown": "This is markdown content"})
        cache.set("doc3", {"content": "This is generic content"})
        cache.set("doc4", {"title": "Just a Title", "data": 123})

        # Search should work for all of them
        results = cache.search("content", limit=10)
        assert len(results) >= 2, "Should find content-related items"
    finally:
        cache.close()
