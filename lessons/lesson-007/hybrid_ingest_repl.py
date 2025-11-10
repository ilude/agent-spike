"""Hybrid REPL with background scheduled ingestion and manual URL processing.

Features:
- Background scheduler processing CSV at 1 video per 15 minutes
- Manual URL input with rate limiting (5 videos per 15 minutes)
- Auto-append to CSV if rate limit would be exceeded
- No quotes needed for URLs
"""

import asyncio
import csv
import sys
from pathlib import Path
from datetime import datetime, timedelta
from collections import deque

# Add project root and lesson-001 to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))
sys.path.insert(0, str(project_root / "lessons" / "lesson-001"))

from youtube_agent.tools import get_transcript, extract_video_id
from youtube_agent.agent import create_agent
from cache import QdrantCache
from tools.env_loader import load_root_env

load_root_env()


class RateLimiter:
    """Track ingestion timestamps to enforce rate limits."""

    def __init__(self, max_ingests: int = 5, window_minutes: int = 15):
        self.max_ingests = max_ingests
        self.window_minutes = window_minutes
        self.timestamps = deque()

    def add_ingest(self):
        """Record a new ingestion timestamp."""
        self.timestamps.append(datetime.now())

    def can_ingest(self) -> bool:
        """Check if we can ingest without exceeding rate limit."""
        now = datetime.now()
        cutoff = now - timedelta(minutes=self.window_minutes)

        # Remove old timestamps outside the window
        while self.timestamps and self.timestamps[0] < cutoff:
            self.timestamps.popleft()

        return len(self.timestamps) < self.max_ingests

    def get_status(self) -> str:
        """Get current rate limit status."""
        now = datetime.now()
        cutoff = now - timedelta(minutes=self.window_minutes)

        # Clean old timestamps
        while self.timestamps and self.timestamps[0] < cutoff:
            self.timestamps.popleft()

        count = len(self.timestamps)
        return f"{count}/{self.max_ingests} in last {self.window_minutes} min"

    def time_until_available(self) -> int:
        """Get seconds until next slot is available."""
        if self.can_ingest():
            return 0

        # Oldest timestamp will expire first
        oldest = self.timestamps[0]
        expires_at = oldest + timedelta(minutes=self.window_minutes)
        delta = expires_at - datetime.now()
        return max(0, int(delta.total_seconds()))


async def ingest_video(url: str, collection_name: str, rate_limiter: RateLimiter) -> tuple[bool, str]:
    """Fetch transcript, generate tags, and insert into Qdrant.

    Args:
        url: YouTube video URL
        collection_name: Qdrant collection name
        rate_limiter: RateLimiter instance

    Returns:
        Tuple of (success: bool, message: str)
    """
    # Create cache connection only for this operation
    cache = None
    try:
        cache = QdrantCache(collection_name=collection_name)

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

        # Record successful ingestion
        rate_limiter.add_ingest()

        return True, f"SUCCESS - Cached {video_id} ({len(transcript)} chars)"

    except ValueError as e:
        return False, f"ERROR - Invalid URL: {e}"
    except Exception as e:
        return False, f"ERROR - {type(e).__name__}: {e}"
    finally:
        # Close cache connection to release lock
        if cache is not None:
            del cache


def append_url_to_csv(csv_path: Path, url: str):
    """Insert URL at the beginning of CSV (after header).

    Args:
        csv_path: Path to CSV file
        url: YouTube URL to add
    """
    try:
        # Read existing CSV
        with open(csv_path, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            fieldnames = reader.fieldnames
            existing_rows = list(reader)

        # Create new row (minimal data, just URL)
        new_row = {field: '' for field in fieldnames}
        new_row['url'] = url
        new_row['title'] = '[Manual addition - pending metadata]'

        # Write back with new row at top
        with open(csv_path, 'w', encoding='utf-8', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerow(new_row)  # New URL first
            writer.writerows(existing_rows)

        return True
    except Exception as e:
        print(f"[ERROR] Failed to append to CSV: {e}")
        return False


async def background_scheduler(
    csv_path: Path,
    collection_name: str,
    rate_limiter: RateLimiter,
    stop_event: asyncio.Event,
    interval_minutes: int = 15,
    next_run_time: list = None,  # Mutable list to share next run time
):
    """Background task to process CSV videos at scheduled intervals.

    Args:
        csv_path: Path to CSV file
        collection_name: Qdrant collection name
        rate_limiter: RateLimiter instance
        stop_event: Event to signal stop
        interval_minutes: Minutes between videos
        next_run_time: Shared list to track next scheduled run
    """
    print(f"[SCHEDULER] Starting background scheduler ({interval_minutes} min intervals)")

    interval_seconds = interval_minutes * 60
    processed = 0

    if next_run_time is None:
        next_run_time = []

    while not stop_event.is_set():
        try:
            # Read CSV to find next unprocessed video
            if not csv_path.exists():
                await asyncio.sleep(60)  # Wait and retry
                continue

            with open(csv_path, 'r', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                videos = list(reader)

            # Find first unprocessed video (need to check cache)
            next_video = None
            cache = None
            try:
                cache = QdrantCache(collection_name=collection_name)
                for video in videos:
                    url = video.get('url', '').strip()
                    if not url:
                        continue

                    try:
                        video_id = extract_video_id(url)
                        cache_key = f"youtube:video:{video_id}"
                        if not cache.exists(cache_key):
                            next_video = video
                            break
                    except:
                        continue
            finally:
                if cache:
                    del cache

            if next_video:
                url = next_video['url']
                title = next_video.get('title', 'N/A')[:60]

                print(f"\n[SCHEDULER] Processing next video:")
                print(f"  Title: {title}")
                print(f"  URL: {url}")

                success, message = await ingest_video(url, collection_name, rate_limiter)

                if "RATE_LIMIT" in message:
                    print(f"[SCHEDULER] Rate limit detected, pausing for 1 hour...")
                    await asyncio.sleep(3600)  # Wait 1 hour
                    continue

                elif success:
                    print(f"  {message}")
                    processed += 1
                    print(f"[SCHEDULER] Total processed: {processed}")

                else:
                    print(f"  {message}")

                # Calculate and store next run time
                next_time = datetime.now() + timedelta(minutes=interval_minutes)
                if next_run_time:
                    next_run_time[0] = next_time
                else:
                    next_run_time.append(next_time)

                # Wait interval before next video
                print(f"[SCHEDULER] Waiting {interval_minutes} minutes... (next run at {next_time.strftime('%H:%M:%S')})")
                await asyncio.sleep(interval_seconds)

            else:
                # No more unprocessed videos, wait and check again
                await asyncio.sleep(60)

        except Exception as e:
            print(f"[SCHEDULER ERROR] {e}")
            await asyncio.sleep(60)


async def interactive_repl(
    csv_path: Path,
    collection_name: str,
    rate_limiter: RateLimiter,
):
    """Run interactive REPL while background scheduler runs.

    Args:
        csv_path: Path to CSV file for scheduler
        collection_name: Qdrant collection name
        rate_limiter: RateLimiter instance
    """
    print("=" * 80)
    print("Hybrid YouTube Video Ingestion REPL + Scheduler")
    print("=" * 80)
    print(f"Collection: {collection_name}")
    print(f"CSV File: {csv_path}")
    print()
    print("Features:")
    print("  - Background scheduler: 1 video per 15 minutes from CSV")
    print("  - Manual ingestion: Up to 5 videos per 15 minutes")
    print("  - Auto-append to CSV if rate limit would be exceeded")
    print()
    print("Commands:")
    print("  - Paste any YouTube URL (no quotes needed)")
    print("  - 'status' - Show rate limit status")
    print("  - 'list' - Show all cached videos")
    print("  - 'count' - Show total cached videos")
    print("  - 'quit' or 'exit' - Exit the REPL")
    print("  - 'help' - Show this help message")
    print("=" * 80)
    print()

    # Start background scheduler
    stop_event = asyncio.Event()
    next_run_time = []  # Shared state for next scheduled run
    scheduler_task = asyncio.create_task(
        background_scheduler(csv_path, collection_name, rate_limiter, stop_event, interval_minutes=15, next_run_time=next_run_time)
    )

    try:
        while True:
            try:
                # Get input (this blocks, but scheduler runs in background)
                user_input = await asyncio.get_event_loop().run_in_executor(
                    None, input, ">> "
                )
                user_input = user_input.strip()

                if not user_input:
                    continue

                # Handle commands
                if user_input.lower() in ['quit', 'exit', 'q']:
                    print("\nStopping scheduler...")
                    stop_event.set()
                    await scheduler_task
                    print("Goodbye!")
                    break

                elif user_input.lower() == 'help':
                    print("\nCommands:")
                    print("  - Paste any YouTube URL (no quotes needed)")
                    print("  - 'status' - Show rate limit status")
                    print("  - 'list' - Show all cached videos")
                    print("  - 'count' - Show total cached videos")
                    print("  - 'quit' or 'exit' - Exit the REPL")
                    print("  - 'help' - Show this help message")
                    print()

                elif user_input.lower() == 'status':
                    print(f"\n=== STATUS ===")
                    print(f"Rate limit: {rate_limiter.get_status()}")

                    if not rate_limiter.can_ingest():
                        wait_time = rate_limiter.time_until_available()
                        wait_mins = wait_time // 60
                        wait_secs = wait_time % 60
                        print(f"Manual ingestion available in: {wait_mins}m {wait_secs}s")
                    else:
                        print("Manual ingestion: READY (can process immediately)")

                    # Show scheduler info
                    if next_run_time:
                        next_time = next_run_time[0]
                        delta = next_time - datetime.now()
                        delta_mins = int(delta.total_seconds() / 60)
                        delta_secs = int(delta.total_seconds() % 60)
                        print(f"\nScheduler next run: {next_time.strftime('%H:%M:%S')} (in {delta_mins}m {delta_secs}s)")
                    else:
                        print(f"\nScheduler: Starting up...")

                    # Show cache count
                    cache = None
                    try:
                        cache = QdrantCache(collection_name=collection_name)
                        videos = cache.filter({"type": "youtube_video"}, limit=1000)
                        print(f"Total cached videos: {len(videos)}")
                    finally:
                        if cache:
                            del cache
                    print()

                elif user_input.lower() == 'list':
                    print("\nFetching cached videos...")
                    cache = None
                    try:
                        cache = QdrantCache(collection_name=collection_name)
                        videos = cache.filter({"type": "youtube_video"}, limit=100)
                        if videos:
                            print(f"\nFound {len(videos)} cached videos (showing first 10):")
                            for i, video in enumerate(videos[:10], 1):
                                video_id = video.get('video_id', 'N/A')
                                transcript_len = video.get('transcript_length', 0)
                                print(f"  {i}. {video_id} ({transcript_len:,} chars)")
                        else:
                            print("\n[INFO] No videos found in cache.")
                    finally:
                        if cache:
                            del cache
                    print()

                elif user_input.lower() == 'count':
                    cache = None
                    try:
                        cache = QdrantCache(collection_name=collection_name)
                        videos = cache.filter({"type": "youtube_video"}, limit=1000)
                        print(f"\nTotal cached videos: {len(videos)}")
                        print(f"Rate limit status: {rate_limiter.get_status()}\n")
                    finally:
                        if cache:
                            del cache

                elif user_input.startswith('http'):
                    # Manual URL ingestion
                    print(f"\nProcessing: {user_input}")

                    # Check rate limit
                    if rate_limiter.can_ingest():
                        print(f"Rate limit OK ({rate_limiter.get_status()})")
                        success, message = await ingest_video(user_input, collection_name, rate_limiter)

                        if success:
                            print(f"{message}\n")
                        else:
                            print(f"{message}\n")

                    else:
                        # Rate limit exceeded, append to CSV
                        wait_time = rate_limiter.time_until_available()
                        wait_mins = wait_time // 60
                        print(f"[RATE LIMIT] Already processed {rate_limiter.max_ingests} videos in last {rate_limiter.window_minutes} minutes")
                        print(f"Next slot available in: {wait_mins} minutes")
                        print(f"\nAppending URL to CSV for scheduled processing...")

                        if append_url_to_csv(csv_path, user_input):
                            print(f"[OK] URL added to top of CSV queue")
                            print(f"     Will be processed by scheduler next (in ~15 minutes)")
                        else:
                            print(f"[ERROR] Failed to add URL to CSV")
                        print()

                else:
                    print(f"[ERROR] Unknown command or invalid URL: {user_input}")
                    print("Type 'help' for available commands.\n")

            except EOFError:
                print("\n\nStopping scheduler...")
                stop_event.set()
                await scheduler_task
                print("Goodbye!")
                break

    except KeyboardInterrupt:
        print("\n\nStopping scheduler...")
        stop_event.set()
        await scheduler_task
        print("Goodbye!")

    except Exception as e:
        print(f"\n[ERROR] {e}")
        stop_event.set()
        await scheduler_task


async def main():
    """Main entry point."""
    if len(sys.argv) < 2:
        # Default to Nate Jones CSV
        csv_path = project_root / "projects" / "video-lists" / "nate_jones_videos.csv"
    else:
        csv_path = Path(sys.argv[1])

    collection_name = sys.argv[2] if len(sys.argv) > 2 else "cached_content"

    if not csv_path.exists():
        print(f"[ERROR] CSV file not found: {csv_path}")
        sys.exit(1)

    # Initialize rate limiter
    rate_limiter = RateLimiter(max_ingests=5, window_minutes=15)

    print(f"[OK] Using Qdrant collection: {collection_name}\n")

    await interactive_repl(csv_path, collection_name, rate_limiter)


if __name__ == "__main__":
    asyncio.run(main())
