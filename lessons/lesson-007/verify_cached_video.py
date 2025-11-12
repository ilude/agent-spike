"""Verify a video is cached and search for it."""

import sys
from pathlib import Path

# Bootstrap: Add project root to path so we can import lessons.lesson_base
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from lessons.lesson_base import setup_lesson_environment

setup_lesson_environment()

from tools.services.cache import create_qdrant_cache


def verify_video(video_id: str, collection_name: str = "cached_content"):
    """Check if a video is cached and show its data.

    Args:
        video_id: YouTube video ID
        collection_name: Qdrant collection name
    """
    print(f"\nVerifying video: {video_id}")
    print(f"Collection: {collection_name}\n")

    # Initialize cache
    cache = create_qdrant_cache(collection_name=collection_name)

    # Check by key
    cache_key = f"youtube:video:{video_id}"
    print(f"[1] Checking cache key: {cache_key}")

    if cache.exists(cache_key):
        print("[OK] Video found in cache!")
        data = cache.get(cache_key)
        if data:
            print(f"\n--- Cached Data ---")
            print(f"Video ID: {data.get('video_id')}")
            print(f"URL: {data.get('url')}")
            print(f"Transcript Length: {data.get('transcript_length')} chars")
            print(f"Tags: {data.get('tags')}")
            print(f"\nFirst 500 chars of transcript:")
            print(data.get('transcript', '')[:500])
    else:
        print("[ERROR] Video not found in cache!")
        return

    # Try semantic search
    print(f"\n\n[2] Testing semantic search...")
    results = cache.search("RAG system embeddings", limit=5)

    print(f"\nFound {len(results)} results for 'RAG system embeddings':")
    for i, result in enumerate(results, 1):
        score = result.get('_score', 0)
        vid = result.get('video_id', 'N/A')
        tags = result.get('tags', 'N/A')
        print(f"\n  {i}. Video ID: {vid} (score: {score:.3f})")
        print(f"     Tags: {tags}")


def main():
    """Main entry point."""
    if len(sys.argv) < 2:
        print("Usage: python verify_cached_video.py <video_id> [collection_name]")
        print("\nExample:")
        print("  python verify_cached_video.py MuP9ki6Bdtg")
        print("  python verify_cached_video.py MuP9ki6Bdtg cached_content")
        sys.exit(1)

    video_id = sys.argv[1]
    collection_name = sys.argv[2] if len(sys.argv) > 2 else "cached_content"

    verify_video(video_id, collection_name)


if __name__ == "__main__":
    main()
