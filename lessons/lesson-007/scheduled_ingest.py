"""Scheduled ingestion of videos from CSV with rate limiting.

Ingests one video every 15 minutes to avoid hitting YouTube API rate limits.
Automatically skips videos that are already cached.
Exits gracefully on rate limit errors.
"""

import asyncio
import csv
import sys
import time
from pathlib import Path
from datetime import datetime

# Add project root and lesson-001 to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))
sys.path.insert(0, str(project_root / "lessons" / "lesson-001"))

from youtube_agent.tools import get_transcript, extract_video_id
from youtube_agent.agent import create_agent
from tools.services.cache import create_qdrant_cache
from tools.env_loader import load_root_env

load_root_env()


async def ingest_video(url: str, cache) -> tuple[bool, str]:
    """Fetch transcript, generate tags, and insert into Qdrant.

    Args:
        url: YouTube video URL
        cache instance

    Returns:
        Tuple of (success: bool, message: str)
    """
    try:
        # Extract video ID
        video_id = extract_video_id(url)
        cache_key = f"youtube:video:{video_id}"

        # Check if already cached
        if cache.exists(cache_key):
            return True, f"SKIPPED - Already cached (ID: {video_id})"

        # Fetch transcript
        print(f"  [1/3] Fetching transcript for video ID: {video_id}...")
        transcript = get_transcript(url, cache=None)

        # Check for rate limit or other errors
        if "ERROR:" in transcript:
            if "Too Many Requests" in transcript or "429" in transcript:
                return False, f"RATE_LIMIT - {transcript}"
            return False, f"ERROR - {transcript}"

        print(f"  [2/3] Generating tags ({len(transcript)} chars)...")
        agent = create_agent(instrument=False)

        result = await agent.run(
            f"Analyze this YouTube video transcript and generate 3-5 relevant tags. "
            f"Return ONLY the tags as a comma-separated list, nothing else.\n\n"
            f"Transcript:\n{transcript[:15000]}"
        )

        tags = result.output if hasattr(result, 'output') else str(result)
        tags = tags.strip()

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
        }

        # Insert into Qdrant
        print(f"  [3/3] Inserting into Qdrant...")
        cache.set(cache_key, cache_data, metadata=metadata)

        return True, f"SUCCESS - Cached {video_id} ({len(transcript)} chars)"

    except ValueError as e:
        return False, f"ERROR - Invalid URL: {e}"
    except Exception as e:
        return False, f"ERROR - {type(e).__name__}: {e}"


async def process_csv(
    csv_path: Path,
    collection_name: str = "cached_content",
    interval_minutes: int = 15,
):
    """Process videos from CSV with scheduled rate limiting.

    Args:
        csv_path: Path to CSV file with 'url' column
        collection_name: Qdrant collection name
        interval_minutes: Minutes to wait between ingestions
    """
    print("=" * 80)
    print("Scheduled YouTube Video Ingestion")
    print("=" * 80)
    print(f"CSV File: {csv_path}")
    print(f"Collection: {collection_name}")
    print(f"Interval: {interval_minutes} minutes between videos")
    print(f"Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 80)
    print()

    # Initialize cache
    cache = create_qdrant_cache(collection_name=collection_name)
    print(f"[OK] Connected to Qdrant collection: {collection_name}\n")

    # Read CSV
    if not csv_path.exists():
        print(f"[ERROR] CSV file not found: {csv_path}")
        return

    with open(csv_path, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        videos = list(reader)

    if not videos:
        print("[ERROR] No videos found in CSV")
        return

    if 'url' not in videos[0]:
        print("[ERROR] CSV must have 'url' column")
        return

    total_videos = len(videos)
    print(f"[INFO] Found {total_videos} videos in CSV\n")

    # Process videos
    processed = 0
    skipped = 0
    failed = 0
    interval_seconds = interval_minutes * 60

    for i, row in enumerate(videos, 1):
        url = row['url'].strip()
        title = row.get('title', 'N/A')[:60]  # Truncate title

        print(f"\n[{i}/{total_videos}] Processing video:")
        print(f"  Title: {title}")
        print(f"  URL: {url}")

        # Process the video
        success, message = await ingest_video(url, cache)

        # Handle result
        if "RATE_LIMIT" in message:
            print(f"\n[RATE LIMIT DETECTED]")
            print(f"Message: {message}")
            print(f"\nExiting to avoid further rate limit issues.")
            print(f"Resume later - already processed {i-1}/{total_videos} videos")
            break

        elif "SKIPPED" in message:
            print(f"  {message}")
            skipped += 1

        elif success:
            print(f"  {message}")
            processed += 1

        else:
            print(f"  {message}")
            failed += 1

        # Show summary so far
        print(f"\n  Progress: {processed} processed, {skipped} skipped, {failed} failed")

        # Wait before next video (unless this is the last one or we hit an error)
        if i < total_videos and success and "SKIPPED" not in message:
            next_time = datetime.now().timestamp() + interval_seconds
            next_time_str = datetime.fromtimestamp(next_time).strftime('%H:%M:%S')
            print(f"  Waiting {interval_minutes} minutes... (next video at {next_time_str})")

            # Sleep in chunks so we can respond to Ctrl+C faster
            for _ in range(interval_seconds):
                await asyncio.sleep(1)

    # Final summary
    print("\n" + "=" * 80)
    print("FINAL SUMMARY")
    print("=" * 80)
    print(f"Total videos in CSV: {total_videos}")
    print(f"Successfully processed: {processed}")
    print(f"Skipped (already cached): {skipped}")
    print(f"Failed: {failed}")
    print(f"Completed: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 80)


def main():
    """Main entry point."""
    if len(sys.argv) < 2:
        print("Usage: python scheduled_ingest.py <csv_path> [collection_name] [interval_minutes]")
        print("\nExample:")
        print("  python scheduled_ingest.py ../../projects/video-lists/nate_jones_videos.csv")
        print("  python scheduled_ingest.py videos.csv cached_content 15")
        print("\nDefault collection: cached_content")
        print("Default interval: 15 minutes")
        sys.exit(1)

    csv_path = Path(sys.argv[1])
    collection_name = sys.argv[2] if len(sys.argv) > 2 else "cached_content"
    interval_minutes = int(sys.argv[3]) if len(sys.argv) > 3 else 15

    try:
        asyncio.run(process_csv(csv_path, collection_name, interval_minutes))
    except KeyboardInterrupt:
        print("\n\n[INTERRUPTED] Stopped by user (Ctrl+C)")
        print("You can resume later - progress is saved in Qdrant cache")
        sys.exit(0)


if __name__ == "__main__":
    main()
