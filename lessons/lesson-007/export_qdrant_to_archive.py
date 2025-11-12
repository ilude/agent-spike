"""Export existing Qdrant data to archive storage.

This script reads all cached videos from Qdrant and creates archive files
in projects/data/archive/youtube/. This is a one-time migration to establish
the archive as the source of truth.

Run with: uv run python export_qdrant_to_archive.py
"""

import sys
from pathlib import Path

# Bootstrap: Add project root to path so we can import lessons.lesson_base
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from lessons.lesson_base import setup_lesson_environment

setup_lesson_environment()

from tools.services.cache import create_qdrant_cache
from archive import LocalArchiveWriter


def export_all_videos(collection_name: str = "cached_content", dry_run: bool = False):
    """Export all videos from Qdrant to archive.

    Args:
        collection_name: Qdrant collection to export from
        dry_run: If True, only print what would be done without writing files
    """
    print(f"\n{'='*70}")
    print(f"Exporting Qdrant Collection to Archive")
    print(f"{'='*70}")
    print(f"Collection: {collection_name}")
    print(f"Dry run: {dry_run}")
    print(f"{'='*70}\n")

    # Initialize cache and archive
    cache = create_qdrant_cache(collection_name=collection_name)
    writer = LocalArchiveWriter()

    # Get all videos from cache
    print(f"[1/3] Fetching videos from Qdrant...")
    all_videos = cache.filter({}, limit=10000)  # Get all videos
    print(f"  Found {len(all_videos)} videos in collection\n")

    if len(all_videos) == 0:
        print(f"  No videos to export. Exiting.")
        return

    # Export each video
    print(f"[2/3] Exporting to archive...")
    exported = 0
    skipped = 0
    errors = 0

    for i, video in enumerate(all_videos, 1):
        video_id = video.get("video_id")
        if not video_id:
            print(f"  [{i}/{len(all_videos)}] SKIP: No video_id in record")
            skipped += 1
            continue

        # Check if already archived
        if writer.exists(video_id):
            print(f"  [{i}/{len(all_videos)}] SKIP: {video_id} (already archived)")
            skipped += 1
            continue

        # Extract data
        url = video.get("url", f"https://www.youtube.com/watch?v={video_id}")
        transcript = video.get("transcript", "")
        tags = video.get("tags", "")

        # Build metadata from what we have
        metadata = {
            "source": "exported_from_qdrant",
            "original_collection": collection_name,
        }

        # Add any other fields as metadata
        for key in ["title", "channel", "upload_date", "duration"]:
            if key in video:
                metadata[key] = video[key]

        if dry_run:
            print(f"  [{i}/{len(all_videos)}] DRY RUN: Would archive {video_id}")
            print(f"                      URL: {url}")
            print(f"                      Transcript: {len(transcript)} chars")
            print(f"                      Tags: {tags}")
            exported += 1
            continue

        # Archive the video
        try:
            archive_path = writer.archive_youtube_video(
                video_id=video_id,
                url=url,
                transcript=transcript,
                metadata=metadata,
            )

            # Add LLM output for tags if present
            if tags:
                writer.add_llm_output(
                    video_id=video_id,
                    output_type="tags",
                    output_value=tags,
                    model="unknown",  # We don't know which model generated these
                    cost_usd=None,  # Cost not tracked in original data
                )

            # Add processing record
            writer.add_processing_record(
                video_id=video_id,
                version="v1_full_embed",
                collection_name=collection_name,
                notes="Migrated from Qdrant",
            )

            print(f"  [{i}/{len(all_videos)}] OK: {video_id} ({len(transcript)} chars)")
            exported += 1

        except Exception as e:
            print(f"  [{i}/{len(all_videos)}] ERROR: {video_id} - {e}")
            errors += 1

    # Summary
    print(f"\n[3/3] Export complete")
    print(f"  Exported: {exported}")
    print(f"  Skipped: {skipped}")
    print(f"  Errors: {errors}")
    print(f"  Total: {len(all_videos)}")

    if not dry_run:
        # Verify
        archive_count = writer.count()
        print(f"\n  Archive now contains: {archive_count} videos")

    print(f"\n{'='*70}")
    print(f"Export {'would be' if dry_run else 'is'} complete!")
    print(f"{'='*70}\n")


def main():
    """Main entry point."""
    import argparse

    parser = argparse.ArgumentParser(description="Export Qdrant data to archive")
    parser.add_argument(
        "--collection",
        default="cached_content",
        help="Qdrant collection name (default: cached_content)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print what would be done without actually exporting",
    )

    args = parser.parse_args()

    export_all_videos(collection_name=args.collection, dry_run=args.dry_run)


if __name__ == "__main__":
    main()
