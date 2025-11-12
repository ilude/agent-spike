#!/usr/bin/env python3
"""Check if all cached videos have the latest structured metadata format."""

import sys
from pathlib import Path

# Setup script environment
sys.path.insert(0, str(Path(__file__).parent))
from script_base import setup_script_environment
setup_script_environment()

from tools.services.cache import create_qdrant_cache


def check_metadata_format():
    """Check metadata format in cached videos."""
    cache = create_qdrant_cache()

    # Get all cached videos
    print("Fetching all cached videos...")
    videos = cache.search(query="", limit=1000)

    if not videos:
        print("No cached videos found.")
        return

    print(f"Found {len(videos)} cached videos.\n")

    # Categorize by metadata format
    structured = []  # Has subject_matter, entities, etc.
    old_tags = []    # Has tags string only
    no_metadata = []  # Missing metadata entirely

    for video in videos:
        video_id = video.get("video_id", "unknown")

        if "metadata" in video:
            meta = video["metadata"]
            # Check for new structured format
            if "subject_matter" in meta or "entities" in meta:
                structured.append(video_id)
            else:
                # Could be old format or incomplete
                old_tags.append(video_id)
        elif "tags" in video:
            # Definitely old format
            old_tags.append(video_id)
        else:
            no_metadata.append(video_id)

    # Print summary
    print("=== Metadata Format Summary ===")
    print(f"Structured metadata: {len(structured)} videos")
    print(f"Old tags format:     {len(old_tags)} videos")
    print(f"No metadata:         {len(no_metadata)} videos")
    print(f"Total:               {len(videos)} videos\n")

    # Show percentage
    if videos:
        pct = (len(structured) / len(videos)) * 100
        print(f"Structured format coverage: {pct:.1f}%\n")

    # Show sample of each category
    if structured:
        print("Sample structured video:")
        sample = next((v for v in videos if v.get("video_id") in structured[:1]), None)
        if sample:
            print(f"  ID: {sample.get('video_id')}")
            if "metadata" in sample:
                meta = sample["metadata"]
                print(f"  Subject: {meta.get('subject_matter', [])[:3]}")
                print(f"  Style: {meta.get('content_style', 'N/A')}")

    if old_tags:
        print("\nSample old format video:")
        sample = next((v for v in videos if v.get("video_id") in old_tags[:1]), None)
        if sample:
            print(f"  ID: {sample.get('video_id')}")
            if "tags" in sample:
                print(f"  Tags: {sample['tags'][:80]}...")
            elif "metadata" in sample:
                print(f"  Metadata keys: {list(sample['metadata'].keys())}")

    if no_metadata:
        print("\nSample video without metadata:")
        sample = next((v for v in videos if v.get("video_id") in no_metadata[:1]), None)
        if sample:
            print(f"  ID: {sample.get('video_id')}")
            print(f"  Keys: {list(sample.keys())}")


if __name__ == "__main__":
    check_metadata_format()
