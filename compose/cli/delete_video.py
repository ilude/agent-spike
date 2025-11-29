#!/usr/bin/env python
"""Delete a video from SurrealDB.

Usage:
    uv run python compose/cli/delete_video.py <video_id> [--yes]
    uv run python compose/cli/delete_video.py --help
"""
import argparse
import asyncio
import sys
from pathlib import Path

# Setup script environment
sys.path.insert(0, str(Path(__file__).parent))
from compose.cli.base import setup_script_environment
setup_script_environment(load_env=True)

from compose.services.surrealdb.repository import delete_video, get_video


async def main():
    """Delete a video with confirmation."""
    parser = argparse.ArgumentParser(
        description="Delete a YouTube video from SurrealDB",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Delete with confirmation prompt
  uv run python compose/cli/delete_video.py abc123xyz

  # Delete without confirmation (dangerous!)
  uv run python compose/cli/delete_video.py abc123xyz --yes
        """
    )
    parser.add_argument(
        "video_id",
        help="YouTube video ID to delete"
    )
    parser.add_argument(
        "--yes", "-y",
        action="store_true",
        help="Skip confirmation prompt (use with caution)"
    )

    args = parser.parse_args()
    video_id = args.video_id

    # Check if video exists first
    video = await get_video(video_id)
    if not video:
        print(f"✗ Video '{video_id}' not found in SurrealDB")
        return 1

    # Show what will be deleted
    print(f"\nVideo to delete:")
    print(f"  ID: {video.video_id}")
    print(f"  Title: {video.title or 'Unknown'}")
    print(f"  Channel: {video.channel_name or 'Unknown'}")
    print(f"  Archive: {video.archive_path or 'N/A'}")
    print()

    # Confirmation prompt (unless --yes flag)
    if not args.yes:
        response = input(f"Delete video '{video_id}'? (y/N): ")
        if response.lower() not in ['y', 'yes']:
            print("Deletion cancelled.")
            return 0

    # Perform deletion
    result = await delete_video(video_id)
    if result:
        print(f"✓ Deleted video '{video_id}' from SurrealDB")
        print(f"  Note: Archive file at '{video.archive_path}' was NOT deleted")
    else:
        print(f"✗ Failed to delete video '{video_id}'")
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
