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

# Add project root for imports
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

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

        for i, result in enumerate(results, 1):
            video_id = result.get('video_id', 'N/A')
            url = result.get('url', 'N/A')
            score = result.get('_score', 0)
            transcript_len = result.get('transcript_length', 0)
            transcript = result.get('transcript', '')

            # Extract metadata (new structured format or old tags format)
            metadata = result.get('metadata', {})
            if metadata:
                title = metadata.get('title', 'N/A')
                summary = metadata.get('summary', 'N/A')
                subject = ', '.join(metadata.get('subject_matter', [])[:3])
                content_style = metadata.get('content_style', 'N/A')
            else:
                # Fallback to old format
                title = 'N/A'
                summary = result.get('tags', 'N/A')
                subject = 'N/A'
                content_style = 'N/A'

            print(f"{i}. {video_id} (relevance: {score:.3f})")
            print(f"   URL: {url}")
            print(f"   Title: {title}")
            print(f"   Summary: {summary[:100]}..." if len(str(summary)) > 100 else f"   Summary: {summary}")
            print(f"   Subject: {subject}")
            print(f"   Style: {content_style}")
            print(f"   Transcript: {transcript_len:,} characters")
            print()

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
