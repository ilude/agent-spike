#!/usr/bin/env python
"""Extract YouTube video IDs from Brave browser history.

Queries SQLite history database for YouTube watch URLs from the last 3 months.
"""

import json
import re
import sqlite3
from datetime import datetime, timedelta
from pathlib import Path

# Brave history location (relative to project root)
BRAVE_HISTORY_DIR = Path(__file__).parent.parent.parent / "compose/data/browser_history/brave_history"
OUTPUT_DIR = Path(__file__).parent / "output"

# YouTube URL patterns
YOUTUBE_PATTERNS = [
    r"youtube\.com/watch\?v=([a-zA-Z0-9_-]{11})",
    r"youtu\.be/([a-zA-Z0-9_-]{11})",
    r"youtube\.com/shorts/([a-zA-Z0-9_-]{11})",
]


def extract_video_id(url: str) -> str | None:
    """Extract YouTube video ID from URL."""
    for pattern in YOUTUBE_PATTERNS:
        match = re.search(pattern, url)
        if match:
            return match.group(1)
    return None


def chrome_time_to_datetime(chrome_time: int) -> datetime:
    """Convert Chrome/Brave timestamp to Python datetime.

    Chrome uses microseconds since 1601-01-01.
    """
    # Chrome epoch is 1601-01-01, Unix epoch is 1970-01-01
    # Difference is 11644473600 seconds
    epoch_diff = 11644473600
    unix_timestamp = (chrome_time / 1_000_000) - epoch_diff
    return datetime.fromtimestamp(unix_timestamp)


def query_brave_history(db_path: Path, months_back: int = 3) -> list[dict]:
    """Query Brave history for YouTube URLs.

    Args:
        db_path: Path to Brave history SQLite database
        months_back: How many months of history to retrieve

    Returns:
        List of dicts with video_id, url, title, visit_time
    """
    cutoff_date = datetime.now() - timedelta(days=months_back * 30)
    # Convert to Chrome timestamp
    chrome_cutoff = int((cutoff_date.timestamp() + 11644473600) * 1_000_000)

    results = []

    try:
        # Connect read-only to avoid locking issues
        conn = sqlite3.connect(f"file:{db_path}?mode=ro", uri=True)
        cursor = conn.cursor()

        # Query URLs table joined with visits for timestamp
        query = """
            SELECT DISTINCT u.url, u.title, v.visit_time
            FROM urls u
            JOIN visits v ON u.id = v.url
            WHERE (u.url LIKE '%youtube.com/watch%'
                   OR u.url LIKE '%youtu.be/%'
                   OR u.url LIKE '%youtube.com/shorts/%')
            AND v.visit_time > ?
            ORDER BY v.visit_time DESC
        """

        cursor.execute(query, (chrome_cutoff,))

        for url, title, visit_time in cursor.fetchall():
            video_id = extract_video_id(url)
            if video_id:
                results.append({
                    "video_id": video_id,
                    "url": url,
                    "title": title,
                    "visit_time": chrome_time_to_datetime(visit_time).isoformat(),
                    "source": "brave",
                })

        conn.close()

    except sqlite3.Error as e:
        print(f"SQLite error querying {db_path}: {e}")

    return results


def dedupe_by_video_id(videos: list[dict]) -> list[dict]:
    """Deduplicate videos, keeping the most recent visit."""
    seen = {}
    for v in videos:
        vid = v["video_id"]
        if vid not in seen:
            seen[vid] = v
        else:
            # Keep the more recent one
            if v["visit_time"] > seen[vid]["visit_time"]:
                seen[vid] = v
    return list(seen.values())


def main():
    """Extract YouTube video IDs from Brave history."""
    OUTPUT_DIR.mkdir(exist_ok=True)

    all_videos = []

    # Find all SQLite files in brave history dir
    if not BRAVE_HISTORY_DIR.exists():
        print(f"Brave history directory not found: {BRAVE_HISTORY_DIR}")
        return

    sqlite_files = list(BRAVE_HISTORY_DIR.glob("*.sqlite"))
    print(f"Found {len(sqlite_files)} Brave history database(s)")

    for db_path in sqlite_files:
        print(f"\nProcessing: {db_path.name}")
        videos = query_brave_history(db_path, months_back=3)
        print(f"  Found {len(videos)} YouTube videos")
        all_videos.extend(videos)

    # Deduplicate across all databases
    unique_videos = dedupe_by_video_id(all_videos)
    print(f"\nTotal unique videos (last 3 months): {len(unique_videos)}")

    # Save output
    output_file = OUTPUT_DIR / "brave_videos.json"
    with open(output_file, "w") as f:
        json.dump({
            "extracted_at": datetime.now().isoformat(),
            "months_back": 3,
            "total_videos": len(unique_videos),
            "videos": unique_videos,
        }, f, indent=2)

    print(f"\nSaved to: {output_file}")

    # Show sample
    if unique_videos:
        print("\nSample videos:")
        for v in unique_videos[:5]:
            print(f"  {v['video_id']}: {v['title'][:60]}...")


if __name__ == "__main__":
    main()
