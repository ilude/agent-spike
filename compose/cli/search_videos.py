#!/usr/bin/env python
"""Semantic search for YouTube videos in SurrealDB.

Usage:
    # Basic search
    uv run python compose/cli/search_videos.py "machine learning tutorial"

    # More results
    uv run python compose/cli/search_videos.py "AI agents" --limit 20

    # Filter by channel
    uv run python compose/cli/search_videos.py "python coding" --channel "3Blue1Brown"
"""

import argparse
import asyncio
import sys
from pathlib import Path

# Setup script environment
sys.path.insert(0, str(Path(__file__).parent))
from compose.cli.base import setup_script_environment
setup_script_environment(load_env=True)

from compose.services.surrealdb.repository import search_videos_by_text


async def search_videos(
    query: str,
    limit: int = 10,
    channel: str | None = None,
):
    """Search for videos using semantic similarity.

    Args:
        query: Search query (e.g., "machine learning tutorial")
        limit: Maximum number of results
        channel: Filter by channel name (optional)
    """
    print(f"\n{'='*80}")
    print(f"Semantic Video Search (SurrealDB)")
    print(f"{'='*80}")
    print(f"Query: '{query}'")
    print(f"Limit: {limit}")
    if channel:
        print(f"Channel filter: {channel}")
    print()

    # Perform semantic search
    print(f"Searching...")
    try:
        results = await search_videos_by_text(
            query_text=query,
            limit=limit,
            channel_filter=channel,
        )
    except Exception as e:
        print(f"\n[ERROR] Search failed: {e}")
        print("Make sure Infinity embedding service is running.")
        return

    if not results:
        print(f"\n[INFO] No results found for '{query}'\n")
        return

    print(f"\nFound {len(results)} results:\n")
    print(f"{'='*80}\n")

    for i, result in enumerate(results, 1):
        video_id = result.get("video_id", "unknown")
        title = (result.get("title") or "Unknown")[:60]
        channel_name = result.get("channel_name") or "Unknown"
        score = result.get("score", 0.0)

        print(f"[{i}] {title}")
        print(f"    Score: {score:.4f}")
        print(f"    ID: {video_id}")
        print(f"    Channel: {channel_name}")
        print(f"    URL: https://youtube.com/watch?v={video_id}")
        print()

    print(f"{'='*80}\n")


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Semantic search for YouTube videos in SurrealDB"
    )
    parser.add_argument(
        "query",
        help="Search query string (e.g., 'machine learning tutorial')"
    )
    parser.add_argument(
        "--limit",
        "-l",
        type=int,
        default=10,
        help="Maximum number of results (default: 10)"
    )
    parser.add_argument(
        "--channel",
        "-c",
        default=None,
        help="Filter by channel name (optional)"
    )

    try:
        args = parser.parse_args()
        asyncio.run(search_videos(args.query, args.limit, args.channel))

    except KeyboardInterrupt:
        print("\n\nKeyboard Interrupt Received... Exiting!")
        sys.exit(0)


if __name__ == "__main__":
    main()
