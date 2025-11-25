#!/usr/bin/env python
"""Populate SurrealDB from MinIO archive files.

Reads all archive JSON files from compose/data/archive/youtube/ and creates
video records in SurrealDB with embeddings generated via Infinity API.

This script is critical - we have 1,695 videos in MinIO archives but only 1 in SurrealDB.

IMPORTANT: Archive files are encrypted with git-crypt. Run 'git-crypt unlock' before
running this script, or it will fail with UnicodeDecodeError.

Usage:
    git-crypt unlock  # Required first!
    uv run python compose/cli/populate_surrealdb_from_archive.py [--dry-run] [--limit N]

Examples:
    # Preview what would be created (first 10)
    uv run python compose/cli/populate_surrealdb_from_archive.py --dry-run --limit 10

    # Populate first 100 videos
    uv run python compose/cli/populate_surrealdb_from_archive.py --limit 100

    # Populate all videos
    uv run python compose/cli/populate_surrealdb_from_archive.py
"""

import asyncio
import json
import logging
import os
import sys
from datetime import datetime
from pathlib import Path
from typing import Optional

# Setup script environment before imports
sys.path.insert(0, str(Path(__file__).parent))
from compose.cli.base import setup_script_environment
setup_script_environment(load_env=True)

import httpx
import typer
from rich.console import Console
from rich.progress import Progress

from compose.services.surrealdb.repository import init_schema, upsert_video
from compose.services.surrealdb.models import VideoRecord

logger = logging.getLogger(__name__)

app = typer.Typer(help="Populate SurrealDB from archive files")
console = Console(force_terminal=True, force_interactive=False, width=120)

# Configuration
ARCHIVE_DIR = Path("compose/data/archive/youtube")
INFINITY_URL = os.getenv("INFINITY_URL", "http://192.168.16.241:7997")
INFINITY_MODEL = os.getenv("INFINITY_MODEL", "Alibaba-NLP/gte-large-en-v1.5")


def find_archive_files(base_dir: Optional[Path] = None) -> list[Path]:
    """Find all archive JSON files in month subdirectories.

    Args:
        base_dir: Base archive directory (defaults to ARCHIVE_DIR)

    Returns:
        Sorted list of archive JSON file paths
    """
    if base_dir is None:
        base_dir = ARCHIVE_DIR

    files = []
    if not base_dir.exists():
        console.print(f"[yellow]Archive directory not found: {base_dir}[/]")
        return files

    # Iterate through month directories (e.g., 2025-11)
    for month_dir in base_dir.iterdir():
        if month_dir.is_dir():
            for json_file in month_dir.glob("*.json"):
                files.append(json_file)

    return sorted(files)


def parse_archive(file_path: Path) -> dict:
    """Parse archive JSON file.

    Args:
        file_path: Path to archive JSON file

    Returns:
        Parsed archive data as dict

    Raises:
        json.JSONDecodeError: If file is not valid JSON
        UnicodeDecodeError: If file is encrypted (git-crypt)
    """
    try:
        with open(file_path, encoding="utf-8") as f:
            data = json.load(f)
            # Quick sanity check - encrypted files won't have video_id
            if "video_id" not in data:
                raise ValueError("Archive missing video_id field")
            return data
    except UnicodeDecodeError as e:
        # File is likely encrypted with git-crypt
        raise UnicodeDecodeError(
            e.encoding,
            e.object,
            e.start,
            e.end,
            f"File appears to be encrypted. Run 'git-crypt unlock' first."
        )


def generate_metadata_text(archive_data: dict, max_chars: int = 8000) -> str:
    """Generate metadata text for embedding from archive data.

    Constructs structured text matching the format used during ingestion:
    "Video ID: {id}\nChannel: {channel}\nTitle: {title}\nSummary: {summary}\nTopics: {topics}"

    Args:
        archive_data: Parsed archive JSON data
        max_chars: Maximum characters to return (for embedding API limits)

    Returns:
        Formatted metadata text
    """
    video_id = archive_data.get("video_id", "")
    youtube_meta = archive_data.get("youtube_metadata", {})
    llm_outputs = archive_data.get("llm_outputs", [])

    # Extract metadata from LLM outputs if available
    metadata_output = {}
    for output in llm_outputs:
        if output.get("output_type") == "metadata":
            metadata_output = output.get("output_value", {})
            break

    # Build structured text
    channel_name = youtube_meta.get("channel_title", "")
    title = youtube_meta.get("title") or metadata_output.get("title", "")
    summary = metadata_output.get("summary", "")
    subjects = metadata_output.get("subject_matter", [])
    topics = " ".join(subjects) if subjects else ""

    text = f"Video ID: {video_id}\nChannel: {channel_name}\nTitle: {title}\nSummary: {summary}\nTopics: {topics}"

    # Truncate if too long
    if len(text) > max_chars:
        text = text[:max_chars]

    return text


def generate_embedding(text: str, infinity_url: str = INFINITY_URL, max_chars: int = 8000) -> list[float]:
    """Generate embedding via Infinity API.

    Args:
        text: Text to embed
        infinity_url: Infinity API URL
        max_chars: Max characters to send (Infinity has token limits)

    Returns:
        Embedding vector as list of floats (1024 dimensions for gte-large)

    Raises:
        Exception: If Infinity API call fails
    """
    # Truncate text if too long
    if len(text) > max_chars:
        text = text[:max_chars]

    response = httpx.post(
        f"{infinity_url}/embeddings",
        json={
            "model": INFINITY_MODEL,
            "input": [text]
        },
        timeout=120.0
    )
    response.raise_for_status()

    data = response.json()
    return data["data"][0]["embedding"]


async def populate_single_video(
    archive_data: dict,
    month: str,
    infinity_url: str = INFINITY_URL,
    dry_run: bool = False,
) -> bool:
    """Populate a single video record in SurrealDB.

    Args:
        archive_data: Parsed archive JSON data
        month: Month directory name (e.g., "2025-11")
        infinity_url: Infinity API URL for embedding generation
        dry_run: If True, don't write to database

    Returns:
        True if successful, False otherwise
    """
    video_id = archive_data.get("video_id")
    if not video_id:
        logger.error("Archive missing video_id")
        return False

    try:
        # 1. Generate metadata text for embedding
        metadata_text = generate_metadata_text(archive_data)

        # 2. Generate embedding via Infinity
        embedding = generate_embedding(metadata_text, infinity_url=infinity_url)

        # 3. Extract metadata from archive
        youtube_meta = archive_data.get("youtube_metadata", {})
        import_meta = archive_data.get("import_metadata", {})
        channel_context = import_meta.get("channel_context", {}) if import_meta else {}

        # Convert fetched_at to datetime
        fetched_at = archive_data.get("fetched_at")
        if isinstance(fetched_at, str):
            try:
                fetched_at = datetime.fromisoformat(fetched_at)
            except (ValueError, TypeError):
                fetched_at = datetime.now()
        elif not isinstance(fetched_at, datetime):
            fetched_at = datetime.now()

        # Convert published_at if needed
        published_at = youtube_meta.get("published_at")
        if published_at and isinstance(published_at, str):
            try:
                published_at = datetime.fromisoformat(published_at)
            except (ValueError, TypeError):
                published_at = None

        # 4. Create VideoRecord
        archive_path = f"archives/youtube/{month}/{video_id}.json"

        video_record = VideoRecord(
            video_id=video_id,
            url=archive_data.get("url", f"https://www.youtube.com/watch?v={video_id}"),
            fetched_at=fetched_at,
            title=youtube_meta.get("title"),
            channel_id=channel_context.get("channel_id") or youtube_meta.get("channel_id"),
            channel_name=channel_context.get("channel_name") or youtube_meta.get("channel_title"),
            duration_seconds=youtube_meta.get("duration_seconds"),
            view_count=youtube_meta.get("view_count"),
            published_at=published_at,
            source_type=import_meta.get("source_type") if import_meta else None,
            import_method=import_meta.get("import_method") if import_meta else None,
            recommendation_weight=import_meta.get("recommendation_weight", 1.0) if import_meta else 1.0,
            embedding=embedding,
            archive_path=archive_path,
            pipeline_state={},
            last_processed_at=datetime.now(),
        )

        # 5. Upsert to SurrealDB (unless dry run)
        if not dry_run:
            await upsert_video(video_record)

        return True

    except Exception as e:
        logger.error(f"Failed to populate video {video_id}: {e}")
        return False


@app.command()
def populate(
    dry_run: bool = typer.Option(
        False,
        "--dry-run",
        help="Show what would be created without doing it",
    ),
    limit: int = typer.Option(0, "--limit", help="Limit number of videos (0 = all)"),
):
    """Populate SurrealDB from archive files."""

    async def run():
        console.print("[bold blue]Finding archive files...[/]")
        files = find_archive_files()
        console.print(f"Found {len(files)} archive files")

        if not files:
            console.print("[yellow]No archive files found![/]")
            return

        if limit > 0:
            files = files[:limit]
            console.print(f"Limited to {limit} files")

        if dry_run:
            console.print("[yellow]DRY RUN - no changes will be made[/]")
            for f in files[:10]:
                try:
                    archive_data = parse_archive(f)
                    title = archive_data.get("youtube_metadata", {}).get("title", "Unknown")
                    console.print(f"  Would create: {f.name:20} -> {title[:50]}")
                except Exception as e:
                    console.print(f"  [red]Error parsing {f.name}: {e}[/]")
            if len(files) > 10:
                console.print(f"  ... and {len(files) - 10} more")
            return

        # Initialize SurrealDB schema
        console.print("[bold blue]Initializing SurrealDB...[/]")
        try:
            await init_schema()
            console.print("[green]OK SurrealDB schema ready[/]")
        except Exception as e:
            console.print(f"[yellow]Schema init note: {e}[/]")

        # Test Infinity connection
        console.print("[bold blue]Testing Infinity API...[/]")
        try:
            test_response = httpx.get(f"{INFINITY_URL}/models", timeout=10)
            test_response.raise_for_status()
            console.print(f"[green]OK Infinity ready at {INFINITY_URL}[/]")
        except Exception as e:
            console.print(f"[red]Failed to connect to Infinity: {e}[/]")
            return

        success = 0
        failed = 0
        skipped = 0

        with Progress() as progress:
            task = progress.add_task("Populating videos...", total=len(files))

            for file_path in files:
                try:
                    archive_data = parse_archive(file_path)
                    month = file_path.parent.name

                    result = await populate_single_video(
                        archive_data,
                        month,
                        infinity_url=INFINITY_URL,
                        dry_run=False,
                    )

                    if result:
                        success += 1
                    else:
                        failed += 1

                except Exception as e:
                    progress.console.print(f"[red]Failed {file_path.name}: {e}[/]")
                    failed += 1

                progress.update(task, advance=1)

        console.print(f"\n[bold green]Population complete![/]")
        console.print(f"  Success: {success}")
        console.print(f"  Failed: {failed}")
        console.print(f"  Skipped: {skipped}")

    asyncio.run(run())


@app.command()
def stats():
    """Show archive statistics."""
    console.print("[bold blue]Analyzing archives...[/]")

    files = find_archive_files()
    console.print(f"Found {len(files)} archive files")

    if not files:
        console.print("[yellow]No archive files found![/]")
        return

    # Sample first 100 to get stats quickly
    sample_files = files[:100]

    has_metadata = 0
    has_transcript = 0
    has_llm_outputs = 0
    channels = {}

    for file_path in sample_files:
        try:
            archive_data = parse_archive(file_path)

            if archive_data.get("youtube_metadata"):
                has_metadata += 1

            if archive_data.get("raw_transcript"):
                has_transcript += 1

            if archive_data.get("llm_outputs"):
                has_llm_outputs += 1

            youtube_meta = archive_data.get("youtube_metadata", {})
            channel = youtube_meta.get("channel_title", "Unknown")
            channels[channel] = channels.get(channel, 0) + 1

        except Exception as e:
            console.print(f"[red]Error reading {file_path.name}: {e}[/]")

    console.print(f"\n[bold]Statistics (sample of {len(sample_files)}):[/]")
    console.print(f"  Total files: {len(files)}")
    console.print(f"  With metadata: {has_metadata}")
    console.print(f"  With transcript: {has_transcript}")
    console.print(f"  With LLM outputs: {has_llm_outputs}")

    console.print(f"\n[bold]Top Channels:[/]")
    for channel, count in sorted(channels.items(), key=lambda x: x[1], reverse=True)[:10]:
        safe_channel = channel.encode('ascii', 'ignore').decode('ascii') or "Unknown"
        console.print(f"  {safe_channel}: {count}")


if __name__ == "__main__":
    app()
