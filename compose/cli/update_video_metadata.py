#!/usr/bin/env python
"""Update YouTube metadata for existing archives.

This script fetches YouTube Data API metadata for videos that already have transcripts
but are missing metadata. This is more efficient than re-ingesting entire videos.

Usage:
    # Update single video
    uv run python tools/scripts/update_video_metadata.py VIDEO_ID

    # Update all archives missing metadata
    uv run python tools/scripts/update_video_metadata.py --all

    # Dry run (show what would be updated)
    uv run python tools/scripts/update_video_metadata.py --all --dry-run
"""

import sys
from pathlib import Path

# Setup script environment
sys.path.insert(0, str(Path(__file__).parent))
from compose.cli.base import setup_script_environment
setup_script_environment()

from compose.services.archive import create_archive_manager
from compose.services.youtube import fetch_video_metadata


def safe_print(text: str, **kwargs) -> None:
    """Print text with unicode encoding error handling for Windows console.

    Args:
        text: Text to print (may contain unicode characters)
        **kwargs: Additional arguments to pass to print()
    """
    try:
        print(text, **kwargs)
    except UnicodeEncodeError:
        # Replace problematic characters with safe representation
        safe_text = text.encode('ascii', errors='replace').decode('ascii')
        print(safe_text, **kwargs)


def update_single_video_metadata(
    video_id: str,
    archive_manager,
    dry_run: bool = False,
    force: bool = False,
) -> dict:
    """Update YouTube metadata for a single video.

    Args:
        video_id: YouTube video ID
        archive_manager: ArchiveManager instance
        dry_run: If True, don't update archive
        force: If True, update even if metadata exists

    Returns:
        Dict with processing results
    """
    # Get archive
    archive = archive_manager.get(video_id)
    if not archive:
        return {
            "success": False,
            "message": f"Archive not found for video_id: {video_id}",
        }

    # Check if metadata already exists
    has_metadata = bool(archive.youtube_metadata and
                       archive.youtube_metadata.get("title"))

    if has_metadata and not force:
        return {
            "success": False,
            "message": f"Metadata already exists for {video_id} (use --force to update)",
        }

    print(f"\nUpdating metadata for: {video_id}")
    print(f"URL: {archive.url}")

    # Fetch metadata
    print("Fetching YouTube metadata...")
    youtube_metadata, error = fetch_video_metadata(video_id)

    if error:
        return {
            "success": False,
            "message": f"Metadata fetch failed: {error}",
        }

    print(f"  [OK] Fetched metadata:")
    safe_print(f"      Title: {youtube_metadata.get('title', 'N/A')}")
    print(f"      Duration: {youtube_metadata.get('duration', 'N/A')}")
    print(f"      Views: {youtube_metadata.get('view_count', 0):,}")
    safe_print(f"      Channel: {youtube_metadata.get('channel_title', 'N/A')}")

    if dry_run:
        print(f"\n[DRY RUN] Archive NOT updated")
        return {
            "success": True,
            "video_id": video_id,
            "metadata": youtube_metadata,
            "dry_run": True,
        }

    # Update archive
    print("Updating archive...")
    archive_manager.update_metadata(
        video_id=video_id,
        url=archive.url,
        metadata=youtube_metadata,
    )
    print(f"  [OK] Archive updated")

    return {
        "success": True,
        "video_id": video_id,
        "metadata": youtube_metadata,
    }


def update_all_video_metadata(
    archive_manager,
    dry_run: bool = False,
    force: bool = False,
) -> dict:
    """Update YouTube metadata for all archives missing metadata.

    Args:
        archive_manager: ArchiveManager instance
        dry_run: If True, don't update archives
        force: If True, update even if metadata exists

    Returns:
        Dict with batch processing results
    """
    # Get all archive files
    youtube_dir = archive_manager.writer.youtube_dir

    # Find all JSON files
    archive_files = []
    if archive_manager.writer.config.organize_by_month:
        # Search in month directories
        for month_dir in youtube_dir.iterdir():
            if month_dir.is_dir():
                archive_files.extend(month_dir.glob("*.json"))
    else:
        # Search in flat structure
        archive_files = list(youtube_dir.glob("*.json"))

    print(f"Found {len(archive_files)} archives to check\n")

    # Process each video
    total_stats = {
        "processed": 0,
        "skipped": 0,
        "errors": 0,
        "already_has_metadata": 0,
    }

    for archive_file in archive_files:
        video_id = archive_file.stem

        try:
            result = update_single_video_metadata(
                video_id,
                archive_manager,
                dry_run,
                force,
            )

            if result["success"]:
                total_stats["processed"] += 1
            else:
                if "already exists" in result["message"]:
                    total_stats["already_has_metadata"] += 1
                else:
                    total_stats["skipped"] += 1
                print(f"  [SKIP] {result['message']}")

        except Exception as e:
            total_stats["errors"] += 1
            print(f"  [ERROR] {video_id}: {e}")

        print("-" * 70)

    # Print summary
    print(f"\n{'='*70}")
    print(f"Batch Metadata Update Summary")
    print(f"{'='*70}")
    print(f"Total archives: {len(archive_files)}")
    print(f"Updated: {total_stats['processed']}")
    print(f"Already had metadata: {total_stats['already_has_metadata']}")
    print(f"Skipped: {total_stats['skipped']}")
    print(f"Errors: {total_stats['errors']}")
    print(f"{'='*70}\n")

    return total_stats


def main():
    """Main entry point."""
    import argparse

    parser = argparse.ArgumentParser(
        description="Update YouTube metadata for existing archives"
    )
    parser.add_argument(
        "video_id",
        nargs="?",
        help="YouTube video ID to update (omit for --all)",
    )
    parser.add_argument(
        "--all",
        action="store_true",
        help="Update all archives missing metadata",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be updated without modifying archives",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Update metadata even if it already exists",
    )

    args = parser.parse_args()

    # Validate arguments
    if not args.video_id and not args.all:
        parser.print_help()
        print("\nError: Provide either VIDEO_ID or --all")
        sys.exit(1)

    if args.video_id and args.all:
        print("Error: Cannot specify both VIDEO_ID and --all")
        sys.exit(1)

    # Initialize archive manager
    archive_manager = create_archive_manager()

    try:
        if args.all:
            # Update all videos
            print(f"{'='*70}")
            print(f"Batch Metadata Update")
            print(f"{'='*70}")
            print(f"Mode: {'Force update all' if args.force else 'Update missing only'}")
            print(f"Dry run: {args.dry_run}")
            print(f"{'='*70}\n")

            stats = update_all_video_metadata(
                archive_manager,
                args.dry_run,
                args.force,
            )

            if stats["errors"] > 0:
                sys.exit(1)
        else:
            # Update single video
            print(f"{'='*70}")
            print(f"Single Video Metadata Update")
            print(f"{'='*70}")
            print(f"Video ID: {args.video_id}")
            print(f"Force: {args.force}")
            print(f"Dry run: {args.dry_run}")
            print(f"{'='*70}")

            result = update_single_video_metadata(
                args.video_id,
                archive_manager,
                args.dry_run,
                args.force,
            )

            if not result["success"]:
                print(f"\n[ERROR] {result['message']}")
                sys.exit(1)

            print(f"\n{'='*70}")
            print(f"SUCCESS!")
            print(f"{'='*70}\n")

    except KeyboardInterrupt:
        print("\n\nInterrupted by user")
        sys.exit(0)
    except Exception as e:
        import traceback
        traceback.print_exc()
        print(f"\n[ERROR] {type(e).__name__}: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
