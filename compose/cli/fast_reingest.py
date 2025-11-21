#!/usr/bin/env python
"""Fast re-ingest from archive - uses existing metadata, no LLM calls.

This script reads archived videos and re-ingests them into Qdrant
using the existing metadata from the archive (no API calls needed).

Usage:
    cd compose/cli
    uv run python fast_reingest.py
    uv run python fast_reingest.py --collection content --limit 10
    uv run python fast_reingest.py --force  # Re-ingest even if already cached
"""

import argparse
import sys
from pathlib import Path

# Add project root
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from compose.services.cache import create_qdrant_cache
from compose.services.archive import create_local_archive_reader


def fast_reingest(collection_name: str = "content", limit: int = None, force: bool = False):
    """Fast re-ingest using existing archive metadata.

    Args:
        collection_name: Target Qdrant collection
        limit: Max number of videos to process (None = all)
        force: Re-ingest even if already in cache
    """
    print(f"\n{'='*70}")
    print(f"Fast Re-ingest from Archive (no LLM calls)")
    print(f"{'='*70}")
    print(f"Collection: {collection_name}")
    print(f"Limit: {limit if limit else 'all'}")
    print(f"Force: {force}")
    print(f"{'='*70}\n")

    # Initialize services
    archive = create_local_archive_reader()
    cache = create_qdrant_cache(
        collection_name=collection_name,
        qdrant_url="http://localhost:6335",
        infinity_url="http://localhost:7997"
    )

    # Get all videos from archive
    print("[1/2] Loading videos from archive...")
    all_videos = list(archive.iter_youtube_videos())

    if limit:
        all_videos = all_videos[:limit]

    print(f"  Found {len(all_videos)} videos to process\n")

    # Process each video
    print("[2/2] Embedding and caching...")
    success_count = 0
    skip_count = 0
    error_count = 0

    for i, video in enumerate(all_videos, 1):
        try:
            video_id = video.video_id
            cache_key = f"youtube:video:{video_id}"

            # Check if already in cache
            if not force and cache.exists(cache_key):
                print(f"  [{i}/{len(all_videos)}] SKIP: {video_id} (already cached)")
                skip_count += 1
                continue

            # Load full data from archive
            video_data = archive.get(video_id)
            if not video_data:
                print(f"  [{i}/{len(all_videos)}] ERROR: {video_id} (not in archive)")
                error_count += 1
                continue

            transcript = video_data.raw_transcript
            if not transcript:
                print(f"  [{i}/{len(all_videos)}] SKIP: {video_id} (no transcript)")
                skip_count += 1
                continue

            # Get YouTube metadata
            yt_meta = video_data.youtube_metadata or {}
            title = yt_meta.get("title", "Unknown")

            # Get LLM-generated tags if available
            llm_tags = []
            if video_data.llm_outputs:
                for output in video_data.llm_outputs:
                    if output.output_type == "tags":
                        tag_str = output.output_value or ""
                        llm_tags = [t.strip() for t in tag_str.split(",") if t.strip()]
                        break

            # Build cache data
            cache_data = {
                "video_id": video_id,
                "url": video_data.url,
                "title": title,
                "description": yt_meta.get("description", ""),
                "transcript": transcript,
                "transcript_length": len(transcript),
                "channel_title": yt_meta.get("channel_title", ""),
                "channel_id": yt_meta.get("channel_id", ""),
                "published_at": yt_meta.get("published_at", ""),
                "duration_seconds": yt_meta.get("duration_seconds", 0),
                "view_count": yt_meta.get("view_count", 0),
                "youtube_tags": yt_meta.get("tags", []),
                "llm_tags": llm_tags,
            }

            # Build metadata for Qdrant filtering
            metadata = {
                "type": "youtube_video",
                "source": "archive",
                "video_id": video_id,
                "channel_id": yt_meta.get("channel_id", ""),
                "channel_title": yt_meta.get("channel_title", ""),
                "has_transcript": True,
            }

            # Cache it (embedding happens in cache.set)
            cache.set(cache_key, cache_data, metadata=metadata)

            print(f"  [{i}/{len(all_videos)}] OK: {title[:50]}...")
            success_count += 1

        except Exception as e:
            print(f"  [{i}/{len(all_videos)}] ERROR: {video_id} - {e}")
            error_count += 1

    # Summary
    print(f"\n{'='*70}")
    print(f"Re-ingestion complete!")
    print(f"  Success: {success_count}")
    print(f"  Skipped: {skip_count}")
    print(f"  Errors: {error_count}")
    print(f"  Total: {len(all_videos)}")
    print(f"{'='*70}\n")

    cache.close()


def main():
    parser = argparse.ArgumentParser(description="Fast re-ingest from archive (no LLM calls)")
    parser.add_argument(
        "--collection", "-c",
        default="content",
        help="Target Qdrant collection (default: content)"
    )
    parser.add_argument(
        "--limit", "-l",
        type=int,
        help="Max number of videos to process (default: all)"
    )
    parser.add_argument(
        "--force", "-f",
        action="store_true",
        help="Re-ingest even if already in cache"
    )

    args = parser.parse_args()
    fast_reingest(args.collection, args.limit, args.force)


if __name__ == "__main__":
    main()
