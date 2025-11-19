#!/usr/bin/env python
"""Re-ingest archived videos with new structured tagging.

This script reads all videos from the archive and re-ingests them
into Qdrant with the new metadata extraction (structured tags, entities, references).

Usage:
    uv run python reingest_from_archive.py
    uv run python reingest_from_archive.py --collection cached_content --limit 5
"""

import asyncio
import argparse
import sys
from pathlib import Path

# Add project root
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))
sys.path.insert(0, str(project_root / "lessons" / "lesson-001"))

from compose.services.cache import create_qdrant_cache
from compose.services.archive import create_local_archive_reader
from youtube_agent.agent import create_agent
import json


async def reingest_all(collection_name: str = "cached_content", limit: int = None):
    """Re-ingest all archived videos with new tagging.
    
    Args:
        collection_name: Target Qdrant collection
        limit: Max number of videos to process (None = all)
    """
    print(f"\n{'='*70}")
    print(f"Re-ingesting Archived Videos with New Tagging")
    print(f"{'='*70}")
    print(f"Target collection: {collection_name}")
    print(f"Limit: {limit if limit else 'all'}")
    print(f"{'='*70}\n")
    
    # Initialize services
    archive = create_local_archive_reader()
    cache = create_qdrant_cache(
        collection_name=collection_name,
        qdrant_url="http://localhost:6335",
        infinity_url="http://localhost:7997"
    )
    agent = create_agent(instrument=False)
    
    # Get all videos from archive
    print("[1/3] Loading videos from archive...")
    all_videos = [v.video_id for v in archive.iter_youtube_videos()]
    
    if limit:
        all_videos = all_videos[:limit]
    
    print(f"  Found {len(all_videos)} videos to process\n")
    
    # Process each video
    print("[2/3] Generating metadata and caching...")
    success_count = 0
    skip_count = 0
    error_count = 0
    
    for i, video_id in enumerate(all_videos, 1):
        try:
            # Check if already in cache
            cache_key = f"youtube:video:{video_id}"
            if cache.exists(cache_key):
                print(f"  [{i}/{len(all_videos)}] SKIP: {video_id} (already cached)")
                skip_count += 1
                continue
            
            # Load from archive
            video_data = archive.get(video_id)
            if not video_data:
                print(f"  [{i}/{len(all_videos)}] ERROR: {video_id} (not in archive)")
                error_count += 1
                continue

            url = video_data.url
            transcript = video_data.raw_transcript
            
            if not transcript:
                print(f"  [{i}/{len(all_videos)}] SKIP: {video_id} (no transcript)")
                skip_count += 1
                continue
            
            # Generate structured metadata using agent
            print(f"  [{i}/{len(all_videos)}] Processing {video_id}...", end='', flush=True)
            
            result = await agent.run(url)
            tags_output = result.output if hasattr(result, 'output') else str(result)
            
            try:
                tags_data = json.loads(tags_output)
            except json.JSONDecodeError:
                print(f" ERROR: Failed to parse metadata JSON")
                error_count += 1
                continue
            
            # Build cache data
            cache_data = {
                "video_id": video_id,
                "url": url,
                "transcript": transcript,
                "transcript_length": len(transcript),
                "metadata": tags_data,
            }
            
            # Build flattened metadata for filtering
            metadata = {
                "type": "youtube_video",
                "source": "youtube-transcript-api",
                "video_id": video_id,
                "content_style": tags_data.get("content_style"),
                "difficulty": tags_data.get("difficulty"),
            }
            
            # Flatten metadata for Qdrant filtering
            from compose.services.metadata import flatten_video_metadata
            flattened = flatten_video_metadata(tags_data)
            metadata.update(flattened)
            
            # Cache it
            cache.set(cache_key, cache_data, metadata=metadata)
            
            title = tags_data.get('title', 'N/A')
            print(f" OK: {title[:50]}")
            success_count += 1
            
            # Small delay to avoid rate limiting
            await asyncio.sleep(0.5)
            
        except Exception as e:
            print(f"  [{i}/{len(all_videos)}] ERROR: {video_id} - {e}")
            error_count += 1
    
    # Summary
    print(f"\n[3/3] Re-ingestion complete")
    print(f"  Success: {success_count}")
    print(f"  Skipped: {skip_count}")
    print(f"  Errors: {error_count}")
    print(f"  Total: {len(all_videos)}")
    
    cache.close()
    
    print(f"\n{'='*70}")
    print(f"Done!")
    print(f"{'='*70}\n")


def main():
    parser = argparse.ArgumentParser(description="Re-ingest archived videos with new tagging")
    parser.add_argument(
        "--collection",
        "-c",
        default="cached_content",
        help="Target Qdrant collection (default: cached_content)"
    )
    parser.add_argument(
        "--limit",
        "-l",
        type=int,
        help="Max number of videos to process (default: all)"
    )
    
    args = parser.parse_args()
    
    asyncio.run(reingest_all(args.collection, args.limit))


if __name__ == "__main__":
    main()
