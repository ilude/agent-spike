#!/usr/bin/env python
"""Semantic search for cached YouTube videos.

Usage:
    # Search default collection
    uv run python tools/scripts/search_videos.py "machine learning tutorial"

    # Custom collection
    uv run python tools/scripts/search_videos.py "AI agents" my_collection

    # More results
    uv run python tools/scripts/search_videos.py "python coding" cached_content 20
"""

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
            tags = result.get('tags', 'N/A')
            transcript_len = result.get('transcript_length', 0)
            transcript = result.get('transcript', '')

            print(f"{i}. {video_id} (relevance: {score:.3f})")
            print(f"   URL: {url}")
            print(f"   Tags: {tags}")
            print(f"   Transcript: {transcript_len:,} characters")

            # Show snippet from transcript
            if transcript:
                # Try to find query term in transcript for context
                query_lower = query.lower()
                transcript_lower = transcript.lower()
                idx = transcript_lower.find(query_lower)

                if idx >= 0:
                    # Show context around query
                    start = max(0, idx - 100)
                    end = min(len(transcript), idx + len(query) + 100)
                    snippet = transcript[start:end]
                    if start > 0:
                        snippet = "..." + snippet
                    if end < len(transcript):
                        snippet = snippet + "..."
                    print(f"   Context: {snippet}")
                else:
                    # Just show beginning
                    snippet = transcript[:200]
                    if len(transcript) > 200:
                        snippet += "..."
                    print(f"   Snippet: {snippet}")

            print()

        print(f"{'='*80}\n")

    finally:
        cache.close()


def main():
    """Main entry point."""
    try:
        if len(sys.argv) < 2:
            print("Error: Search query required")
            print()
            print("Usage:")
            print("  uv run python tools/scripts/search_videos.py <query> [collection] [limit]")
            print()
            print("Examples:")
            print("  uv run python tools/scripts/search_videos.py 'machine learning'")
            print("  uv run python tools/scripts/search_videos.py 'AI agents' my_collection")
            print("  uv run python tools/scripts/search_videos.py 'python' cached_content 20")
            sys.exit(1)

        query = sys.argv[1]
        collection_name = sys.argv[2] if len(sys.argv) > 2 else "cached_content"
        limit = int(sys.argv[3]) if len(sys.argv) > 3 else 10

        search_videos(query, collection_name, limit)

    except KeyboardInterrupt:
        print("\n\nKeyboard Interrupt Received... Exiting!")
        sys.exit(0)
    except ValueError:
        print("Error: Limit must be a number")
        sys.exit(1)


if __name__ == "__main__":
    main()
