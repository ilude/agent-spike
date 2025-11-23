"""Mark existing archives as processed in Neo4j.

Since we already have transcripts and metadata in JSON archives,
this script marks those videos as having completed those steps
without re-fetching from YouTube.

Usage:
    python -m compose.services.pipeline.mark_processed
"""

import json
from datetime import datetime
from pathlib import Path

from compose.lib.env_loader import load_root_env


def log(msg: str):
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"[{timestamp}] {msg}", flush=True)


def mark_archives_as_processed(base_dir: Path = None, batch_size: int = 100) -> dict:
    """Mark videos with existing archives as processed.

    Reads each archive and marks the appropriate steps based on what data exists:
    - Has transcript -> mark fetch_transcript, archive_raw as done
    - Has youtube_metadata -> mark fetch_metadata as done

    Args:
        base_dir: Archive directory
        batch_size: Progress reporting interval

    Returns:
        Summary dict
    """
    from compose.services.graph import execute_query, execute_write, close_driver
    from compose.services.pipeline import get_step

    if base_dir is None:
        this_file = Path(__file__).resolve()
        base_dir = this_file.parent.parent.parent / "data" / "archive" / "youtube"

    # Get current step versions
    transcript_step = get_step("fetch_transcript")
    metadata_step = get_step("fetch_metadata")
    archive_step = get_step("archive_raw")

    transcript_version = transcript_step[1].version_hash if transcript_step else "unknown"
    metadata_version = metadata_step[1].version_hash if metadata_step else "unknown"
    archive_version = archive_step[1].version_hash if archive_step else "unknown"

    log(f"Marking archives as processed from: {base_dir}")
    log(f"Step versions: transcript={transcript_version}, metadata={metadata_version}, archive={archive_version}")

    summary = {
        "total": 0,
        "marked_transcript": 0,
        "marked_metadata": 0,
        "marked_archive": 0,
        "errors": 0,
    }

    archives = list(base_dir.rglob("*.json"))
    summary["total"] = len(archives)
    log(f"Found {len(archives)} archive files")

    for i, file_path in enumerate(archives, 1):
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                archive = json.load(f)

            video_id = archive.get("video_id")
            if not video_id:
                continue

            # Build pipeline_state based on what exists in archive
            pipeline_state = {}

            if archive.get("raw_transcript"):
                pipeline_state["fetch_transcript"] = transcript_version
                pipeline_state["archive_raw"] = archive_version
                summary["marked_transcript"] += 1
                summary["marked_archive"] += 1

            if archive.get("youtube_metadata"):
                pipeline_state["fetch_metadata"] = metadata_version
                summary["marked_metadata"] += 1

            if pipeline_state:
                # Update Neo4j
                query = """
                MATCH (v:Video {video_id: $video_id})
                SET v.pipeline_state = $pipeline_state_json,
                    v.updated_at = datetime()
                RETURN v
                """
                execute_write(query, {
                    "video_id": video_id,
                    "pipeline_state_json": json.dumps(pipeline_state),
                })

        except Exception as e:
            summary["errors"] += 1
            if summary["errors"] <= 5:
                log(f"Error processing {file_path}: {e}")

        if i % batch_size == 0:
            log(f"Progress: {i}/{len(archives)}")

    log(f"\nComplete!")
    log(f"  Total archives: {summary['total']}")
    log(f"  Marked fetch_transcript: {summary['marked_transcript']}")
    log(f"  Marked fetch_metadata: {summary['marked_metadata']}")
    log(f"  Marked archive_raw: {summary['marked_archive']}")
    log(f"  Errors: {summary['errors']}")

    close_driver()
    return summary


if __name__ == "__main__":
    load_root_env()
    mark_archives_as_processed()
