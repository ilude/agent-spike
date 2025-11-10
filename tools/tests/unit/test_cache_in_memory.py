"""Tests for InMemoryCache implementation.

Run with: uv run pytest tools/tests/unit/test_cache_in_memory.py
"""

import pytest
from tools.services.cache import InMemoryCache, create_in_memory_cache


@pytest.mark.unit
def test_in_memory_basic_operations():
    """Test basic cache operations: get, set, exists, delete."""
    cache = InMemoryCache()

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


@pytest.mark.unit
def test_in_memory_count_and_clear():
    """Test count and clear operations."""
    cache = InMemoryCache()

    # Add items
    for i in range(5):
        cache.set(f"item{i}", {"index": i})

    # Test count
    assert cache.count() == 5, "Should have 5 items"

    # Test clear
    cache.clear()
    assert cache.count() == 0, "Should have 0 items after clear"


@pytest.mark.unit
def test_in_memory_text_search():
    """Test simple text search (not semantic)."""
    cache = InMemoryCache()

    # Add test documents
    cache.set(
        "doc1",
        {"text": "How to build multi-agent AI systems"},
        {"type": "article"}
    )
    cache.set(
        "doc2",
        {"text": "Introduction to machine learning"},
        {"type": "article"}
    )
    cache.set(
        "doc3",
        {"text": "Python web development guide"},
        {"type": "article"}
    )

    # Search for "agent"
    results = cache.search("agent", limit=10)
    assert len(results) == 1, "Should find 1 result"
    assert "agent" in results[0]["text"].lower()

    # Search for "python"
    results = cache.search("python", limit=10)
    assert len(results) == 1, "Should find 1 result"
    assert "Python" in results[0]["text"]


@pytest.mark.unit
def test_in_memory_metadata_filtering():
    """Test metadata filtering."""
    cache = InMemoryCache()

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


@pytest.mark.unit
def test_factory_function():
    """Test factory function creates working cache."""
    cache = create_in_memory_cache()

    cache.set("test", {"data": "value"})
    result = cache.get("test")

    assert result is not None
    assert result["data"] == "value"
