#!/usr/bin/env python3
"""
Import video watch history from Phase 0 outputs.

Usage:
    uv run python import_history.py
"""

import asyncio
import json
from pathlib import Path

from import_service import VideoImporter, get_db_connection


async def main():
    """Import Brave and Takeout history from Phase 0 outputs."""
    output_dir = Path(__file__).parent / "output"

    # Load video IDs from Phase 0
    brave_file = output_dir / "brave_videos.json"
    takeout_file = output_dir / "takeout_videos.json"

    brave_videos = []
    takeout_videos = []

    if brave_file.exists():
        with open(brave_file) as f:
            data = json.load(f)
            brave_videos = [v["video_id"] for v in data.get("videos", [])]
            print(f"Loaded {len(brave_videos)} videos from Brave history")
    else:
        print(f"Warning: {brave_file} not found")

    if takeout_file.exists():
        with open(takeout_file) as f:
            data = json.load(f)
            takeout_videos = [v["video_id"] for v in data.get("videos", [])]
            print(f"Loaded {len(takeout_videos)} videos from Takeout history")
    else:
        print(f"Warning: {takeout_file} not found")

    # Connect to database
    print("\nConnecting to SurrealDB...")
    db = await get_db_connection()

    importer = VideoImporter(db)

    # Import Brave history
    if brave_videos:
        print(f"\nImporting {len(brave_videos)} videos from Brave...")
        brave_result = await importer.import_video_ids(
            brave_videos, source="brave", signal_type="watched"
        )
        print(f"  New videos: {brave_result.new_videos}")
        print(f"  Existing videos: {brave_result.existing_videos}")
        print(f"  New signals: {brave_result.new_signals}")
        print(f"  Duplicate signals: {brave_result.duplicate_signals}")
        print(f"  Errors: {brave_result.errors}")

    # Import Takeout history
    if takeout_videos:
        print(f"\nImporting {len(takeout_videos)} videos from Takeout...")
        takeout_result = await importer.import_video_ids(
            takeout_videos, source="takeout", signal_type="watched"
        )
        print(f"  New videos: {takeout_result.new_videos}")
        print(f"  Existing videos: {takeout_result.existing_videos}")
        print(f"  New signals: {takeout_result.new_signals}")
        print(f"  Duplicate signals: {takeout_result.duplicate_signals}")
        print(f"  Errors: {takeout_result.errors}")

    # Summary
    total_unique = brave_result.new_videos + takeout_result.new_videos
    total_signals = brave_result.new_signals + takeout_result.new_signals
    total_errors = brave_result.errors + takeout_result.errors

    print("\n=== Import Summary ===")
    print(f"Total unique videos imported: {total_unique}")
    print(f"Total signals created: {total_signals}")
    print(f"Total errors: {total_errors}")
    print("\nPhase 1 complete! Video history imported into SurrealDB.")


if __name__ == "__main__":
    asyncio.run(main())
