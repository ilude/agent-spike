#!/usr/bin/env python
"""Add retroactive import metadata to existing archives and Qdrant cache.

This script updates existing data with import metadata for recommendation weighting.

Classification rules:
- Videos from nate_jones_videos_12mo.csv → bulk_channel (weight: 0.5)
- All other videos → single_import (weight: 1.0)

Usage:
    # Dry run (show what would be updated)
    uv run python tools/scripts/add_retroactive_metadata.py --dry-run

    # Actually update archives and cache
    uv run python tools/scripts/add_retroactive_metadata.py

    # Update only archives (skip Qdrant)
    uv run python tools/scripts/add_retroactive_metadata.py --skip-qdrant

    # Update only Qdrant (skip archives)
    uv run python tools/scripts/add_retroactive_metadata.py --skip-archives
"""

import csv
import json
import sys
from pathlib import Path
from datetime import datetime
from typing import Set

# Setup script environment
sys.path.insert(0, str(Path(__file__).parent))
from script_base import setup_script_environment
project_root = setup_script_environment()

from tools.services.archive import create_local_archive_writer, ImportMetadata, ChannelContext
from tools.services.cache import create_qdrant_cache
from tools.services.youtube import extract_video_id


def load_bulk_channel_video_ids(csv_path: Path) -> Set[str]:
    """Load video IDs from bulk channel CSV.

    Args:
        csv_path: Path to nate_jones_videos_12mo.csv

    Returns:
        Set of video IDs from bulk channel import
    """
    video_ids = set()

    if not csv_path.exists():
        print(f"[WARN] CSV not found: {csv_path}")
        return video_ids

    with open(csv_path, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            # Try video_id column first, fall back to extracting from URL
            video_id = row.get('video_id', '').strip()
            if not video_id:
                url = row.get('url', '').strip()
                if url:
                    try:
                        video_id = extract_video_id(url)
                    except:
                        continue

            if video_id:
                video_ids.add(video_id)

    return video_ids


def update_archives(
    archive_writer,
    bulk_channel_ids: Set[str],
    dry_run: bool = False,
) -> dict:
    """Update all archives with import metadata.

    Args:
        archive_writer: Archive service
        bulk_channel_ids: Set of video IDs from bulk channel import
        dry_run: If True, only show what would be updated

    Returns:
        Dict with stats: {updated, skipped, errors}
    """
    stats = {"updated": 0, "skipped": 0, "errors": 0}

    print("\n" + "=" * 70)
    print("Updating Archives")
    print("=" * 70)

    # Get all archive files
    youtube_dir = archive_writer.youtube_dir

    # Search all month directories
    archive_files = []
    if archive_writer.config.organize_by_month:
        for month_dir in youtube_dir.iterdir():
            if not month_dir.is_dir():
                continue
            archive_files.extend(month_dir.glob("*.json"))
    else:
        archive_files.extend(youtube_dir.glob("*.json"))

    total = len(archive_files)
    print(f"Found {total} archive files\n")

    for i, archive_path in enumerate(archive_files, 1):
        video_id = archive_path.stem

        try:
            # Read existing archive
            with open(archive_path, 'r', encoding='utf-8') as f:
                data = json.load(f)

            # Check if already has import_metadata
            if data.get('import_metadata'):
                print(f"[{i}/{total}] {video_id} - SKIP (already has metadata)")
                stats["skipped"] += 1
                continue

            # Determine source type
            if video_id in bulk_channel_ids:
                source_type = "bulk_channel"
                weight = 0.5
            else:
                source_type = "single_import"
                weight = 1.0

            print(f"[{i}/{total}] {video_id} - {source_type} (weight: {weight})")

            if dry_run:
                stats["updated"] += 1
                continue

            # Create import metadata
            import_metadata = ImportMetadata(
                source_type=source_type,
                imported_at=datetime.fromisoformat(data['fetched_at']),
                import_method="cli",
                channel_context=ChannelContext(
                    is_bulk_import=(source_type == "bulk_channel"),
                ),
                recommendation_weight=weight,
            )

            # Add to archive data
            data['import_metadata'] = import_metadata.model_dump(mode='json')

            # Write back
            with open(archive_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, default=str)

            stats["updated"] += 1

        except Exception as e:
            print(f"[{i}/{total}] {video_id} - ERROR: {e}")
            stats["errors"] += 1

    print(f"\n{'=' * 70}")
    print(f"Archive Stats")
    print(f"{'=' * 70}")
    print(f"Updated: {stats['updated']}")
    print(f"Skipped: {stats['skipped']}")
    print(f"Errors: {stats['errors']}")
    print(f"{'=' * 70}\n")

    return stats


def update_qdrant_cache(
    collection_name: str,
    bulk_channel_ids: Set[str],
    dry_run: bool = False,
) -> dict:
    """Update all Qdrant points with import metadata.

    Args:
        collection_name: Qdrant collection name
        bulk_channel_ids: Set of video IDs from bulk channel import
        dry_run: If True, only show what would be updated

    Returns:
        Dict with stats: {updated, skipped, errors}
    """
    stats = {"updated": 0, "skipped": 0, "errors": 0}

    print("\n" + "=" * 70)
    print("Updating Qdrant Cache")
    print("=" * 70)

    cache = create_qdrant_cache(collection_name=collection_name)

    try:
        # Get all YouTube videos
        videos = cache.filter({"type": "youtube_video"}, limit=10000)
        total = len(videos)
        print(f"Found {total} videos in cache\n")

        for i, video in enumerate(videos, 1):
            video_id = video.get('video_id', 'unknown')

            try:
                # Check if already has import metadata
                if 'source_type' in video and 'recommendation_weight' in video:
                    print(f"[{i}/{total}] {video_id} - SKIP (already has metadata)")
                    stats["skipped"] += 1
                    continue

                # Determine source type
                if video_id in bulk_channel_ids:
                    source_type = "bulk_channel"
                    weight = 0.5
                else:
                    source_type = "single_import"
                    weight = 1.0

                print(f"[{i}/{total}] {video_id} - {source_type} (weight: {weight})")

                if dry_run:
                    stats["updated"] += 1
                    continue

                # Update point metadata (preserve existing fields)
                cache_key = f"youtube:video:{video_id}"
                existing_data = cache.get(cache_key)

                if not existing_data:
                    print(f"[{i}/{total}] {video_id} - ERROR: Not found in cache")
                    stats["errors"] += 1
                    continue

                # Add import tracking to metadata
                metadata = {
                    "type": "youtube_video",
                    "source": "youtube-transcript-api",
                    "video_id": video_id,
                    "tags": video.get('tags', ''),
                    # Import tracking
                    "source_type": source_type,
                    "recommendation_weight": weight,
                    "imported_at": datetime.now().isoformat(),
                    "is_bulk_import": (source_type == "bulk_channel"),
                }

                # Re-insert with updated metadata
                cache.set(cache_key, existing_data, metadata=metadata)
                stats["updated"] += 1

            except Exception as e:
                print(f"[{i}/{total}] {video_id} - ERROR: {e}")
                stats["errors"] += 1

    finally:
        cache.close()

    print(f"\n{'=' * 70}")
    print(f"Qdrant Stats")
    print(f"{'=' * 70}")
    print(f"Updated: {stats['updated']}")
    print(f"Skipped: {stats['skipped']}")
    print(f"Errors: {stats['errors']}")
    print(f"{'=' * 70}\n")

    return stats


def main():
    """Main entry point."""
    import argparse

    parser = argparse.ArgumentParser(
        description="Add retroactive import metadata to archives and Qdrant cache"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be updated without making changes",
    )
    parser.add_argument(
        "--skip-archives",
        action="store_true",
        help="Skip updating archives (only update Qdrant)",
    )
    parser.add_argument(
        "--skip-qdrant",
        action="store_true",
        help="Skip updating Qdrant (only update archives)",
    )
    parser.add_argument(
        "--collection",
        default="cached_content",
        help="Qdrant collection name (default: cached_content)",
    )

    args = parser.parse_args()

    # Load bulk channel video IDs
    csv_path = project_root / "projects" / "data" / "queues" / "completed" / "nate_jones_videos_12mo.csv"
    print(f"Loading bulk channel video IDs from: {csv_path}")
    bulk_channel_ids = load_bulk_channel_video_ids(csv_path)
    print(f"Found {len(bulk_channel_ids)} bulk channel video IDs\n")

    if args.dry_run:
        print("[DRY RUN] No changes will be made\n")

    # Update archives
    if not args.skip_archives:
        archive_writer = create_local_archive_writer()
        archive_stats = update_archives(archive_writer, bulk_channel_ids, args.dry_run)
    else:
        print("[SKIP] Archives not updated\n")
        archive_stats = {"updated": 0, "skipped": 0, "errors": 0}

    # Update Qdrant cache
    if not args.skip_qdrant:
        qdrant_stats = update_qdrant_cache(args.collection, bulk_channel_ids, args.dry_run)
    else:
        print("[SKIP] Qdrant not updated\n")
        qdrant_stats = {"updated": 0, "skipped": 0, "errors": 0}

    # Final summary
    print("\n" + "=" * 70)
    print("Final Summary")
    print("=" * 70)
    print(f"Archives:")
    print(f"  Updated: {archive_stats['updated']}")
    print(f"  Skipped: {archive_stats['skipped']}")
    print(f"  Errors: {archive_stats['errors']}")
    print()
    print(f"Qdrant Cache:")
    print(f"  Updated: {qdrant_stats['updated']}")
    print(f"  Skipped: {qdrant_stats['skipped']}")
    print(f"  Errors: {qdrant_stats['errors']}")
    print("=" * 70)

    if args.dry_run:
        print("\n[DRY RUN] Run without --dry-run to apply changes")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\nInterrupted by user. Exiting...")
        sys.exit(0)
