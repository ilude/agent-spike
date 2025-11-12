"""List all cached YouTube videos in the Qdrant collection."""

import sys
from pathlib import Path

# Bootstrap: Add project root to path so we can import lessons.lesson_base
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from lessons.lesson_base import setup_lesson_environment

setup_lesson_environment()

from tools.services.cache import create_qdrant_cache


def list_videos(collection_name: str = "cached_content"):
    """List all cached YouTube videos.

    Args:
        collection_name: Qdrant collection name
    """
    print(f"\nListing all videos in collection: {collection_name}\n")
    print("=" * 80)

    # Initialize cache
    cache = create_qdrant_cache(collection_name=collection_name)

    # Get all videos by filtering on type
    videos = cache.filter({"type": "youtube_video"}, limit=100)

    if not videos:
        print("[INFO] No videos found in cache.")
        return

    print(f"Found {len(videos)} cached videos:\n")

    for i, video in enumerate(videos, 1):
        video_id = video.get('video_id', 'N/A')
        url = video.get('url', 'N/A')
        transcript_len = video.get('transcript_length', 0)
        tags = video.get('tags', 'N/A')

        print(f"{i}. Video ID: {video_id}")
        print(f"   URL: {url}")
        print(f"   Transcript: {transcript_len:,} characters")
        print(f"   Tags: {tags}")
        print()


def main():
    """Main entry point."""
    collection_name = sys.argv[1] if len(sys.argv) > 1 else "cached_content"
    list_videos(collection_name)


if __name__ == "__main__":
    main()
