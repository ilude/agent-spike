#!/usr/bin/env python
"""Semantic search for cached YouTube videos.

Usage:
    # Search default collection
    uv run python tools/scripts/search_videos.py "machine learning tutorial"

    # Custom collection
    uv run python tools/scripts/search_videos.py "AI agents" --collection my_collection

    # More results
    uv run python tools/scripts/search_videos.py "python coding" --limit 20

    # All options
    uv run python tools/scripts/search_videos.py "MCP protocol" --collection cached_content --limit 10
"""

import argparse
import sys
from pathlib import Path

# Setup script environment
sys.path.insert(0, str(Path(__file__).parent))
from script_base import setup_script_environment
setup_script_environment(load_env=False)

from tools.services.cache import create_qdrant_cache


def search_videos(
    query: str,
    collection_name: str = "cached_content",
    limit: int = 10
):
    """Search for videos using semantic similarity.

    Args:
        query: Search query (e.g., "machine learning tutorial")
        collection_name: Qdrant collection name
        limit: Maximum number of results
    """
    print(f"\n{'='*80}")
    print(f"Semantic Video Search")
    print(f"{'='*80}")
    print(f"Query: '{query}'")
    print(f"Collection: {collection_name}")
    print(f"Limit: {limit}\n")

    # Initialize cache
    cache = create_qdrant_cache(collection_name=collection_name)

    try:
        # Perform semantic search
        print(f"Searching...")
        results = cache.search(query, limit=limit)

        if not results:
            print(f"\n[INFO] No results found for '{query}'\n")
            return

        print(f"\nFound {len(results)} results:\n")
        print(f"{'='*80}\n")

        from tools.services.display import format_video_display

        for i, result in enumerate(results, 1):
            # Show summary if available (not in format_video_display)
            metadata = result.get('metadata', {})
            if summary := metadata.get('summary'):
                summary_preview = f"{summary[:100]}..." if len(summary) > 100 else summary
                print(format_video_display(result, i, show_score=True))
                print(f"   Summary: {summary_preview}\n")
            else:
                print(format_video_display(result, i, show_score=True))

        print(f"{'='*80}\n")

    finally:
        cache.close()


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Semantic search for cached YouTube videos"
    )
    parser.add_argument(
        "query",
        help="Search query string (e.g., 'machine learning tutorial')"
    )
    parser.add_argument(
        "--collection",
        "-c",
        default="cached_content",
        help="Qdrant collection name (default: cached_content)"
    )
    parser.add_argument(
        "--limit",
        "-l",
        type=int,
        default=10,
        help="Maximum number of results (default: 10)"
    )

    try:
        args = parser.parse_args()
        search_videos(args.query, args.collection, args.limit)

    except KeyboardInterrupt:
        print("\n\nKeyboard Interrupt Received... Exiting!")
        sys.exit(0)


if __name__ == "__main__":
    main()
