#!/usr/bin/env python
"""List all cached YouTube videos in the Qdrant collection.

Usage:
    # Default collection
    uv run python tools/scripts/list_videos.py

    # Custom collection
    uv run python tools/scripts/list_videos.py --collection my_collection

    # Limit results
    uv run python tools/scripts/list_videos.py --limit 20

    # Both
    uv run python tools/scripts/list_videos.py --collection cached_content --limit 20
"""

import argparse
import sys
from pathlib import Path

# Setup script environment
sys.path.insert(0, str(Path(__file__).parent))
from compose.cli.base import setup_script_environment
setup_script_environment(load_env=False)

from compose.services.cache import create_qdrant_cache


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

        from compose.services.display import format_video_display

        for i, video in enumerate(videos[:limit], 1):
            print(format_video_display(video, i, show_score=False))

        print(f"{'='*80}\n")

    finally:
        cache.close()


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="List all cached YouTube videos in the Qdrant collection"
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
        default=100,
        help="Maximum number of videos to show (default: 100)"
    )

    try:
        args = parser.parse_args()
        list_videos(args.collection, args.limit)

    except KeyboardInterrupt:
        print("\n\nKeyboard Interrupt Received... Exiting!")
        sys.exit(0)


if __name__ == "__main__":
    main()
