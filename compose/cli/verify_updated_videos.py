#!/usr/bin/env python3
"""Verify specific videos have structured metadata."""

import sys
from pathlib import Path

# Setup script environment
sys.path.insert(0, str(Path(__file__).parent))
from compose.cli.base import setup_script_environment
setup_script_environment()

from compose.services.cache import create_qdrant_cache


def verify_videos(video_ids: list[str]):
    """Check if videos have structured metadata."""
    cache = create_qdrant_cache()

    for vid in video_ids:
        data = cache.get(f"youtube:video:{vid}")
        if data and "metadata" in data:
            meta = data["metadata"]
            has_structured = "subject_matter" in meta or "entities" in meta
            status = "STRUCTURED" if has_structured else "OLD FORMAT"
            print(f"{vid}: {status}")
            if has_structured and "subject_matter" in meta:
                print(f"  Subject: {meta['subject_matter'][:3]}")
        else:
            print(f"{vid}: NOT FOUND or NO METADATA")


if __name__ == "__main__":
    # Test the 3 videos from our test run
    test_videos = ["-BJ11YziNwY", "-bugLOJjaow", "-hK4Qt8B9Fg"]
    verify_videos(test_videos)
