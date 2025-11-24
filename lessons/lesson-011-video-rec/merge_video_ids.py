#!/usr/bin/env python
"""Merge video IDs from multiple sources and check against archive.

Combines Brave history + Takeout, deduplicates, and splits into:
- videos_ready.json: Already in archive (have transcript)
- videos_to_fetch.json: Need to fetch transcript
"""

import json
import random
from datetime import datetime
from pathlib import Path

OUTPUT_DIR = Path(__file__).parent / "output"
ARCHIVE_DIR = Path(__file__).parent.parent.parent / "compose/data/archive/youtube"

# Target: 3 months recent + 50 historical
HISTORICAL_SAMPLE_SIZE = 50


def load_json(path: Path) -> dict | None:
    """Load JSON file if it exists."""
    if path.exists():
        with open(path) as f:
            return json.load(f)
    return None


def get_archived_video_ids() -> set[str]:
    """Get set of video IDs already in archive."""
    archived = set()

    if not ARCHIVE_DIR.exists():
        return archived

    # Scan all month directories
    for month_dir in ARCHIVE_DIR.iterdir():
        if month_dir.is_dir():
            for json_file in month_dir.glob("*.json"):
                # Video ID is the filename without extension
                video_id = json_file.stem
                archived.add(video_id)

    return archived


def merge_videos(brave_videos: list[dict], takeout_videos: list[dict]) -> list[dict]:
    """Merge videos from multiple sources, keeping most recent per video_id."""
    all_videos = {}

    for v in brave_videos + takeout_videos:
        vid = v["video_id"]
        if vid not in all_videos:
            all_videos[vid] = v
        else:
            # Prefer the one with more metadata or more recent
            existing = all_videos[vid]
            # Prefer brave (more recent) over takeout
            if v.get("source") == "brave":
                all_videos[vid] = v

    return list(all_videos.values())


def main():
    """Merge video sources and check archive."""
    OUTPUT_DIR.mkdir(exist_ok=True)

    # Load extracted videos
    brave_data = load_json(OUTPUT_DIR / "brave_videos.json")
    takeout_data = load_json(OUTPUT_DIR / "takeout_videos.json")
    takeout_sample = load_json(OUTPUT_DIR / "takeout_historical_sample.json")

    brave_videos = brave_data.get("videos", []) if brave_data else []
    takeout_videos = takeout_sample.get("videos", []) if takeout_sample else []

    print(f"Brave videos: {len(brave_videos)}")
    print(f"Takeout sample: {len(takeout_videos)}")

    if not brave_videos and not takeout_videos:
        print("\nNo videos found! Run extract scripts first:")
        print("  uv run python extract_brave_history.py")
        print("  uv run python extract_takeout_history.py")
        return

    # Merge
    merged = merge_videos(brave_videos, takeout_videos)
    print(f"\nMerged unique videos: {len(merged)}")

    # Check archive
    archived_ids = get_archived_video_ids()
    print(f"Videos already in archive: {len(archived_ids)}")

    # Split into ready vs needs fetch
    ready = []
    to_fetch = []

    for v in merged:
        if v["video_id"] in archived_ids:
            ready.append(v)
        else:
            to_fetch.append(v)

    print(f"\nReady (have transcript): {len(ready)}")
    print(f"Need to fetch: {len(to_fetch)}")

    # If we have too few ready videos, we might want to limit fetch scope
    # For the spike, let's cap at a reasonable number
    MAX_TO_FETCH = 200

    if len(to_fetch) > MAX_TO_FETCH:
        print(f"\nLimiting fetch to {MAX_TO_FETCH} videos to avoid rate limiting")
        # Prefer brave (recent) over takeout
        brave_to_fetch = [v for v in to_fetch if v.get("source") == "brave"]
        takeout_to_fetch = [v for v in to_fetch if v.get("source") == "takeout"]

        # Take all brave, fill rest with takeout
        if len(brave_to_fetch) >= MAX_TO_FETCH:
            to_fetch = brave_to_fetch[:MAX_TO_FETCH]
        else:
            remaining = MAX_TO_FETCH - len(brave_to_fetch)
            to_fetch = brave_to_fetch + takeout_to_fetch[:remaining]

        print(f"Limited to: {len(to_fetch)} videos")

    # Save outputs
    ready_file = OUTPUT_DIR / "videos_ready.json"
    with open(ready_file, "w") as f:
        json.dump({
            "generated_at": datetime.now().isoformat(),
            "count": len(ready),
            "videos": ready,
        }, f, indent=2)
    print(f"\nSaved ready videos to: {ready_file}")

    fetch_file = OUTPUT_DIR / "videos_to_fetch.json"
    with open(fetch_file, "w") as f:
        json.dump({
            "generated_at": datetime.now().isoformat(),
            "count": len(to_fetch),
            "videos": to_fetch,
        }, f, indent=2)
    print(f"Saved to-fetch list to: {fetch_file}")

    # Summary
    print("\n" + "=" * 50)
    print("SUMMARY")
    print("=" * 50)
    print(f"Total videos for clustering: {len(ready) + len(to_fetch)}")
    print(f"  - Ready now: {len(ready)}")
    print(f"  - Need transcript fetch: {len(to_fetch)}")

    if len(ready) >= 50:
        print("\nYou can proceed with clustering using ready videos!")
        print("Run: uv run python cluster_personas.py --ready-only")
    else:
        print("\nRecommendation: Fetch missing transcripts first")
        print("Run: uv run python fetch_missing_transcripts.py")


if __name__ == "__main__":
    main()
