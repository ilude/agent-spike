"""Demo script for SurrealDB vector search functionality.

Shows:
1. Text-based semantic search
2. Vector similarity search with filters
3. Pagination through results
"""

import asyncio
import sys

# Fix Windows encoding
if sys.platform == "win32":
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

from compose.lib.env_loader import load_root_env
from compose.services.surrealdb.repository import (
    search_videos_by_text,
    search_videos_by_embedding,
    get_video_count,
)

# Load environment
load_root_env()


async def demo_text_search():
    """Demo text-based search."""
    print("\n" + "=" * 60)
    print("TEXT-BASED SEMANTIC SEARCH")
    print("=" * 60)

    query = "machine learning tutorial"
    print(f"\nQuery: '{query}'")
    print("\nTop 5 results:")
    print("-" * 60)

    results = await search_videos_by_text(query_text=query, limit=5)

    for i, result in enumerate(results, 1):
        print(f"\n{i}. {result.get('title', 'No title')}")
        print(f"   Channel: {result.get('channel_name', 'Unknown')}")
        print(f"   Score: {result.get('score', 0):.4f}")
        print(f"   URL: {result.get('url', '')}")


async def demo_channel_filter():
    """Demo search with channel filter."""
    print("\n\n" + "=" * 60)
    print("SEARCH WITH CHANNEL FILTER")
    print("=" * 60)

    # First get a popular channel
    all_results = await search_videos_by_text("python", limit=50)
    channels = [r.get("channel_name") for r in all_results if r.get("channel_name")]

    if not channels:
        print("\nNo channels found in results")
        return

    channel = channels[0]
    print(f"\nFiltering by channel: {channel}")
    print("\nResults:")
    print("-" * 60)

    results = await search_videos_by_text(
        query_text="programming",
        limit=3,
        channel_filter=channel,
    )

    for i, result in enumerate(results, 1):
        print(f"\n{i}. {result.get('title', 'No title')}")
        print(f"   Score: {result.get('score', 0):.4f}")


async def demo_pagination():
    """Demo pagination through results."""
    print("\n\n" + "=" * 60)
    print("PAGINATION DEMO")
    print("=" * 60)

    query = "artificial intelligence"
    print(f"\nQuery: '{query}'")

    # Get first page
    print("\n--- Page 1 (results 1-3) ---")
    page1 = await search_videos_by_text(query_text=query, limit=3, offset=0)
    for i, result in enumerate(page1, 1):
        print(f"{i}. {result.get('title', 'No title')[:50]}...")

    # Get second page
    print("\n--- Page 2 (results 4-6) ---")
    page2 = await search_videos_by_text(query_text=query, limit=3, offset=3)
    for i, result in enumerate(page2, 4):
        print(f"{i}. {result.get('title', 'No title')[:50]}...")


async def demo_stats():
    """Show database stats."""
    print("\n\n" + "=" * 60)
    print("DATABASE STATISTICS")
    print("=" * 60)

    total_videos = await get_video_count()
    print(f"\nTotal videos in database: {total_videos:,}")


async def main():
    """Run all demos."""
    print("\n")
    print("╔" + "=" * 58 + "╗")
    print("║" + " " * 10 + "SurrealDB Vector Search Demo" + " " * 20 + "║")
    print("╚" + "=" * 58 + "╝")

    try:
        await demo_stats()
        await demo_text_search()
        await demo_channel_filter()
        await demo_pagination()

        print("\n\n" + "=" * 60)
        print("Demo completed successfully!")
        print("=" * 60 + "\n")

    except Exception as e:
        print(f"\n\nError: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())
