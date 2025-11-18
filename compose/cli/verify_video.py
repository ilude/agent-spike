#!/usr/bin/env python
"""Verify a video is cached and show its data.

Usage:
    # Check if video is cached
    uv run python tools/scripts/verify_video.py dQw4w9WgXcQ

    # Custom collection
    uv run python tools/scripts/verify_video.py dQw4w9WgXcQ my_collection
"""

import sys
from pathlib import Path

# Setup script environment
sys.path.insert(0, str(Path(__file__).parent))
from compose.cli.base import setup_script_environment
setup_script_environment(load_env=False)

from compose.services.cache import create_qdrant_cache


def verify_video(video_id: str, collection_name: str = "cached_content"):
    """Check if a video is cached and show its data.

    Args:
        video_id: YouTube video ID
        collection_name: Qdrant collection name
    """
    print(f"\n{'='*80}")
    print(f"Video Verification: {video_id}")
    print(f"{'='*80}")
    print(f"Collection: {collection_name}\n")

    # Initialize cache
    cache = create_qdrant_cache(collection_name=collection_name)

    try:
        # Check by key
        cache_key = f"youtube:video:{video_id}"
        print(f"[1/2] Checking cache key: {cache_key}")

        if not cache.exists(cache_key):
            print(f"  [NOT FOUND] Video not in cache\n")
            print(f"To ingest this video:")
            print(f"  uv run python tools/scripts/ingest_video.py 'https://youtube.com/watch?v={video_id}'\n")
            return False

        print(f"  [OK] Video found in cache!\n")

        # Get data
        data = cache.get(cache_key)
        if not data:
            print(f"  [ERROR] Could not retrieve cache data\n")
            return False

        # Display data
        print(f"{'='*80}")
        print(f"Cached Data")
        print(f"{'='*80}")
        print(f"Video ID: {data.get('video_id', 'N/A')}")
        print(f"URL: {data.get('url', 'N/A')}")
        print(f"Transcript Length: {data.get('transcript_length', 0):,} characters")
        print(f"Tags: {data.get('tags', 'N/A')}")
        print()

        transcript = data.get('transcript', '')
        if transcript:
            print(f"First 500 characters of transcript:")
            print(f"{'-'*80}")
            print(transcript[:500])
            if len(transcript) > 500:
                print("...")
            print(f"{'-'*80}\n")

        # Try semantic search with tags
        print(f"[2/2] Testing semantic search with tags...")
        tags = data.get('tags', '')
        if tags:
            # Use first tag for search
            first_tag = tags.split(',')[0].strip() if ',' in tags else tags.strip()
            results = cache.search(first_tag, limit=5)
            print(f"  Found {len(results)} videos similar to '{first_tag}':")
            for i, result in enumerate(results[:5], 1):
                vid_id = result.get('video_id', 'N/A')
                score = result.get('_score', 0)
                result_tags = result.get('tags', 'N/A')[:50]
                print(f"    {i}. {vid_id} (score: {score:.3f}) - {result_tags}")
            print()

        print(f"{'='*80}\n")
        return True

    finally:
        cache.close()


def main():
    """Main entry point."""
    try:
        if len(sys.argv) < 2:
            print("Error: Video ID required")
            print()
            print("Usage:")
            print("  uv run python tools/scripts/verify_video.py <video_id> [collection_name]")
            print()
            print("Examples:")
            print("  uv run python tools/scripts/verify_video.py dQw4w9WgXcQ")
            print("  uv run python tools/scripts/verify_video.py dQw4w9WgXcQ my_collection")
            sys.exit(1)

        video_id = sys.argv[1]
        collection_name = sys.argv[2] if len(sys.argv) > 2 else "cached_content"

        verify_video(video_id, collection_name)

    except KeyboardInterrupt:
        print("\n\nKeyboard Interrupt Received... Exiting!")
        sys.exit(0)


if __name__ == "__main__":
    main()
