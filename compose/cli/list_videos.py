#!/usr/bin/env python
"""List all YouTube videos in SurrealDB.

Usage:
    # Default (first 100)
    uv run python compose/cli/list_videos.py

    # Limit results
    uv run python compose/cli/list_videos.py --limit 20

    # With offset for pagination
    uv run python compose/cli/list_videos.py --limit 20 --offset 100
"""

import argparse
import asyncio
import sys
from pathlib import Path

# Setup script environment
sys.path.insert(0, str(Path(__file__).parent))
from compose.cli.base import setup_script_environment
setup_script_environment(load_env=True)

from compose.services.surrealdb.repository import get_all_videos, get_video_count


async def list_videos(limit: int = 100, offset: int = 0):
    """List all videos in SurrealDB.

    Args:
        limit: Maximum number of videos to show
        offset: Number of videos to skip (for pagination)
    """
    print(f"\n{'='*80}")
    print(f"Videos in SurrealDB")
    print(f"{'='*80}\n")

    # Get total count
    total = await get_video_count()
    print(f"Total videos: {total}")
    print(f"Showing: {offset + 1} to {min(offset + limit, total)}\n")

    # Get videos
    videos = await get_all_videos(limit=limit, offset=offset)

    if not videos:
        print("[INFO] No videos found.\n")
        return

    print(f"{'='*80}\n")

    for i, video in enumerate(videos, offset + 1):
        title = (video.title or "Unknown")[:60]
        channel = video.channel_name or "Unknown"
        video_id = video.video_id

        print(f"[{i}] {title}")
        print(f"    ID: {video_id}")
        print(f"    Channel: {channel}")
        print(f"    URL: https://youtube.com/watch?v={video_id}")
        if video.view_count:
            print(f"    Views: {video.view_count:,}")
        print()

    print(f"{'='*80}")
    print(f"Showing {len(videos)} of {total} videos")
    if offset + limit < total:
        print(f"Next page: --offset {offset + limit}")
    print(f"{'='*80}\n")


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="List all YouTube videos in SurrealDB"
    )
    parser.add_argument(
        "--limit",
        "-l",
        type=int,
        default=100,
        help="Maximum number of videos to show (default: 100)"
    )
    parser.add_argument(
        "--offset",
        "-o",
        type=int,
        default=0,
        help="Number of videos to skip (default: 0)"
    )

    try:
        args = parser.parse_args()
        asyncio.run(list_videos(args.limit, args.offset))

    except KeyboardInterrupt:
        print("\n\nKeyboard Interrupt Received... Exiting!")
        sys.exit(0)


if __name__ == "__main__":
    main()
