#!/usr/bin/env python
"""Delete a video from cache.

Usage:
    python delete_video.py <video_id> [--yes]
    python delete_video.py --help
"""
import argparse
import sys
from pathlib import Path

# Setup script environment
sys.path.insert(0, str(Path(__file__).parent))
from compose.cli.base import setup_script_environment
setup_script_environment(load_env=False)

from compose.services.cache import create_qdrant_cache


def main():
    """Delete a cached video with confirmation."""
    parser = argparse.ArgumentParser(
        description="Delete a cached YouTube video from Qdrant",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Delete with confirmation prompt
  python delete_video.py abc123xyz

  # Delete without confirmation (dangerous!)
  python delete_video.py abc123xyz --yes
        """
    )
    parser.add_argument(
        "video_id",
        help="YouTube video ID to delete"
    )
    parser.add_argument(
        "--collection", "-c",
        default="cached_content",
        help="Qdrant collection name (default: cached_content)"
    )
    parser.add_argument(
        "--yes", "-y",
        action="store_true",
        help="Skip confirmation prompt (use with caution)"
    )

    args = parser.parse_args()

    video_id = args.video_id
    cache_key = f"youtube:video:{video_id}"

    # Confirmation prompt (unless --yes flag)
    if not args.yes:
        response = input(f"Delete video '{video_id}' from collection '{args.collection}'? (y/N): ")
        if response.lower() not in ['y', 'yes']:
            print("Deletion cancelled.")
            return 0

    # Perform deletion
    cache = create_qdrant_cache(collection_name=args.collection)
    try:
        result = cache.delete(cache_key)
        if result:
            print(f"✓ Deleted {cache_key} from {args.collection}")
        else:
            print(f"✗ Video {video_id} not found in {args.collection}")
            return 1
    finally:
        cache.close()

    return 0


if __name__ == "__main__":
    sys.exit(main())
