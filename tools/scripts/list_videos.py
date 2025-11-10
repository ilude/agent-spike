#!/usr/bin/env python
"""List all cached YouTube videos in the Qdrant collection.

Usage:
    # Default collection
    uv run python tools/scripts/list_videos.py

    # Custom collection
    uv run python tools/scripts/list_videos.py my_collection

    # Limit results
    uv run python tools/scripts/list_videos.py cached_content 20
"""

import sys
from pathlib import Path

# Add project root for imports
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from tools.services.cache import create_qdrant_cache


def list_videos(collection_name: str = "cached_content", limit: int = 100):
    """List all cached YouTube videos.

    Args:
        collection_name: Qdrant collection name
        limit: Maximum number of videos to show
    """
    print(f"\n{'='*80}")
    print(f"Cached Videos: {collection_name}")
    print(f"{'='*80}\n")

    # Initialize cache
    cache = create_qdrant_cache(collection_name=collection_name)

    try:
        # Get all videos by filtering on type
        videos = cache.filter({"type": "youtube_video"}, limit=limit)

        if not videos:
            print("[INFO] No videos found in cache.")
            print()
            return

        print(f"Found {len(videos)} cached videos (showing first {min(len(videos), limit)}):\n")

        for i, video in enumerate(videos[:limit], 1):
            video_id = video.get('video_id', 'N/A')
            url = video.get('url', 'N/A')
            transcript_len = video.get('transcript_length', 0)
            tags = video.get('tags', 'N/A')

            print(f"{i}. {video_id}")
            print(f"   URL: {url}")
            print(f"   Transcript: {transcript_len:,} characters")
            print(f"   Tags: {tags}")
            print()

        print(f"{'='*80}\n")

    finally:
        cache.close()


def main():
    """Main entry point."""
    try:
        collection_name = sys.argv[1] if len(sys.argv) > 1 else "cached_content"
        limit = int(sys.argv[2]) if len(sys.argv) > 2 else 100

        list_videos(collection_name, limit)

    except KeyboardInterrupt:
        print("\n\nKeyboard Interrupt Received... Exiting!")
        sys.exit(0)
    except ValueError:
        print("Error: Limit must be a number")
        sys.exit(1)


if __name__ == "__main__":
    main()
