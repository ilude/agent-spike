"""Migration script to import existing archives to Neo4j.

Reads all JSON archives from compose/data/archive/youtube/ and creates
Video nodes in Neo4j. Does NOT re-run the pipeline - just creates graph
nodes for existing data.

Usage:
    python -m compose.services.pipeline.migrate
"""

import json
import os
from datetime import datetime
from pathlib import Path
from typing import Generator

from compose.lib.env_loader import load_root_env


def find_archives(base_dir: Path) -> Generator[Path, None, None]:
    """Find all JSON archive files."""
    for json_file in base_dir.rglob("*.json"):
        yield json_file


def parse_archive(file_path: Path) -> dict:
    """Parse a JSON archive file."""
    with open(file_path, "r", encoding="utf-8") as f:
        return json.load(f)


def migrate_archive_to_neo4j(archive: dict, file_path: Path) -> bool:
    """Migrate a single archive to Neo4j.

    Creates Video node with basic metadata. Pipeline state is
    initialized to empty - backfill will process missing steps.
    """
    from compose.services.graph import (
        upsert_video,
        link_video_to_channel,
        VideoNode,
    )

    try:
        video_id = archive.get("video_id")
        if not video_id:
            return False

        # Extract metadata
        youtube_meta = archive.get("youtube_metadata", {})
        import_meta = archive.get("import_metadata", {})
        channel_ctx = import_meta.get("channel_context", {})

        # Parse fetched_at date
        fetched_at_str = archive.get("fetched_at")
        if fetched_at_str:
            try:
                fetched_at = datetime.fromisoformat(fetched_at_str.replace("Z", "+00:00"))
            except ValueError:
                fetched_at = datetime.now()
        else:
            fetched_at = datetime.now()

        # Parse published_at date
        published_at = None
        published_str = youtube_meta.get("published_at")
        if published_str:
            try:
                published_at = datetime.fromisoformat(published_str.replace("Z", "+00:00"))
            except ValueError:
                pass

        # Create video node - pipeline_state empty since we haven't run pipeline
        video = VideoNode(
            video_id=video_id,
            url=archive.get("url", f"https://youtube.com/watch?v={video_id}"),
            fetched_at=fetched_at,
            title=youtube_meta.get("title"),
            channel_id=youtube_meta.get("channel_id") or channel_ctx.get("channel_id"),
            channel_name=youtube_meta.get("channel_title") or channel_ctx.get("channel_name"),
            duration_seconds=youtube_meta.get("duration_seconds"),
            view_count=youtube_meta.get("view_count"),
            published_at=published_at,
            source_type=import_meta.get("source_type"),
            import_method=import_meta.get("import_method"),
            recommendation_weight=import_meta.get("recommendation_weight", 1.0),
            pipeline_state={},  # Empty - needs backfill
        )

        upsert_video(video)

        # Link to channel if available
        channel_id = video.channel_id
        channel_name = video.channel_name
        if channel_id and channel_name:
            link_video_to_channel(video_id, channel_id, channel_name)

        return True

    except Exception as e:
        print(f"Error migrating {file_path}: {e}")
        return False


def run_migration(base_dir: Path = None, batch_size: int = 100) -> dict:
    """Run full migration of archives to Neo4j.

    Args:
        base_dir: Archive base directory
        batch_size: Print progress every N videos

    Returns:
        Summary dict with counts
    """
    from compose.services.graph import init_schema, get_video_count, close_driver

    if base_dir is None:
        # Find compose/data/archive/youtube
        this_file = Path(__file__).resolve()
        base_dir = this_file.parent.parent.parent / "data" / "archive" / "youtube"

    print(f"Migrating archives from: {base_dir}")
    print("Initializing Neo4j schema...")
    init_schema()

    initial_count = get_video_count()
    print(f"Current video count in Neo4j: {initial_count}")

    summary = {
        "total_files": 0,
        "migrated": 0,
        "failed": 0,
        "skipped": 0,
    }

    archives = list(find_archives(base_dir))
    summary["total_files"] = len(archives)
    print(f"Found {len(archives)} archive files to process")

    for i, file_path in enumerate(archives, 1):
        try:
            archive = parse_archive(file_path)
            if migrate_archive_to_neo4j(archive, file_path):
                summary["migrated"] += 1
            else:
                summary["skipped"] += 1
        except Exception as e:
            print(f"Failed to parse {file_path}: {e}")
            summary["failed"] += 1

        if i % batch_size == 0:
            print(f"Progress: {i}/{len(archives)} ({summary['migrated']} migrated)")

    final_count = get_video_count()
    print(f"\nMigration complete!")
    print(f"  Files processed: {summary['total_files']}")
    print(f"  Migrated: {summary['migrated']}")
    print(f"  Skipped: {summary['skipped']}")
    print(f"  Failed: {summary['failed']}")
    print(f"  Neo4j videos: {initial_count} -> {final_count}")

    close_driver()
    return summary


if __name__ == "__main__":
    load_root_env()
    run_migration()
