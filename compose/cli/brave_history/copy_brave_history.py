#!/usr/bin/env python3
"""
Copy Brave browser history to local data/ directory and consolidate.

This script:
1. Copies the Brave history SQLite database to data/brave_history.HOSTNAME.sqlite
2. Consolidates all machine-specific files into data/brave_history.sqlite
3. Removes duplicates based on URL and visit timestamp
4. Only the consolidated brave_history.sqlite is committed (machine files are gitignored)
"""

import csv
import re
import shutil
import sys
import platform
import sqlite3
import subprocess
import json
from pathlib import Path
from datetime import datetime, timezone, timedelta


# Chromium timestamp constants
# Chromium uses microseconds since 1601-01-01 (Windows epoch)
# Unix uses seconds since 1970-01-01
CHROMIUM_EPOCH_OFFSET = 11644473600  # Seconds between 1601 and 1970


def unix_to_chromium(unix_timestamp: int) -> int:
    """Convert Unix timestamp to Chromium timestamp.

    Args:
        unix_timestamp: Seconds since 1970-01-01

    Returns:
        Microseconds since 1601-01-01
    """
    return int((unix_timestamp + CHROMIUM_EPOCH_OFFSET) * 1_000_000)


def datetime_to_chromium(dt: datetime) -> int:
    """Convert datetime to Chromium timestamp.

    Args:
        dt: Datetime object (should be timezone-aware)

    Returns:
        Microseconds since 1601-01-01
    """
    return unix_to_chromium(int(dt.timestamp()))


def chromium_to_datetime(chromium_timestamp: int) -> datetime:
    """Convert Chromium timestamp to datetime.

    Args:
        chromium_timestamp: Microseconds since 1601-01-01

    Returns:
        Datetime object in UTC
    """
    unix_timestamp = (chromium_timestamp / 1_000_000) - CHROMIUM_EPOCH_OFFSET
    return datetime.fromtimestamp(unix_timestamp, tz=timezone.utc)


def extract_video_id(url: str) -> str | None:
    """Extract YouTube video ID from URL.

    Supports formats:
    - https://youtube.com/watch?v=VIDEO_ID
    - https://www.youtube.com/watch?v=VIDEO_ID&other=params
    - https://youtu.be/VIDEO_ID

    Args:
        url: YouTube URL

    Returns:
        11-character video ID, or None if extraction fails
    """
    patterns = [
        r'[?&]v=([0-9A-Za-z_-]{11})',  # Standard watch URLs
        r'youtu\.be/([0-9A-Za-z_-]{11})',  # Short URLs
    ]
    for pattern in patterns:
        match = re.search(pattern, url)
        if match:
            return match.group(1)
    return None


def get_last_sync_timestamp(data_dir: Path) -> int:
    """Get the Chromium timestamp to sync from.

    Strategy:
    1. Try git commit time of brave_history.sqlite (safest)
    2. Fallback to local .sync_state file if no commits
    3. Final fallback: sync last 30 days only

    Args:
        data_dir: Data directory containing brave_history.sqlite

    Returns:
        Chromium timestamp (microseconds since 1601-01-01)
    """
    # Try git first
    try:
        result = subprocess.run(
            ["git", "log", "-1", "--format=%ct", "--", str(data_dir / "brave_history.sqlite")],
            capture_output=True,
            text=True,
            check=True,
            cwd=data_dir.parent  # Run from project root
        )
        if result.stdout.strip():
            unix_time = int(result.stdout.strip())
            print(f"  Using git commit time: {datetime.fromtimestamp(unix_time, tz=timezone.utc)}")
            return unix_to_chromium(unix_time)
    except (subprocess.CalledProcessError, ValueError, FileNotFoundError):
        pass

    # Fallback to sync state file
    sync_state_file = data_dir / ".sync_state"
    if sync_state_file.exists():
        try:
            state = json.loads(sync_state_file.read_text())
            timestamp = state.get("last_sync_chromium_timestamp", 0)
            if timestamp > 0:
                dt = chromium_to_datetime(timestamp)
                print(f"  Using .sync_state time: {dt}")
                return timestamp
        except (json.JSONDecodeError, KeyError):
            pass

    # Final fallback: 30 days ago
    thirty_days_ago = datetime.now(timezone.utc) - timedelta(days=30)
    print(f"  No sync history found, using 30-day fallback: {thirty_days_ago}")
    return datetime_to_chromium(thirty_days_ago)


def update_sync_state(data_dir: Path, youtube_export_timestamp: int | None = None) -> None:
    """Update .sync_state file as backup timestamp source.

    Args:
        data_dir: Data directory to store .sync_state
        youtube_export_timestamp: Optional Chromium timestamp of last YouTube export
    """
    sync_state_file = data_dir / ".sync_state"

    # Load existing state to preserve youtube export timestamp if not provided
    existing_state = {}
    if sync_state_file.exists():
        try:
            existing_state = json.loads(sync_state_file.read_text())
        except json.JSONDecodeError:
            pass

    now = datetime.now(timezone.utc)
    sync_state = {
        "last_sync_chromium_timestamp": datetime_to_chromium(now),
        "last_sync_datetime": now.isoformat(),
        "machine": platform.node(),
    }

    # Preserve or update YouTube export timestamp
    if youtube_export_timestamp is not None:
        sync_state["last_youtube_export_timestamp"] = youtube_export_timestamp
        sync_state["last_youtube_export_datetime"] = chromium_to_datetime(youtube_export_timestamp).isoformat()
    elif "last_youtube_export_timestamp" in existing_state:
        sync_state["last_youtube_export_timestamp"] = existing_state["last_youtube_export_timestamp"]
        sync_state["last_youtube_export_datetime"] = existing_state.get("last_youtube_export_datetime", "")

    sync_state_file.write_text(json.dumps(sync_state, indent=2))


def get_last_youtube_export_timestamp(data_dir: Path) -> int:
    """Get the Chromium timestamp of last YouTube CSV export.

    Args:
        data_dir: Data directory containing .sync_state

    Returns:
        Chromium timestamp, or 0 if never exported
    """
    sync_state_file = data_dir / ".sync_state"
    if sync_state_file.exists():
        try:
            state = json.loads(sync_state_file.read_text())
            return state.get("last_youtube_export_timestamp", 0)
        except json.JSONDecodeError:
            pass
    return 0


def export_youtube_to_csv(data_dir: Path, pending_dir: Path | None = None) -> int:
    """Export new YouTube URLs from consolidated history to a CSV file.

    Queries the consolidated brave_history.sqlite for YouTube watch URLs
    that haven't been exported yet (based on last_youtube_export_timestamp).
    Normalizes URLs to canonical format and dedupes by video ID.

    Args:
        data_dir: Directory containing brave_history.sqlite and .sync_state
        pending_dir: Directory to write CSV (default: compose/data/queues/pending/)

    Returns:
        Number of unique YouTube videos exported
    """
    consolidated_db = data_dir / "brave_history.sqlite"
    if not consolidated_db.exists():
        print("  No consolidated database found, skipping YouTube export")
        return 0

    # Determine pending directory
    if pending_dir is None:
        # Default: compose/data/queues/pending/ relative to brave_history location
        # data_dir is compose/data/queues/brave_history/
        pending_dir = data_dir.parent / "pending"

    pending_dir.mkdir(parents=True, exist_ok=True)

    # Get last export timestamp
    last_export = get_last_youtube_export_timestamp(data_dir)
    if last_export > 0:
        last_export_dt = chromium_to_datetime(last_export)
        print(f"  Last YouTube export: {last_export_dt.strftime('%Y-%m-%d %H:%M:%S')}")
    else:
        print("  First YouTube export (no previous export found)")

    # Query YouTube URLs newer than last export
    conn = sqlite3.connect(consolidated_db)
    cursor = conn.cursor()

    cursor.execute("""
        SELECT u.url, u.title, v.visit_time
        FROM visits v
        JOIN urls u ON v.url = u.id
        WHERE u.url LIKE '%youtube.com/watch%'
          AND v.visit_time > ?
        ORDER BY v.visit_time ASC
    """, (last_export,))

    rows = cursor.fetchall()
    conn.close()

    if not rows:
        print("  No new YouTube URLs to export")
        return 0

    # Find the max visit_time for updating sync state
    max_visit_time = max(row[2] for row in rows)

    # Normalize URLs and dedupe by video ID (keep first occurrence with its title)
    seen_video_ids: dict[str, tuple[str, str, int]] = {}  # video_id -> (url, title, visit_time)
    skipped = 0

    for url, title, visit_time in rows:
        video_id = extract_video_id(url)
        if video_id is None:
            skipped += 1
            continue

        if video_id not in seen_video_ids:
            # Normalize URL to canonical format
            normalized_url = f"https://www.youtube.com/watch?v={video_id}"
            seen_video_ids[video_id] = (normalized_url, title or "", visit_time)

    if skipped > 0:
        print(f"  Skipped {skipped} URLs (couldn't extract video ID)")

    if not seen_video_ids:
        print("  No valid YouTube URLs to export")
        return 0

    # Generate CSV filename: brave_history.HOSTNAME.YYYY-MM-DD.csv
    machine_name = platform.node()
    today = datetime.now().strftime("%Y-%m-%d")
    csv_filename = f"brave_history.{machine_name}.{today}.csv"
    csv_path = pending_dir / csv_filename

    # Write CSV (sorted by visit_time)
    sorted_videos = sorted(seen_video_ids.values(), key=lambda x: x[2])

    with open(csv_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["url", "title", "visit_time"])

        for url, title, visit_time in sorted_videos:
            visit_dt = chromium_to_datetime(visit_time)
            writer.writerow([url, title, visit_dt.isoformat()])

    print(f"  [OK] Exported {len(seen_video_ids)} unique videos to {csv_path.name}")
    print(f"       (deduped from {len(rows)} raw URLs)")

    # Update sync state with new export timestamp
    update_sync_state(data_dir, youtube_export_timestamp=max_visit_time)

    return len(seen_video_ids)


def get_brave_history_path() -> Path:
    """Get the path to the Brave browser history file."""
    if sys.platform == "win32":
        # Windows path
        brave_path = Path.home() / "AppData" / "Local" / "BraveSoftware" / "Brave-Browser" / "User Data" / "Default" / "History"
    elif sys.platform == "darwin":
        # macOS path
        brave_path = Path.home() / "Library" / "Application Support" / "BraveSoftware" / "Brave-Browser" / "Default" / "History"
    elif sys.platform == "linux":
        # Linux path
        brave_path = Path.home() / ".config" / "BraveSoftware" / "Brave-Browser" / "Default" / "History"
    else:
        raise OSError(f"Unsupported operating system: {sys.platform}")

    return brave_path


def copy_brave_history(dest_dir: Path | str = "data") -> None:
    """
    Copy Brave history file to the specified destination directory.
    Files are named using the machine hostname.

    Args:
        dest_dir: Destination directory (default: "data" in current directory)
    """
    dest_dir = Path(dest_dir)
    dest_dir.mkdir(exist_ok=True)

    source = get_brave_history_path()
    machine_name = platform.node()  # Get hostname/machine name
    destination = dest_dir / f"brave_history.{machine_name}.sqlite"

    if not source.exists():
        print(f"Error: Brave history file not found at {source}")
        sys.exit(1)

    try:
        print(f"Copying Brave history...")
        print(f"  From: {source}")
        print(f"  To:   {destination}")

        # Remove existing file if it exists
        if destination.exists():
            destination.unlink()

        # Copy the file
        shutil.copy2(source, destination)

        # Get file info
        size_mb = destination.stat().st_size / (1024 * 1024)
        print(f"[OK] Success! Copied {size_mb:.1f} MB")

    except PermissionError:
        print(f"Error: Permission denied. Make sure Brave browser is closed.")
        sys.exit(1)
    except Exception as e:
        print(f"Error: Failed to copy file: {e}")
        sys.exit(1)


def consolidate_history_files(data_dir: Path) -> None:
    """
    Consolidate all history files (including existing brave_history.sqlite) into a new file.
    Uses brave_history.tmp.sqlite during consolidation, then replaces brave_history.sqlite.
    Removes duplicates based on URL and visit timestamp.
    
    Args:
        data_dir: Directory containing the history files
    """
    # Find all history files including the consolidated one and machine-specific ones
    all_files = list(data_dir.glob("brave_history*.sqlite"))
    # Exclude any existing .tmp file
    all_files = [f for f in all_files if not f.name.endswith(".tmp.sqlite")]
    
    if not all_files:
        print("No history files to consolidate")
        return
    
    temp_path = data_dir / "brave_history.tmp.sqlite"
    final_path = data_dir / "brave_history.sqlite"
    
    # Remove any existing temp file
    if temp_path.exists():
        temp_path.unlink()
    
    print(f"\nConsolidating {len(all_files)} history file(s)...")
    for f in all_files:
        print(f"  - {f.name}")
    
    # Create temporary consolidated database
    temp_conn = sqlite3.connect(temp_path)
    temp_cursor = temp_conn.cursor()
    
    # Get schema from first file
    first_file = all_files[0]
    source_conn = sqlite3.connect(first_file)
    source_cursor = source_conn.cursor()
    
    # Copy schema for main tables
    source_cursor.execute("""
        SELECT sql FROM sqlite_master 
        WHERE type='table' AND name IN ('urls', 'visits')
        ORDER BY name
    """)
    
    for (sql,) in source_cursor.fetchall():
        if sql:
            temp_cursor.execute(sql)
    
    source_conn.close()
    
    # Track statistics
    total_processed = 0
    
    # Process each file
    for history_file in all_files:
        print(f"  Processing: {history_file.name}")
        
        source_conn = sqlite3.connect(history_file)
        source_cursor = source_conn.cursor()
        
        # Insert URLs (ignore duplicates by URL text)
        source_cursor.execute("SELECT id, url, title, visit_count, last_visit_time FROM urls")
        urls = source_cursor.fetchall()
        
        for url_data in urls:
            try:
                temp_cursor.execute("""
                    INSERT OR IGNORE INTO urls (url, title, visit_count, last_visit_time)
                    VALUES (?, ?, ?, ?)
                """, url_data[1:])  # Skip the source id
            except sqlite3.Error:
                pass  # Skip on error
        
        # Get URL ID mappings (old ID -> new ID)
        source_cursor.execute("SELECT id, url FROM urls")
        url_mapping = {}
        for old_id, url in source_cursor.fetchall():
            temp_cursor.execute("SELECT id FROM urls WHERE url = ?", (url,))
            result = temp_cursor.fetchone()
            if result:
                url_mapping[old_id] = result[0]
        
        # Insert visits (ignore duplicates by URL and timestamp)
        source_cursor.execute("SELECT id, url, visit_time, from_visit, transition FROM visits")
        visits = source_cursor.fetchall()
        
        for visit_data in visits:
            old_url_id = visit_data[1]
            if old_url_id in url_mapping:
                new_url_id = url_mapping[old_url_id]
                try:
                    temp_cursor.execute("""
                        INSERT OR IGNORE INTO visits (url, visit_time, from_visit, transition)
                        VALUES (?, ?, ?, ?)
                    """, (new_url_id, visit_data[2], visit_data[3], visit_data[4]))
                    total_processed += temp_cursor.rowcount
                except sqlite3.Error:
                    pass  # Skip on error
        
        source_conn.close()
    
    # Commit and get final statistics
    temp_conn.commit()
    
    temp_cursor.execute("SELECT COUNT(*) FROM urls")
    final_urls = temp_cursor.fetchone()[0]
    
    temp_cursor.execute("SELECT COUNT(*) FROM visits")
    final_visits = temp_cursor.fetchone()[0]
    
    temp_conn.close()
    
    # Replace the old file with the new consolidated one
    if final_path.exists():
        final_path.unlink()
    
    temp_path.rename(final_path)
    
    print(f"\n[OK] Consolidated database created:")
    print(f"  Total URLs: {final_urls:,}")
    print(f"  Total visits: {final_visits:,}")
    print(f"  Saved to: {final_path.name}")


def copy_brave_history_incremental(dest_dir: Path, since_timestamp: int) -> tuple[int, int]:
    """Copy only new history since the given Chromium timestamp.

    Args:
        dest_dir: Destination directory
        since_timestamp: Chromium timestamp (microseconds since 1601-01-01)

    Returns:
        Tuple of (new_visits_count, new_urls_count)
    """
    source = get_brave_history_path()
    machine_name = platform.node()
    temp_dest = dest_dir / f"brave_history.{machine_name}.tmp.sqlite"
    final_dest = dest_dir / f"brave_history.{machine_name}.sqlite"

    if not source.exists():
        print(f"Error: Brave history file not found at {source}")
        return 0, 0

    try:
        # Copy full database first (fast file copy)
        shutil.copy2(source, temp_dest)

        # Connect and filter to only recent visits
        conn = sqlite3.connect(temp_dest)
        cursor = conn.cursor()

        # Delete old visits (keep only new ones)
        cursor.execute("""
            DELETE FROM visits
            WHERE visit_time <= ?
        """, (since_timestamp,))
        deleted_visits = cursor.rowcount

        # Delete URLs that have no remaining visits
        cursor.execute("""
            DELETE FROM urls
            WHERE id NOT IN (SELECT DISTINCT url FROM visits)
        """)
        deleted_urls = cursor.rowcount

        conn.commit()

        # Get stats
        cursor.execute("SELECT COUNT(*) FROM visits")
        new_visits = cursor.fetchone()[0]
        cursor.execute("SELECT COUNT(*) FROM urls")
        new_urls = cursor.fetchone()[0]

        conn.close()

        # Move to final location
        if final_dest.exists():
            final_dest.unlink()
        temp_dest.rename(final_dest)

        return new_visits, new_urls

    except PermissionError:
        print(f"Error: Permission denied. Make sure Brave browser is closed.")
        if temp_dest.exists():
            temp_dest.unlink()
        return 0, 0
    except Exception as e:
        print(f"Error: Failed to copy file: {e}")
        if temp_dest.exists():
            temp_dest.unlink()
        return 0, 0


def consolidate_history_incremental(data_dir: Path, since_timestamp: int) -> int:
    """Consolidate only new history records since timestamp.

    Strategy:
    1. Load existing brave_history.sqlite
    2. Attach new machine-specific databases
    3. INSERT only visits newer than since_timestamp
    4. Deduplicate based on (url, visit_time) composite key

    Args:
        data_dir: Directory containing history files
        since_timestamp: Chromium timestamp to filter from

    Returns:
        Total number of new visits added
    """
    consolidated_db = data_dir / "brave_history.sqlite"
    machine_files = [f for f in data_dir.glob("brave_history.*.sqlite")]

    if not machine_files:
        print("No machine-specific history files to consolidate")
        return 0

    # Work on the consolidated database directly
    conn = sqlite3.connect(consolidated_db)
    cursor = conn.cursor()

    total_new_visits = 0

    for machine_file in machine_files:
        print(f"  Processing: {machine_file.name}")

        try:
            # Attach the machine database
            cursor.execute(f"ATTACH DATABASE '{machine_file}' AS new_data")

            # Insert new URLs (ignore if already exists)
            cursor.execute("""
                INSERT OR IGNORE INTO main.urls (url, title, visit_count, last_visit_time)
                SELECT url, title, visit_count, last_visit_time
                FROM new_data.urls
                WHERE id IN (
                    SELECT DISTINCT url FROM new_data.visits
                    WHERE visit_time > ?
                )
            """, (since_timestamp,))

            # Insert new visits with URL remapping
            # Uses a subquery to map old URL IDs to new ones
            cursor.execute("""
                INSERT OR IGNORE INTO main.visits
                (url, visit_time, from_visit, transition)
                SELECT
                    (SELECT main.urls.id FROM main.urls WHERE main.urls.url = new_data.urls.url) AS url_id,
                    v.visit_time,
                    v.from_visit,
                    v.transition
                FROM new_data.visits v
                JOIN new_data.urls ON v.url = new_data.urls.id
                WHERE v.visit_time > ?
            """, (since_timestamp,))

            new_visits = cursor.rowcount
            total_new_visits += new_visits
            print(f"    Added {new_visits} new visits")

        finally:
            # Always detach, even if queries fail
            try:
                cursor.execute("DETACH DATABASE new_data")
            except sqlite3.OperationalError:
                # Database might not be attached if attach failed
                pass

    conn.commit()
    conn.close()

    return total_new_visits


def safe_incremental_sync(data_dir: Path = Path("data")) -> None:
    """Incremental sync with edge case handling.

    This is the main entry point that handles:
    - First sync (no existing database)
    - Corrupted database (integrity check)
    - Large time gaps (>30 days → full resync)
    - Normal incremental sync

    Args:
        data_dir: Data directory containing history files
    """
    data_dir = Path(data_dir)
    data_dir.mkdir(exist_ok=True)

    consolidated_db = data_dir / "brave_history.sqlite"

    # Safety check: Does consolidated DB exist?
    if not consolidated_db.exists():
        print("No existing database found, performing full sync...")
        copy_brave_history(data_dir)
        consolidate_history_files(data_dir)
        update_sync_state(data_dir)
        print("\n[YouTube Export]")
        export_youtube_to_csv(data_dir)
        return

    # Get last sync timestamp
    print("Determining sync point...")
    last_sync = get_last_sync_timestamp(data_dir)
    since_datetime = chromium_to_datetime(last_sync)
    days_ago = (datetime.now(timezone.utc) - since_datetime).days

    print(f"Last sync: {since_datetime.strftime('%Y-%m-%d %H:%M:%S')} ({days_ago} days ago)")

    # Safety check: If > 30 days, do full resync
    if days_ago > 30:
        print(f"WARNING: Last sync was {days_ago} days ago")
        print("Performing full resync for safety...")
        copy_brave_history(data_dir)
        consolidate_history_files(data_dir)
        update_sync_state(data_dir)
        print("\n[YouTube Export]")
        export_youtube_to_csv(data_dir)
        return

    # Integrity check on consolidated DB
    conn = sqlite3.connect(consolidated_db)
    cursor = conn.cursor()
    try:
        cursor.execute("PRAGMA integrity_check")
        result = cursor.fetchone()[0]
        if result != "ok":
            raise sqlite3.DatabaseError(f"Integrity check failed: {result}")
    except sqlite3.DatabaseError as e:
        print(f"ERROR: Database corrupted: {e}")
        print("Performing full resync...")
        conn.close()
        consolidated_db.unlink()
        copy_brave_history(data_dir)
        consolidate_history_files(data_dir)
        update_sync_state(data_dir)
        print("\n[YouTube Export]")
        export_youtube_to_csv(data_dir)
        return
    finally:
        conn.close()

    # Perform incremental sync
    print("\n[Incremental Sync Mode]")
    print("Copying new history from browser...")
    new_visits, new_urls = copy_brave_history_incremental(data_dir, last_sync)

    if new_visits == 0:
        print(f"  No new history since {since_datetime.strftime('%Y-%m-%d %H:%M:%S')}")
        update_sync_state(data_dir)
        # Still export any un-exported YouTube URLs from existing DB
        print("\n[YouTube Export]")
        export_youtube_to_csv(data_dir)
        return

    print(f"  [OK] Copied {new_visits} new visits across {new_urls} URLs")

    # Consolidate only new records
    print("\nConsolidating new records...")
    total_added = consolidate_history_incremental(data_dir, last_sync)

    # Get final stats
    conn = sqlite3.connect(consolidated_db)
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM urls")
    total_urls = cursor.fetchone()[0]
    cursor.execute("SELECT COUNT(*) FROM visits")
    total_visits = cursor.fetchone()[0]
    conn.close()

    print(f"\n[OK] Incremental sync complete!")
    print(f"  New visits added: {total_added:,}")
    print(f"  Total database: {total_urls:,} URLs, {total_visits:,} visits")

    # Update sync state
    update_sync_state(data_dir)

    # Export new YouTube URLs to CSV for downstream processing
    print("\n[YouTube Export]")
    export_youtube_to_csv(data_dir)


def _build_cli_parser():
    """Build the argparse CLI parser.

    Exposes two modes:
    1. Full sync (default) – copies current Brave history and consolidates all machine files.
    2. Incremental sync – uses `safe_incremental_sync` with timestamp heuristics and integrity checks.

    The destination directory defaults to `compose/data/queues/brave_history` for project-scoped storage.
    """
    import argparse

    parser = argparse.ArgumentParser(description="Brave history synchronization utility")
    parser.add_argument(
        "--incremental",
        action="store_true",
        help="Perform incremental sync (safe heuristic mode)."
    )
    parser.add_argument(
        "--dest",
        type=Path,
        default=Path("data"),
        help="Destination directory for history databases (default: ./data)"
    )
    return parser


def main():  # pragma: no cover - thin CLI wrapper
    parser = _build_cli_parser()
    args = parser.parse_args()

    dest: Path = args.dest

    if args.incremental:
        # Incremental sync with protective logic
        safe_incremental_sync(dest)
    else:
        # Original behavior: copy then consolidate all machine-specific files
        copy_brave_history(dest)
        if dest.exists():
            consolidate_history_files(dest)


if __name__ == "__main__":  # pragma: no cover
    main()
