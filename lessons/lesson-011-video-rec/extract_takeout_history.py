#!/usr/bin/env python
"""Extract YouTube video IDs from Google Takeout watch history.

Parses watch-history.json from Takeout zip.
Samples ~50 random videos from history older than 3 months for diversity.
"""

import json
import random
import re
import zipfile
from datetime import datetime, timedelta
from pathlib import Path

# Takeout location
TAKEOUT_ZIP = Path(__file__).parent.parent.parent / "compose/data/google-takeout-20250723T204430Z-1-001.zip"
WATCH_HISTORY_PATH = "Takeout/YouTube and YouTube Music/history/watch-history.json"
OUTPUT_DIR = Path(__file__).parent / "output"

# How many historical videos to sample
HISTORICAL_SAMPLE_SIZE = 50


def extract_video_id(url: str) -> str | None:
    """Extract YouTube video ID from URL."""
    # Handle escaped equals sign in JSON
    url = url.replace(r"\u003d", "=")

    patterns = [
        r"youtube\.com/watch\?v=([a-zA-Z0-9_-]{11})",
        r"youtu\.be/([a-zA-Z0-9_-]{11})",
        r"youtube\.com/shorts/([a-zA-Z0-9_-]{11})",
    ]

    for pattern in patterns:
        match = re.search(pattern, url)
        if match:
            return match.group(1)
    return None


def parse_takeout_watch_history(zip_path: Path) -> list[dict]:
    """Parse watch-history.json from Takeout zip.

    Returns:
        List of dicts with video_id, title, channel, watch_time
    """
    results = []

    with zipfile.ZipFile(zip_path, "r") as zf:
        with zf.open(WATCH_HISTORY_PATH) as f:
            data = json.load(f)

    for entry in data:
        # Skip non-YouTube entries
        if entry.get("header") != "YouTube":
            continue

        # Skip entries without URL (e.g., ads, removed videos)
        title_url = entry.get("titleUrl")
        if not title_url:
            continue

        video_id = extract_video_id(title_url)
        if not video_id:
            continue

        # Extract channel info
        channel_name = None
        channel_url = None
        if entry.get("subtitles"):
            channel_name = entry["subtitles"][0].get("name")
            channel_url = entry["subtitles"][0].get("url")

        # Parse timestamp
        watch_time = entry.get("time")

        results.append({
            "video_id": video_id,
            "title": entry.get("title", "").replace("Watched ", ""),
            "channel_name": channel_name,
            "channel_url": channel_url,
            "watch_time": watch_time,
            "source": "takeout",
        })

    return results


def split_by_recency(videos: list[dict], months_back: int = 3) -> tuple[list[dict], list[dict]]:
    """Split videos into recent (last N months) and historical.

    Args:
        videos: List of video dicts with watch_time
        months_back: Cutoff in months

    Returns:
        Tuple of (recent_videos, historical_videos)
    """
    cutoff = datetime.now() - timedelta(days=months_back * 30)

    recent = []
    historical = []

    for v in videos:
        try:
            watch_dt = datetime.fromisoformat(v["watch_time"].replace("Z", "+00:00"))
            # Make naive for comparison
            watch_dt = watch_dt.replace(tzinfo=None)

            if watch_dt >= cutoff:
                recent.append(v)
            else:
                historical.append(v)
        except (ValueError, TypeError):
            # If we can't parse the date, treat as historical
            historical.append(v)

    return recent, historical


def dedupe_by_video_id(videos: list[dict]) -> list[dict]:
    """Deduplicate videos, keeping the most recent watch."""
    seen = {}
    for v in videos:
        vid = v["video_id"]
        if vid not in seen:
            seen[vid] = v
        else:
            # Keep the more recent one
            if v.get("watch_time", "") > seen[vid].get("watch_time", ""):
                seen[vid] = v
    return list(seen.values())


def main():
    """Extract YouTube video IDs from Google Takeout."""
    OUTPUT_DIR.mkdir(exist_ok=True)

    if not TAKEOUT_ZIP.exists():
        print(f"Takeout zip not found: {TAKEOUT_ZIP}")
        return

    print(f"Parsing: {TAKEOUT_ZIP.name}")
    all_videos = parse_takeout_watch_history(TAKEOUT_ZIP)
    print(f"Total watch history entries: {len(all_videos)}")

    # Deduplicate
    unique_videos = dedupe_by_video_id(all_videos)
    print(f"Unique videos: {len(unique_videos)}")

    # Split by recency
    recent, historical = split_by_recency(unique_videos, months_back=3)
    print(f"Recent (last 3 months): {len(recent)}")
    print(f"Historical (older): {len(historical)}")

    # Note: Takeout is from July 2025, so "recent" relative to export date
    # For our spike, we'll use ALL Takeout data as historical since it predates
    # the Brave history window (Aug-Nov 2025)

    # Sample historical videos for diversity
    if len(historical) > HISTORICAL_SAMPLE_SIZE:
        sampled = random.sample(historical, HISTORICAL_SAMPLE_SIZE)
        print(f"Sampled {HISTORICAL_SAMPLE_SIZE} historical videos for diversity")
    else:
        sampled = historical
        print(f"Using all {len(historical)} historical videos")

    # Combine: all recent from Takeout + sampled historical
    # But since Takeout predates our Brave window, treat all as supplementary
    output_videos = unique_videos  # Use all for now, merge script will handle dedup

    # Save output
    output_file = OUTPUT_DIR / "takeout_videos.json"
    with open(output_file, "w") as f:
        json.dump({
            "extracted_at": datetime.now().isoformat(),
            "takeout_date": "2025-07-23",
            "total_videos": len(output_videos),
            "historical_sample_size": HISTORICAL_SAMPLE_SIZE,
            "videos": output_videos,
        }, f, indent=2)

    print(f"\nSaved to: {output_file}")

    # Also save just the historical sample separately
    sample_file = OUTPUT_DIR / "takeout_historical_sample.json"
    with open(sample_file, "w") as f:
        json.dump({
            "extracted_at": datetime.now().isoformat(),
            "sample_size": len(sampled),
            "videos": sampled,
        }, f, indent=2)

    print(f"Historical sample saved to: {sample_file}")

    # Show sample
    if output_videos:
        print("\nSample videos:")
        for v in output_videos[:5]:
            title = v.get("title", "Unknown")[:50]
            print(f"  {v['video_id']}: {title}...")


if __name__ == "__main__":
    main()
