"""Test suite for lesson-007: Cache Manager and Qdrant Cache.

Run this file to verify the cache implementation works correctly.

Usage:
    python test_cache.py
"""

import sys
from pathlib import Path

# Add parent dirs to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from tools.services.cache import create_qdrant_cache
from rich.console import Console

console = Console()


def test_basic_operations():
    """Test basic cache operations: get, set, exists, delete."""
    console.print("\n[bold cyan]Test 1: Basic Operations[/bold cyan]")

    # Initialize cache
    cache = create_qdrant_cache(collection_name="test_basic")

    # Clear cache to start fresh
    console.print("Clearing cache...")
    cache.clear()

    # Test set
    console.print("Testing set()...")
    cache.set(
        "test:key1",
        {"data": "Hello, World!", "number": 42},
        metadata={"type": "test", "category": "greeting"}
    )
    console.print("✓ Set operation successful")

    # Test exists
    console.print("Testing exists()...")
    assert cache.exists("test:key1"), "Key should exist"
    assert not cache.exists("test:nonexistent"), "Key should not exist"
    console.print("✓ Exists check successful")

    # Test get
    console.print("Testing get()...")
    result = cache.get("test:key1")
    assert result is not None, "Should retrieve data"
    assert result["data"] == "Hello, World!", "Data should match"
    assert result["number"] == 42, "Number should match"
    console.print(f"✓ Get operation successful: {result}")

    # Test delete
    console.print("Testing delete()...")
    success = cache.delete("test:key1")
    assert success, "Delete should succeed"
    assert not cache.exists("test:key1"), "Key should not exist after delete"
    console.print("✓ Delete operation successful")

    console.print("[green]✓ All basic operations passed![/green]\n")


def test_semantic_search():
    """Test semantic search capabilities."""
    console.print("\n[bold cyan]Test 2: Semantic Search[/bold cyan]")

    cache = create_qdrant_cache(collection_name="test_search")
    cache.clear()

    # Add test documents
    console.print("Adding test documents...")
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

    console.print(f"✓ Added {len(docs)} documents")

    # Test semantic search
    console.print("\nTesting semantic search: 'agent orchestration'...")
    results = cache.search("agent orchestration", limit=3)

    assert len(results) > 0, "Should find results"
    console.print(f"✓ Found {len(results)} results:")

    for i, result in enumerate(results, 1):
        console.print(f"  {i}. Score: {result['_score']:.3f} - {result['text'][:50]}...")

    # First result should be about agents (semantic match)
    assert "agent" in results[0]["text"].lower(), "Top result should be about agents"

    console.print("[green]✓ Semantic search passed![/green]\n")


def test_metadata_filtering():
    """Test metadata filtering."""
    console.print("\n[bold cyan]Test 3: Metadata Filtering[/bold cyan]")

    cache = create_qdrant_cache(collection_name="test_filter")
    cache.clear()

    # Add documents with different types
    console.print("Adding documents with metadata...")
    cache.set("youtube1", {"title": "AI Tutorial"}, {"type": "youtube", "year": "2024"})
    cache.set("youtube2", {"title": "Python Guide"}, {"type": "youtube", "year": "2023"})
    cache.set("webpage1", {"title": "AI Blog"}, {"type": "webpage", "year": "2024"})

    console.print("✓ Added 3 documents")

    # Filter by type
    console.print("\nFiltering by type='youtube'...")
    youtube_results = cache.filter({"type": "youtube"}, limit=10)
    assert len(youtube_results) == 2, "Should find 2 YouTube items"
    console.print(f"✓ Found {len(youtube_results)} YouTube items")

    # Filter by year
    console.print("\nFiltering by year='2024'...")
    year_results = cache.filter({"year": "2024"}, limit=10)
    assert len(year_results) == 2, "Should find 2 items from 2024"
    console.print(f"✓ Found {len(year_results)} items from 2024")

    console.print("[green]✓ Metadata filtering passed![/green]\n")


def test_with_lesson_tools():
    """Test integration with lesson-001 and lesson-002 tools."""
    console.print("\n[bold cyan]Test 4: Integration with Lesson Tools[/bold cyan]")

    try:
        from lessons.lesson001.youtube_agent.tools import get_video_info, extract_video_id
    except ImportError:
        console.print("[yellow]⚠ Skipping lesson tools test (lessons not in path)[/yellow]\n")
        return

    cache = create_qdrant_cache(collection_name="test_integration")

    # Test with a real YouTube URL
    test_url = "https://www.youtube.com/watch?v=i5kwX7jeWL8"

    console.print(f"Testing with YouTube URL: {test_url}")

    # First call - should fetch (or use cache if already there)
    console.print("First call (may fetch or use cache)...")
    info1 = get_video_info(test_url, cache=cache)
    assert "video_id" in info1, "Should have video_id"
    console.print(f"✓ Video ID: {info1['video_id']}")

    # Second call - should definitely use cache
    console.print("Second call (should use cache)...")
    video_id = extract_video_id(test_url)
    cache_key = f"youtube:info:{video_id}"
    cached_before = cache.exists(cache_key)

    info2 = get_video_info(test_url, cache=cache)

    assert info1 == info2, "Results should be identical"
    console.print("✓ Results match (cache working)")

    console.print("[green]✓ Integration with lesson tools passed![/green]\n")


def main():
    """Run all tests."""
    console.print("[bold]Running Lesson-007 Cache Tests[/bold]")
    console.print("=" * 50)

    try:
        test_basic_operations()
        test_semantic_search()
        test_metadata_filtering()
        test_with_lesson_tools()

        console.print("\n[bold green]✅ All Tests Passed![/bold green]")
        return 0

    except AssertionError as e:
        console.print(f"\n[bold red]❌ Test Failed: {e}[/bold red]")
        return 1

    except Exception as e:
        console.print(f"\n[bold red]❌ Error: {e}[/bold red]")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
