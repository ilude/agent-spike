"""Non-interactive batch CSV ingestion (no rate limiting).

Simple batch processor for ingesting YouTube videos from CSV files.
No REPL, no user interaction - just processes the entire CSV and exits.

Usage:
    uv run python tools/scripts/batch_ingest_youtube.py <csv_file>
"""

print("[DEBUG] Starting batch_ingest_youtube.py...")

import asyncio
import csv
import sys
from pathlib import Path
from datetime import datetime

print("[DEBUG] Basic imports done, setting up environment...")

# Use script_base for proper environment setup
from compose.cli.base import setup_script_environment
setup_script_environment(needs_agent=True)

print("[DEBUG] Environment setup complete...")

# Import from centralized services
print("[DEBUG] Importing services...")
from compose.services.youtube import get_transcript, extract_video_id
print("[DEBUG] YouTube services imported")
from compose.services.cache import create_qdrant_cache
print("[DEBUG] Cache services imported")
from compose.services.archive import create_local_archive_writer, ImportMetadata, ChannelContext
print("[DEBUG] Archive services imported")

# Import agent from lesson (still experimental)
print("[DEBUG] Importing agent...")
from youtube_agent.agent import create_agent
print("[DEBUG] All imports complete!")


async def ingest_video(
    url: str,
    collection_name: str,
    archive_writer,
    source_type: str = "bulk_channel",
    channel_id: str = None,
    channel_name: str = None,
) -> tuple[bool, str]:
    """Fetch transcript, generate tags, archive, and cache.

    Pipeline:
    1. Check cache (skip if exists)
    2. Fetch transcript -> Archive immediately
    3. Generate tags -> Archive immediately
    4. Cache result

    Args:
        url: YouTube video URL
        collection_name: Qdrant collection name
        archive_writer: Archive service for storing expensive data
        source_type: Import source type (bulk_channel by default)
        channel_id: Optional channel ID for bulk imports
        channel_name: Optional channel name for bulk imports

    Returns:
        Tuple of (success: bool, message: str)
    """
    cache = None
    try:
        cache = create_qdrant_cache(
            collection_name=collection_name,
            qdrant_url="http://localhost:6335",
            infinity_url="http://localhost:7997"
        )

        # Extract video ID
        video_id = extract_video_id(url)
        cache_key = f"youtube:video:{video_id}"

        # Check if already cached
        if cache.exists(cache_key):
            return True, f"SKIPPED - Already cached (ID: {video_id})"

        # Fetch transcript (using Webshare proxy)
        print(f"  [1/3] Fetching transcript for video ID: {video_id}...")
        transcript = get_transcript(url, cache=None)

        # Check for errors
        if "ERROR:" in transcript:
            return False, f"ERROR - {transcript}"

        # Archive transcript immediately (expensive API call)
        # Determine recommendation weight based on source type
        weight_map = {
            "single_import": 1.0,
            "repl_import": 1.0,
            "bulk_channel": 0.5,
            "bulk_multi_channel": 0.2,
        }

        import_metadata = ImportMetadata(
            source_type=source_type,
            imported_at=datetime.now(),
            import_method="cli",
            channel_context=ChannelContext(
                channel_id=channel_id,
                channel_name=channel_name,
                is_bulk_import=True,
            ),
            recommendation_weight=weight_map.get(source_type, 0.5),
        )

        archive_writer.archive_youtube_video(
            video_id=video_id,
            url=url,
            transcript=transcript,
            metadata={"source": "youtube-transcript-api"},
            import_metadata=import_metadata,
        )

        # Generate tags
        print(f"  [2/3] Generating tags ({len(transcript)} chars)...")
        agent = create_agent(instrument=False)

        result = await agent.run(
            f"Analyze this YouTube video transcript and generate 3-5 relevant tags. "
            f"Return ONLY the tags as a comma-separated list, nothing else.\n\n"
            f"Transcript:\n{transcript[:15000]}"
        )

        tags = result.output if hasattr(result, 'output') else str(result)
        tags = tags.strip()

        # Archive LLM output (expensive operation)
        archive_writer.add_llm_output(
            video_id=video_id,
            output_type="tags",
            output_value=tags,
            model="claude-3-5-haiku-20241022",
            cost_usd=0.001,  # Approximate
        )

        # Prepare cache entry
        cache_data = {
            "video_id": video_id,
            "url": url,
            "transcript": transcript,
            "tags": tags,
            "transcript_length": len(transcript),
        }

        metadata = {
            "type": "youtube_video",
            "source": "youtube-transcript-api",
            "video_id": video_id,
            "tags": tags,
            # Import tracking for recommendations
            "source_type": source_type,
            "recommendation_weight": weight_map.get(source_type, 0.5),
            "imported_at": datetime.now().isoformat(),
            "is_bulk_import": True,
        }

        if channel_id:
            metadata["channel_id"] = channel_id

        # Insert into Qdrant
        print(f"  [3/3] Caching in Qdrant...")
        cache.set(cache_key, cache_data, metadata=metadata)

        return True, f"SUCCESS - Cached {video_id} ({len(transcript)} chars, tags: {tags[:50]}...)"

    except ValueError as e:
        return False, f"ERROR - Invalid URL: {e}"
    except Exception as e:
        return False, f"ERROR - {type(e).__name__}: {e}"
    finally:
        if cache is not None:
            cache.close()


async def process_csv(csv_path: Path, collection_name: str) -> dict:
    """Process all videos from CSV file.

    Args:
        csv_path: Path to CSV file
        collection_name: Qdrant collection name

    Returns:
        Dict with stats: {processed, skipped, errors, total}
    """
    print(f"\n{'='*80}")
    print(f"Batch YouTube Video Ingestion")
    print(f"{'='*80}")
    print(f"CSV: {csv_path}")
    print(f"Collection: {collection_name}")
    print(f"{'='*80}\n")

    # Read CSV
    with open(csv_path, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        videos = list(reader)

    total = len(videos)
    print(f"[CSV] Found {total} videos\n")

    # Detect channel info from CSV (if present)
    channel_id = None
    channel_name = None
    if videos and 'channel_id' in videos[0]:
        channel_id = videos[0].get('channel_id', '').strip() or None
        channel_name = videos[0].get('channel_title', '').strip() or None
        if channel_name:
            print(f"[CSV] Detected channel: {channel_name} ({channel_id})")
        else:
            print(f"[CSV] No channel info - using bulk_channel source type")
    else:
        print(f"[CSV] No channel info - using bulk_channel source type")

    # Create archive writer
    archive_writer = create_local_archive_writer()

    # Check which videos need processing (skip already cached)
    cache = create_qdrant_cache(
        collection_name=collection_name,
        qdrant_url="http://localhost:6335",
        infinity_url="http://localhost:7997"
    )
    try:
        unprocessed = []
        for video in videos:
            url = video.get('url', '').strip()
            if not url:
                continue

            video_id = extract_video_id(url)
            cache_key = f"youtube:video:{video_id}"

            if not cache.exists(cache_key):
                unprocessed.append(video)

        print(f"[CSV] {len(unprocessed)} videos need processing")
        print(f"[CSV] {total - len(unprocessed)} videos already cached\n")
    finally:
        cache.close()

    # Process videos
    processed = 0
    skipped = 0
    errors = 0

    for i, video in enumerate(unprocessed, 1):
        url = video['url']
        title = video.get('title', 'N/A')[:60]

        print(f"[{i}/{len(unprocessed)}] {title}")
        print(f"  URL: {url}")

        success, message = await ingest_video(
            url=url,
            collection_name=collection_name,
            archive_writer=archive_writer,
            source_type="bulk_channel",
            channel_id=channel_id,
            channel_name=channel_name,
        )

        if success:
            if "SKIPPED" in message:
                skipped += 1
            else:
                processed += 1
        else:
            errors += 1

        print(f"  {message}\n")

    # Print summary
    print(f"\n{'='*80}")
    print(f"Batch Processing Complete!")
    print(f"{'='*80}")
    print(f"Total videos: {total}")
    print(f"Processed: {processed}")
    print(f"Skipped (already cached): {total - len(unprocessed)}")
    print(f"Skipped (errors): {skipped}")
    print(f"Errors: {errors}")
    print(f"{'='*80}\n")

    return {
        "total": total,
        "processed": processed,
        "skipped": skipped,
        "errors": errors,
    }


async def main():
    """Main entry point."""
    if len(sys.argv) < 2:
        print("Usage: uv run python tools/scripts/batch_ingest_youtube.py <csv_file>")
        sys.exit(1)

    csv_path = Path(sys.argv[1])
    if not csv_path.exists():
        print(f"ERROR: CSV file not found: {csv_path}")
        sys.exit(1)

    # Use CSV filename as collection name (sanitized)
    collection_name = "cached_content"

    await process_csv(csv_path, collection_name)


if __name__ == "__main__":
    asyncio.run(main())
