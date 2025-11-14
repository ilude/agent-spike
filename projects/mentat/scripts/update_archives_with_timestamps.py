"""Update existing video archives with timed transcripts.

Reads all archived videos, fetches timed transcripts, and updates the archive files.
"""

import json
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(project_root))

from tools.services.youtube import YouTubeTranscriptService

# Configuration
ARCHIVE_DIR = project_root / "projects" / "data" / "archive" / "youtube" / "2025-11"


def update_archives():
    """Update all archives with timed transcripts."""
    print(f"Updating archives in {ARCHIVE_DIR}")

    # Get all JSON files
    json_files = list(ARCHIVE_DIR.glob("*.json"))
    print(f"Found {len(json_files)} video archives")

    transcript_service = YouTubeTranscriptService()
    success_count = 0
    skip_count = 0
    error_count = 0

    for i, json_file in enumerate(json_files, 1):
        try:
            # Load archive
            with open(json_file, "r", encoding="utf-8") as f:
                data = json.load(f)

            video_id = data["video_id"]

            # Check if already has timed transcript
            if data.get("timed_transcript"):
                print(f"[{i}/{len(json_files)}] SKIP: {video_id} (already has timed transcript)")
                skip_count += 1
                continue

            # Fetch timed transcript
            print(f"[{i}/{len(json_files)}] Fetching timed transcript for {video_id}...", end='', flush=True)

            try:
                timed_transcript = transcript_service.fetch_timed_transcript(video_id)
                data["timed_transcript"] = timed_transcript

                # Write back to file
                with open(json_file, "w", encoding="utf-8") as f:
                    json.dump(data, f, indent=2, default=str)

                print(f" OK ({len(timed_transcript)} segments)")
                success_count += 1

            except Exception as e:
                print(f" ERROR: {e}")
                error_count += 1

        except Exception as e:
            print(f"[{i}/{len(json_files)}] ERROR processing {json_file.name}: {e}")
            error_count += 1

    print(f"\n{'='*50}")
    print(f"Update complete!")
    print(f"  Success: {success_count}")
    print(f"  Skipped: {skip_count}")
    print(f"  Errors: {error_count}")
    print(f"  Total: {len(json_files)}")


if __name__ == "__main__":
    update_archives()
