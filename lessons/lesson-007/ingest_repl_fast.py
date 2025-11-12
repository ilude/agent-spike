"""Fast REPL with background batch CSV processing (no rate limiting).

Features:
- Background task processes entire CSV on startup (with Webshare proxy)
- Manual URL input with instant processing
- No rate limiting (Webshare proxy handles it)
- Auto-append URLs to CSV for batch processing
"""

import sys
from pathlib import Path

# Bootstrap: Add project root to path so we can import lessons.lesson_base
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from lessons.lesson_base import setup_lesson_environment

project_root = setup_lesson_environment(lessons=["lesson-001"])

import asyncio
import csv
from datetime import datetime

from youtube_agent.tools import get_transcript, extract_video_id
from youtube_agent.agent import create_agent
from tools.services.cache import create_qdrant_cache
from tools.services.archive import create_local_archive_writer


async def ingest_video(url: str, collection_name: str, archive_writer) -> tuple[bool, str]:
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

    Returns:
        Tuple of (success: bool, message: str)
    """
    cache = None
    try:
        cache = create_qdrant_cache(collection_name=collection_name)

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
        archive_writer.archive_youtube_video(
            video_id=video_id,
            url=url,
            transcript=transcript,
            metadata={"source": "youtube-transcript-api"}
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
        }

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


async def background_csv_processor(
    csv_path: Path,
    collection_name: str,
    archive_writer,
    stop_event: asyncio.Event,
    progress_callback=None,
):
    """Background task to process entire CSV without rate limiting.

    Args:
        csv_path: Path to CSV file
        collection_name: Qdrant collection name
        archive_writer: Archive service
        stop_event: Event to signal stop
        progress_callback: Optional callback(current, total) for progress updates
    """
    print(f"[PROCESSOR] Starting CSV batch processing: {csv_path}")

    try:
        # Read CSV
        if not csv_path.exists():
            print(f"[ERROR] CSV not found: {csv_path}")
            return

        with open(csv_path, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            videos = list(reader)

        total_videos = len(videos)
        print(f"[PROCESSOR] Found {total_videos} videos in CSV")

        # Find unprocessed videos
        unprocessed = []
        cache = create_qdrant_cache(collection_name=collection_name)
        try:
            for video in videos:
                if stop_event.is_set():
                    break

                url = video.get('url', '').strip()
                if not url:
                    continue

                try:
                    video_id = extract_video_id(url)
                    cache_key = f"youtube:video:{video_id}"
                    if not cache.exists(cache_key):
                        unprocessed.append(video)
                except:
                    continue
        finally:
            cache.close()

        total_unprocessed = len(unprocessed)
        print(f"[PROCESSOR] {total_unprocessed} videos need processing")
        print(f"[PROCESSOR] Starting batch ingestion (no rate limiting)...\n")

        # Process all unprocessed videos
        processed = 0
        skipped = 0
        errors = 0

        for i, video in enumerate(unprocessed, 1):
            if stop_event.is_set():
                print("[PROCESSOR] Stopped by user")
                break

            url = video['url']
            title = video.get('title', 'N/A')[:60]

            print(f"\n[{i}/{total_unprocessed}] Processing:")
            print(f"  Title: {title}")
            print(f"  URL: {url}")

            success, message = await ingest_video(url, collection_name, archive_writer)

            if "SKIPPED" in message:
                skipped += 1
            elif success:
                processed += 1
            else:
                errors += 1

            print(f"  {message}")

            # Progress callback
            if progress_callback:
                progress_callback(i, total_unprocessed)

            # Small delay to avoid hammering the API (even with proxy)
            await asyncio.sleep(1)

        print(f"\n[PROCESSOR] Batch processing complete!")
        print(f"  Processed: {processed}")
        print(f"  Skipped: {skipped}")
        print(f"  Errors: {errors}")
        print(f"  Total: {total_unprocessed}\n")

    except Exception as e:
        print(f"[PROCESSOR ERROR] {e}")
        import traceback
        traceback.print_exc()


def append_url_to_csv(csv_path: Path, url: str):
    """Append URL to end of CSV.

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

        # Create new row
        new_row = {field: '' for field in fieldnames}
        new_row['url'] = url
        new_row['title'] = '[Manual addition - pending metadata]'

        # Append to end
        with open(csv_path, 'w', encoding='utf-8', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(existing_rows)
            writer.writerow(new_row)

        return True
    except Exception as e:
        print(f"[ERROR] Failed to append to CSV: {e}")
        return False


async def interactive_repl(
    csv_path: Path,
    collection_name: str,
    archive_writer,
):
    """Run interactive REPL while background processor runs.

    Args:
        csv_path: Path to CSV file for background processing
        collection_name: Qdrant collection name
        archive_writer: Archive service
    """
    print("=" * 80)
    print("Fast YouTube Video Ingestion REPL (No Rate Limiting)")
    print("=" * 80)
    print(f"Collection: {collection_name}")
    print(f"CSV File: {csv_path}")
    print(f"Proxy: Webshare (configured via .env)")
    print()
    print("Features:")
    print("  - Background batch processor: Entire CSV processed on startup")
    print("  - Manual ingestion: Instant processing (no rate limit)")
    print("  - Archive-first: All expensive data saved before caching")
    print()
    print("Commands:")
    print("  - Paste any YouTube URL (no quotes needed) - instant processing")
    print("  - 'list' - Show cached videos")
    print("  - 'count' - Show total cached videos")
    print("  - 'quit' or 'exit' - Exit the REPL")
    print("  - 'help' - Show this help message")
    print("=" * 80)
    print()

    # Start background processor
    stop_event = asyncio.Event()
    processor_task = asyncio.create_task(
        background_csv_processor(csv_path, collection_name, archive_writer, stop_event)
    )

    try:
        while True:
            try:
                # Get input
                user_input = await asyncio.get_event_loop().run_in_executor(
                    None, input, ">> "
                )
                user_input = user_input.strip()

                if not user_input:
                    continue

                # Handle commands
                if user_input.lower() in ['quit', 'exit', 'q']:
                    print("\nStopping background processor...")
                    stop_event.set()
                    await processor_task
                    print("Goodbye!")
                    break

                elif user_input.lower() == 'help':
                    print("\nCommands:")
                    print("  - Paste any YouTube URL - instant processing")
                    print("  - 'list' - Show cached videos")
                    print("  - 'count' - Show total cached videos")
                    print("  - 'quit' or 'exit' - Exit")
                    print()

                elif user_input.lower() == 'list':
                    print("\nFetching cached videos...")
                    cache = create_qdrant_cache(collection_name=collection_name)
                    try:
                        videos = cache.filter({"type": "youtube_video"}, limit=100)
                        if videos:
                            print(f"\nFound {len(videos)} cached videos (showing first 20):")
                            for i, video in enumerate(videos[:20], 1):
                                video_id = video.get('video_id', 'N/A')
                                tags = video.get('tags', 'N/A')[:50]
                                print(f"  {i}. {video_id} - {tags}")
                        else:
                            print("\n[INFO] No videos found in cache.")
                    finally:
                        cache.close()
                    print()

                elif user_input.lower() == 'count':
                    cache = create_qdrant_cache(collection_name=collection_name)
                    try:
                        videos = cache.filter({"type": "youtube_video"}, limit=1000)
                        print(f"\nTotal cached videos: {len(videos)}\n")
                    finally:
                        cache.close()

                elif user_input.startswith('http'):
                    # Manual URL ingestion (instant, no rate limit)
                    print(f"\nProcessing: {user_input}")
                    success, message = await ingest_video(user_input, collection_name, archive_writer)

                    if success:
                        print(f"{message}\n")
                    else:
                        print(f"{message}\n")

                else:
                    print(f"[ERROR] Unknown command or invalid URL: {user_input}")
                    print("Type 'help' for available commands.\n")

            except EOFError:
                print("\n\nStopping background processor...")
                stop_event.set()
                await processor_task
                print("Goodbye!")
                break

    except (KeyboardInterrupt, asyncio.CancelledError):
        print("\n\nKeyboard Interrupt Received... Exiting!")
        stop_event.set()
        try:
            await asyncio.wait_for(processor_task, timeout=5.0)
        except asyncio.TimeoutError:
            print("[INFO] Background processor still running, force stopping...")
        print("Goodbye!")

    except Exception as e:
        print(f"\n[ERROR] {e}")
        stop_event.set()
        try:
            await asyncio.wait_for(processor_task, timeout=5.0)
        except:
            pass


async def main():
    """Main entry point."""
    try:
        if len(sys.argv) < 2:
            # Default to Nate Jones CSV
            csv_path = project_root / "projects" / "data" / "queues" / "pending" / "nate_jones_videos.csv"
        else:
            csv_path = Path(sys.argv[1])

        collection_name = sys.argv[2] if len(sys.argv) > 2 else "cached_content"

        if not csv_path.exists():
            print(f"[ERROR] CSV file not found: {csv_path}")
            sys.exit(1)

        # Initialize archive writer (shared across all ingestions)
        archive = create_local_archive_writer()

        print(f"[OK] Using Qdrant collection: {collection_name}")
        print(f"[OK] Using archive: {archive.config.base_dir}\n")

        await interactive_repl(csv_path, collection_name, archive)

    except (KeyboardInterrupt, asyncio.CancelledError):
        print("\n\nKeyboard Interrupt Received... Exiting!")
        sys.exit(0)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        # Clean exit - already handled in main()
        pass
