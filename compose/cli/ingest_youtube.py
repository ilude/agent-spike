"""Fast REPL with background batch CSV processing (no rate limiting).

Features:
- Background task processes entire CSV on startup (with Webshare proxy)
- Manual URL input with instant processing
- No rate limiting (Webshare proxy handles it)
- Auto-append URLs to CSV for batch processing
"""

import asyncio
import csv
import sys
import shutil
from pathlib import Path
from datetime import datetime

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))
sys.path.insert(0, str(project_root / "lessons" / "lesson-001"))

# Import from centralized services
from compose.services.youtube import get_transcript, extract_video_id
from compose.services.cache import create_qdrant_cache
from compose.services.archive import create_local_archive_writer, ImportMetadata, ChannelContext
from compose.lib.env_loader import load_root_env

# Import agent from lesson (still experimental)
from youtube_agent.agent import create_agent

load_root_env()


async def ingest_video(
    url: str,
    collection_name: str,
    archive_writer,
    source_type: str = "repl_import",
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
        source_type: Import source type (single_import, repl_import, bulk_channel, bulk_multi_channel)
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
            import_method="repl" if source_type == "repl_import" else "cli",
            channel_context=ChannelContext(
                channel_id=channel_id,
                channel_name=channel_name,
                is_bulk_import=source_type.startswith("bulk_"),
            ),
            recommendation_weight=weight_map.get(source_type, 1.0),
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
            "recommendation_weight": weight_map.get(source_type, 1.0),
            "imported_at": datetime.now().isoformat(),
            "is_bulk_import": source_type.startswith("bulk_"),
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


def move_csv_to_processing(csv_path: Path, processing_dir: Path) -> Path:
    """Move CSV from pending to processing directory.

    Args:
        csv_path: Path to CSV in pending directory
        processing_dir: Processing directory path

    Returns:
        Path to CSV in processing directory
    """
    processing_dir.mkdir(parents=True, exist_ok=True)
    dest_path = processing_dir / csv_path.name
    shutil.move(str(csv_path), str(dest_path))
    return dest_path


def move_csv_to_completed(csv_path: Path, completed_dir: Path) -> Path:
    """Move CSV from processing to completed directory.

    Args:
        csv_path: Path to CSV in processing directory
        completed_dir: Completed directory path

    Returns:
        Path to CSV in completed directory
    """
    completed_dir.mkdir(parents=True, exist_ok=True)
    dest_path = completed_dir / csv_path.name
    shutil.move(str(csv_path), str(dest_path))
    return dest_path


async def process_csv_file(
    csv_path: Path,
    collection_name: str,
    archive_writer,
    stop_event: asyncio.Event,
) -> dict:
    """Process all videos from a single CSV file.

    Args:
        csv_path: Path to CSV file
        collection_name: Qdrant collection name
        archive_writer: Archive service
        stop_event: Event to signal stop

    Returns:
        Dict with processing stats: {processed, skipped, errors, total}
    """
    print(f"\n[CSV] Processing: {csv_path.name}")

    try:
        # Read CSV
        if not csv_path.exists():
            print(f"[ERROR] CSV not found: {csv_path}")
            return {"processed": 0, "skipped": 0, "errors": 0, "total": 0}

        with open(csv_path, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            videos = list(reader)

        # Detect import type by analyzing channel_id column
        channel_ids = set()
        for video in videos:
            channel_id = video.get('channel_id', '').strip()
            if channel_id:
                channel_ids.add(channel_id)

        # Determine source type based on channel count
        if len(channel_ids) == 0:
            source_type = "bulk_channel"  # No channel info, assume single channel
            print(f"[CSV] No channel info - assuming bulk_channel")
        elif len(channel_ids) == 1:
            source_type = "bulk_channel"
            print(f"[CSV] Single channel detected - source_type: bulk_channel (weight: 0.5)")
        else:
            source_type = "bulk_multi_channel"
            print(f"[CSV] Multiple channels detected ({len(channel_ids)}) - source_type: bulk_multi_channel (weight: 0.2)")

        total_videos = len(videos)
        print(f"[CSV] Found {total_videos} videos")

        # Find unprocessed videos
        unprocessed = []
        cache = create_qdrant_cache(
            collection_name=collection_name,
            qdrant_url="http://localhost:6335",
            infinity_url="http://localhost:7997"
        )
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
        print(f"[CSV] {total_unprocessed} videos need processing\n")

        # Process all unprocessed videos
        processed = 0
        skipped = 0
        errors = 0

        for i, video in enumerate(unprocessed, 1):
            if stop_event.is_set():
                print("[CSV] Stopped by user")
                break

            url = video['url']
            title = video.get('title', 'N/A')[:60]
            channel_id = video.get('channel_id', '').strip() or None
            channel_name = video.get('channel_name', '').strip() or None

            print(f"[{i}/{total_unprocessed}] {title}")
            print(f"  URL: {url}")

            success, message = await ingest_video(
                url,
                collection_name,
                archive_writer,
                source_type=source_type,
                channel_id=channel_id,
                channel_name=channel_name,
            )

            if "SKIPPED" in message:
                skipped += 1
            elif success:
                processed += 1
            else:
                errors += 1

            print(f"  {message}\n")

            # Small delay to avoid hammering the API (even with proxy)
            await asyncio.sleep(1)

        return {
            "processed": processed,
            "skipped": skipped,
            "errors": errors,
            "total": total_unprocessed,
        }

    except Exception as e:
        print(f"[CSV ERROR] {e}")
        import traceback
        traceback.print_exc()
        return {"processed": 0, "skipped": 0, "errors": 0, "total": 0}


async def background_queue_processor(
    pending_dir: Path,
    processing_dir: Path,
    completed_dir: Path,
    collection_name: str,
    archive_writer,
    stop_event: asyncio.Event,
):
    """Background task to process all CSVs in pending queue.

    Workflow:
    1. Scan pending/ for all *.csv files
    2. Move each CSV to processing/
    3. Process all videos from CSV
    4. Move completed CSV to completed/

    Args:
        pending_dir: Directory with pending CSV files
        processing_dir: Directory for CSVs being processed
        completed_dir: Directory for completed CSVs
        collection_name: Qdrant collection name
        archive_writer: Archive service
        stop_event: Event to signal stop
    """
    print(f"[QUEUE] Starting queue processor")
    print(f"[QUEUE] Pending: {pending_dir}")
    print(f"[QUEUE] Processing: {processing_dir}")
    print(f"[QUEUE] Completed: {completed_dir}\n")

    try:
        # Find all CSVs in pending directory
        csv_files = list(pending_dir.glob("*.csv"))

        if not csv_files:
            print("[QUEUE] No CSV files found in pending directory")
            return

        print(f"[QUEUE] Found {len(csv_files)} CSV file(s) to process\n")

        total_processed = 0
        total_skipped = 0
        total_errors = 0

        for csv_file in csv_files:
            if stop_event.is_set():
                print("[QUEUE] Stopped by user")
                break

            # Move to processing
            print(f"[QUEUE] Moving {csv_file.name} to processing/")
            processing_path = move_csv_to_processing(csv_file, processing_dir)

            # Process CSV
            stats = await process_csv_file(
                processing_path,
                collection_name,
                archive_writer,
                stop_event,
            )

            total_processed += stats["processed"]
            total_skipped += stats["skipped"]
            total_errors += stats["errors"]

            # Move to completed (even if stopped or errors)
            print(f"[QUEUE] Moving {processing_path.name} to completed/")
            move_csv_to_completed(processing_path, completed_dir)

        print(f"\n[QUEUE] All CSVs processed!")
        print(f"  Total processed: {total_processed}")
        print(f"  Total skipped: {total_skipped}")
        print(f"  Total errors: {total_errors}\n")

    except Exception as e:
        print(f"[QUEUE ERROR] {e}")
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
    queue_dirs: dict,
    collection_name: str,
    archive_writer,
):
    """Run interactive REPL while background queue processor runs.

    Args:
        queue_dirs: Dict with 'pending', 'processing', 'completed' Path objects
        collection_name: Qdrant collection name
        archive_writer: Archive service
    """
    print("=" * 80)
    print("YouTube Video Queue Ingestion REPL (No Rate Limiting)")
    print("=" * 80)
    print(f"Collection: {collection_name}")
    print(f"Queue: {queue_dirs['pending']}")
    print(f"Proxy: Webshare (configured via .env)")
    print()
    print("Features:")
    print("  - Queue-based processing: All CSVs in pending/ directory")
    print("  - Workflow: pending/ -> processing/ -> completed/")
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

    # Start background queue processor
    stop_event = asyncio.Event()
    processor_task = asyncio.create_task(
        background_queue_processor(
            queue_dirs['pending'],
            queue_dirs['processing'],
            queue_dirs['completed'],
            collection_name,
            archive_writer,
            stop_event,
        )
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
                    cache = create_qdrant_cache(
                        collection_name=collection_name,
                        qdrant_url="http://localhost:6335",
                        infinity_url="http://localhost:7997"
                    )
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
                    cache = create_qdrant_cache(
                        collection_name=collection_name,
                        qdrant_url="http://localhost:6335",
                        infinity_url="http://localhost:7997"
                    )
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
        # Setup queue directories
        queue_base = project_root / "compose" / "data" / "queues"
        queue_dirs = {
            'pending': queue_base / "pending",
            'processing': queue_base / "processing",
            'completed': queue_base / "completed",
        }

        # Ensure directories exist
        for dir_path in queue_dirs.values():
            dir_path.mkdir(parents=True, exist_ok=True)

        collection_name = sys.argv[1] if len(sys.argv) > 1 else "cached_content"

        # Initialize archive writer (shared across all ingestions)
        archive = create_local_archive_writer()

        print(f"[OK] Using Qdrant collection: {collection_name}")
        print(f"[OK] Using archive: {archive.config.base_dir}\n")

        await interactive_repl(queue_dirs, collection_name, archive)

    except (KeyboardInterrupt, asyncio.CancelledError):
        print("\n\nKeyboard Interrupt Received... Exiting!")
        sys.exit(0)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        # Clean exit - already handled in main()
        pass
