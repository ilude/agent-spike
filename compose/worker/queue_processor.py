#!/usr/bin/env python
"""Queue processor worker - polls pending/ directory and processes CSV files.

Runs as a headless Docker container, polling for new files.
Uses existing ingest logic for archiving and caching.

Environment variables:
    MINIO_URL: MinIO server URL (default: http://minio:9000)
    MINIO_BUCKET: MinIO bucket name (default: cache)
    POLL_INTERVAL: Seconds between polls (default: 10)
"""

import asyncio
import csv
import json
import os
import shutil
import sys
import time
from datetime import datetime
from pathlib import Path

# Configuration from environment
MINIO_URL = os.getenv("MINIO_URL", "http://minio:9000")
MINIO_BUCKET = os.getenv("MINIO_BUCKET", "cache")
POLL_INTERVAL = int(os.getenv("POLL_INTERVAL", "10"))
WORKER_POOL_SIZE = int(os.getenv("WORKER_POOL_SIZE", "3"))

# Paths - configurable via environment, with sensible defaults for Docker and local dev
def _get_data_base() -> Path:
    """Get base data directory from environment or detect from project structure."""
    env_path = os.getenv("DATA_BASE_DIR")
    if env_path:
        return Path(env_path)
    # Docker default
    if Path("/app/data").exists():
        return Path("/app/data")
    # Local development - find compose/data relative to this file
    this_file = Path(__file__).resolve()
    compose_data = this_file.parent.parent / "data"
    if compose_data.exists():
        return compose_data
    # Fallback to current directory
    return Path.cwd() / "data"

DATA_BASE = _get_data_base()
QUEUE_BASE = DATA_BASE / "queues"
ARCHIVE_BASE = DATA_BASE / "archive"
PENDING_DIR = QUEUE_BASE / "pending"
PROCESSING_DIR = QUEUE_BASE / "processing"
COMPLETED_DIR = QUEUE_BASE / "completed"
PROGRESS_FILE = QUEUE_BASE / ".progress.json"

from compose.services.youtube import get_transcript, extract_video_id, fetch_video_metadata
from compose.services.minio import create_minio_client, ArchiveStorage
from compose.services.archive import create_archive_manager, create_local_archive_writer, ImportMetadata, ChannelContext


def log(msg: str):
    """Log with timestamp."""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"[{timestamp}] {msg}", flush=True)


# Thread-safe progress tracking for multiple workers
_progress_lock = asyncio.Lock()
_active_workers = {}


async def update_progress(worker_id: str, filename: str, completed: int, total: int, started_at: str = None):
    """Update progress file for dashboard monitoring (supports multiple workers)."""
    async with _progress_lock:
        _active_workers[worker_id] = {
            "worker_id": worker_id,
            "filename": filename,
            "completed": completed,
            "total": total,
            "started_at": started_at or datetime.now().isoformat(),
            "updated_at": datetime.now().isoformat(),
        }
        try:
            with open(PROGRESS_FILE, "w") as f:
                json.dump({"workers": list(_active_workers.values())}, f)
        except IOError:
            pass  # Non-critical, don't break processing


async def clear_progress(worker_id: str):
    """Clear worker from progress file when done."""
    async with _progress_lock:
        _active_workers.pop(worker_id, None)
        try:
            if _active_workers:
                with open(PROGRESS_FILE, "w") as f:
                    json.dump({"workers": list(_active_workers.values())}, f)
            elif PROGRESS_FILE.exists():
                PROGRESS_FILE.unlink()
        except IOError:
            pass


async def ingest_video(
    url: str,
    archive_manager,
    storage: ArchiveStorage,
    source_type: str = "single_import",
    channel_id: str = None,
    channel_name: str = None,
) -> tuple[bool, str]:
    """Fetch transcript and metadata, archive, and cache.

    Simplified version - skips LLM tagging for speed.
    Tags can be regenerated later from archive.

    Args:
        source_type: Must be one of: single_import, repl_import, bulk_channel, bulk_multi_channel
    """
    try:
        video_id = extract_video_id(url)
        cache_key = f"youtube:video:{video_id}"

        if storage.client.exists(cache_key):
            return True, f"SKIP: Already cached ({video_id})"

        log(f"  Fetching transcript for {video_id}...")
        transcript = get_transcript(url, cache=None)

        if "ERROR:" in transcript:
            return False, f"ERROR: {transcript}"

        # Fetch YouTube metadata (title, description, etc.)
        log(f"  Fetching YouTube metadata for {video_id}...")
        youtube_metadata, metadata_error = fetch_video_metadata(video_id)
        if metadata_error:
            log(f"  [WARN] Metadata fetch failed: {metadata_error}")
            youtube_metadata = {}

        # Archive transcript - weights per import source type
        weight_map = {
            "single_import": 1.0,
            "repl_import": 1.0,
            "bulk_channel": 0.5,
            "bulk_multi_channel": 0.2,
        }

        import_metadata = ImportMetadata(
            source_type=source_type,
            imported_at=datetime.now(),
            import_method="scheduled",
            channel_context=ChannelContext(
                channel_id=channel_id or youtube_metadata.get("channel_id"),
                channel_name=channel_name or youtube_metadata.get("channel_title"),
                is_bulk_import=True,
            ),
            recommendation_weight=weight_map.get(source_type, 0.8),
        )

        # Archive transcript using manager
        archive_manager.update_transcript(
            video_id=video_id,
            url=url,
            transcript=transcript,
            import_metadata=import_metadata
        )

        # Archive YouTube metadata if available
        if youtube_metadata:
            archive_manager.update_metadata(
                video_id=video_id,
                url=url,
                metadata=youtube_metadata
            )

        # Cache with YouTube metadata
        cache_data = {
            "video_id": video_id,
            "url": url,
            "transcript": transcript,
            "transcript_length": len(transcript),
            "type": "youtube_video",
            "source": "queue_worker",
            "source_type": source_type,
            "recommendation_weight": weight_map.get(source_type, 0.8),
            "imported_at": datetime.now().isoformat(),
            # YouTube metadata for search/filtering
            "youtube_title": youtube_metadata.get("title"),
            "youtube_channel": youtube_metadata.get("channel_title"),
            "youtube_channel_id": youtube_metadata.get("channel_id"),
            "youtube_duration_seconds": youtube_metadata.get("duration_seconds"),
            "youtube_view_count": youtube_metadata.get("view_count"),
            "youtube_published_at": youtube_metadata.get("published_at"),
        }

        if channel_id:
            cache_data["channel_id"] = channel_id

        log(f"  Caching {video_id} ({len(transcript)} chars) to MinIO...")
        storage.client.put_json(cache_key, cache_data)

        title = youtube_metadata.get("title", video_id)[:50]
        return True, f"OK: {title}... ({len(transcript)} chars)"

    except ValueError as e:
        return False, f"ERROR: Invalid URL - {e}"
    except Exception as e:
        return False, f"ERROR: {type(e).__name__}: {e}"


async def process_csv(csv_path: Path, archive_manager, storage: ArchiveStorage, worker_id: str) -> dict:
    """Process all videos from a CSV file."""
    log(f"[{worker_id}] Processing CSV: {csv_path.name}")

    stats = {"processed": 0, "skipped": 0, "errors": 0, "total": 0}
    started_at = datetime.now().isoformat()

    try:
        with open(csv_path, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            videos = list(reader)

        stats["total"] = len(videos)
        log(f"[{worker_id}]   Found {len(videos)} videos")

        # Initialize progress tracking
        await update_progress(worker_id, csv_path.name, 0, len(videos), started_at)

        # Detect source type
        channel_ids = {v.get('channel_id', '').strip() for v in videos if v.get('channel_id')}
        if len(channel_ids) <= 1:
            source_type = "bulk_channel"
        else:
            source_type = "bulk_multi_channel"

        for i, video in enumerate(videos, 1):
            url = video.get('url', '').strip()
            if not url:
                # Update progress even for skipped empty URLs
                await update_progress(worker_id, csv_path.name, i, len(videos), started_at)
                continue

            channel_id = video.get('channel_id', '').strip() or None
            channel_name = video.get('channel_name', '').strip() or None

            success, message = await ingest_video(
                url, archive_manager, storage, source_type, channel_id, channel_name
            )

            if "SKIP" in message:
                stats["skipped"] += 1
            elif success:
                stats["processed"] += 1
            else:
                stats["errors"] += 1
                log(f"[{worker_id}]   [{i}/{len(videos)}] {message}")

            # Update progress after each video
            await update_progress(worker_id, csv_path.name, i, len(videos), started_at)

            # Small delay
            await asyncio.sleep(1)

        log(f"[{worker_id}]   Done: {stats['processed']} processed, {stats['skipped']} skipped, {stats['errors']} errors")

    except Exception as e:
        log(f"[{worker_id}]   CSV Error: {e}")
    finally:
        # Clear this worker's progress when done
        await clear_progress(worker_id)

    return stats


async def process_single_file(csv_file: Path, archive_manager, storage: ArchiveStorage, worker_id: str, semaphore: asyncio.Semaphore):
    """Process a single CSV file with semaphore-controlled concurrency."""
    async with semaphore:
        processing_path = PROCESSING_DIR / csv_file.name
        try:
            # Move to processing
            shutil.move(str(csv_file), str(processing_path))
            log(f"[{worker_id}] Moved {csv_file.name} to processing/")

            # Process
            await process_csv(processing_path, archive_manager, storage, worker_id)

            # Move to completed
            completed_path = COMPLETED_DIR / csv_file.name
            shutil.move(str(processing_path), str(completed_path))
            log(f"[{worker_id}] Moved {csv_file.name} to completed/")

        except Exception as e:
            log(f"[{worker_id}] Error processing {csv_file.name}: {e}")
            # Try to move back to pending on error
            if processing_path.exists():
                try:
                    shutil.move(str(processing_path), str(PENDING_DIR / csv_file.name))
                except Exception:
                    pass


async def poll_and_process():
    """Main polling loop with worker pool."""
    log("=" * 60)
    log("Queue Processor Worker Starting")
    log("=" * 60)
    log(f"MinIO: {MINIO_URL}")
    log(f"Bucket: {MINIO_BUCKET}")
    log(f"Poll interval: {POLL_INTERVAL}s")
    log(f"Worker pool size: {WORKER_POOL_SIZE}")
    log(f"Pending dir: {PENDING_DIR}")
    log(f"Archive dir: {ARCHIVE_BASE}")
    log("=" * 60)

    # Ensure directories exist
    for d in [PENDING_DIR, PROCESSING_DIR, COMPLETED_DIR]:
        d.mkdir(parents=True, exist_ok=True)

    # Recover any interrupted files from processing/
    interrupted_files = list(PROCESSING_DIR.glob("*.csv"))
    if interrupted_files:
        log(f"Recovering {len(interrupted_files)} interrupted file(s) from processing/")
        for f in interrupted_files:
            dest = PENDING_DIR / f.name
            shutil.move(str(f), str(dest))
            log(f"  Moved {f.name} back to pending/")

    # Initialize archive manager with custom base directory
    archive_writer = create_local_archive_writer(base_dir=ARCHIVE_BASE)
    archive_manager = create_archive_manager(writer=archive_writer)

    # Initialize MinIO storage (config loaded from env vars)
    minio_client = create_minio_client()
    storage = ArchiveStorage(minio_client)

    # Semaphore to limit concurrent workers
    semaphore = asyncio.Semaphore(WORKER_POOL_SIZE)
    worker_counter = 0

    while True:
        try:
            # Find CSV files in pending
            csv_files = list(PENDING_DIR.glob("*.csv"))

            if csv_files:
                log(f"Found {len(csv_files)} CSV file(s) to process (pool size: {WORKER_POOL_SIZE})")

                # Create tasks for all pending files (semaphore limits concurrency)
                tasks = []
                for csv_file in csv_files:
                    worker_counter += 1
                    worker_id = f"W{worker_counter:03d}"
                    task = asyncio.create_task(
                        process_single_file(csv_file, archive_manager, storage, worker_id, semaphore)
                    )
                    tasks.append(task)

                # Wait for all tasks to complete
                await asyncio.gather(*tasks)

            # Wait before next poll
            await asyncio.sleep(POLL_INTERVAL)

        except Exception as e:
            log(f"Error in poll loop: {e}")
            await asyncio.sleep(POLL_INTERVAL)


def main():
    """Entry point."""
    try:
        asyncio.run(poll_and_process())
    except KeyboardInterrupt:
        log("Shutting down...")


if __name__ == "__main__":
    main()
