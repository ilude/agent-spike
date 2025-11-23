#!/usr/bin/env python
"""
Migration script: File archives -> SurrealDB + MinIO

Reads all archive JSON files from compose/data/archive/youtube/
and migrates them to:
- SurrealDB: Video metadata, embeddings, relationships
- MinIO: Full archive JSON, transcripts, LLM outputs

Usage:
    uv run python compose/cli/migrate_to_surrealdb.py [--dry-run] [--limit N]

Examples:
    # Preview 10 migrations
    uv run python compose/cli/migrate_to_surrealdb.py --limit 10 --dry-run

    # Migrate first 100 archives
    uv run python compose/cli/migrate_to_surrealdb.py --limit 100

    # Migrate all archives
    uv run python compose/cli/migrate_to_surrealdb.py

    # Show statistics about archives
    uv run python compose/cli/migrate_to_surrealdb.py stats
"""

import asyncio
import json
import logging
import sys
from datetime import datetime
from pathlib import Path
from typing import Optional

# Setup script environment before imports
sys.path.insert(0, str(Path(__file__).parent))
from compose.cli.base import setup_script_environment
setup_script_environment(load_env=True)

import typer
from rich.console import Console
from rich.progress import Progress

from compose.services.surrealdb.repository import init_schema, upsert_video
from compose.services.surrealdb.models import VideoRecord
from compose.services.minio import create_minio_client
from compose.services.minio.archive import ArchiveStorage

logger = logging.getLogger(__name__)

app = typer.Typer(help="Migrate YouTube archives to SurrealDB + MinIO")
console = Console(force_terminal=True, force_interactive=False, width=120)

ARCHIVE_DIR = Path("compose/data/archive/youtube")


def find_archive_files() -> list[Path]:
    """Find all archive JSON files."""
    files = []
    if not ARCHIVE_DIR.exists():
        console.print(f"[yellow]Archive directory not found: {ARCHIVE_DIR}[/]")
        return files

    for month_dir in ARCHIVE_DIR.iterdir():
        if month_dir.is_dir():
            for json_file in month_dir.glob("*.json"):
                files.append(json_file)
    return sorted(files)


def parse_archive(file_path: Path) -> dict:
    """Parse archive JSON file."""
    with open(file_path) as f:
        return json.load(f)


async def migrate_single(
    archive_data: dict,
    month: str,
    minio_client: Optional[object] = None,
    surreal_client: Optional[object] = None,
    dry_run: bool = False,
) -> bool:
    """Migrate a single archive to SurrealDB + MinIO.

    Args:
        archive_data: Parsed archive JSON
        month: Month directory name (e.g., "2025-11")
        minio_client: MinIO client instance (optional)
        surreal_client: SurrealDB client instance (optional)
        dry_run: If True, don't write anything

    Returns:
        True if migration successful, False otherwise
    """
    video_id = archive_data.get("video_id")
    if not video_id:
        return False

    # Extract metadata
    youtube_meta = archive_data.get("youtube_metadata", {})
    import_meta = archive_data.get("import_metadata", {})
    channel_context = import_meta.get("channel_context", {}) if import_meta else {}

    # 1. Upload full archive to MinIO
    archive_path = f"archives/youtube/{month}/{video_id}.json"
    if minio_client and not dry_run:
        try:
            minio_client.put_json(archive_path, archive_data)
        except Exception as e:
            logger.error(f"Failed to upload archive for {video_id}: {e}")
            return False

    # 2. Upload transcript if exists
    transcript = archive_data.get("raw_transcript", "")
    transcript_path = None
    if transcript and minio_client and not dry_run:
        transcript_path = f"transcripts/{video_id}.txt"
        try:
            minio_client.put_text(transcript_path, transcript)
        except Exception as e:
            logger.error(f"Failed to upload transcript for {video_id}: {e}")
            return False

    # 3. Upload LLM outputs if exist
    llm_outputs = archive_data.get("llm_outputs", [])
    for output in llm_outputs:
        if minio_client and not dry_run:
            output_type = output.get("output_type", "unknown")
            try:
                minio_client.put_json(
                    f"llm_outputs/{video_id}/{output_type}.json",
                    output
                )
            except Exception as e:
                logger.error(f"Failed to upload LLM output for {video_id}: {e}")
                return False

    # 4. Create SurrealDB record
    # Convert fetched_at to datetime if it's a string
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
        recommendation_weight=import_meta.get("recommendation_weight", 1.0)
        if import_meta
        else 1.0,
        archive_path=archive_path,
        pipeline_state={},
    )

    # Upsert to SurrealDB (async operation)
    if not dry_run:
        try:
            await upsert_video(video_record)
        except Exception as e:
            logger.error(f"Failed to upsert video {video_id} to SurrealDB: {e}")
            return False

    return True


@app.command()
def migrate(
    dry_run: bool = typer.Option(
        False,
        "--dry-run",
        help="Show what would be migrated without doing it",
    ),
    limit: int = typer.Option(0, "--limit", help="Limit number of files to migrate (0 = all)"),
):
    """Migrate archive files to SurrealDB + MinIO."""

    console.print("[bold blue]Finding archive files...[/]")
    files = find_archive_files()
    console.print(f"Found {len(files)} archive files")

    if limit > 0:
        files = files[:limit]
        console.print(f"Limited to {limit} files")

    if dry_run:
        console.print("[yellow]DRY RUN - no changes will be made[/]")
        console.print(f"\nWould migrate the following files:\n")
        for f in files[:10]:
            try:
                archive_data = parse_archive(f)
                title = archive_data.get("youtube_metadata", {}).get("title", "Unknown")
                console.print(f"  {f.name:20} -> {title[:50]}")
            except Exception as e:
                console.print(f"  [red]{f.name:20} (error: {str(e)[:30]})[/]")
        if len(files) > 10:
            console.print(f"\n  ... and {len(files) - 10} more files")
        return

    # Initialize clients
    console.print("[bold blue]Initializing clients...[/]")
    try:
        minio_client = create_minio_client()
        console.print("[green]OK MinIO client initialized[/]")
    except Exception as e:
        console.print(f"[red]Failed to initialize MinIO: {e}[/]")
        return

    success = 0
    failed = 0
    errors = []

    async def run_migrations():
        """Run all migrations asynchronously."""
        nonlocal success, failed, errors

        # Initialize SurrealDB schema in the same event loop
        console.print("[bold green]Starting migration...[/]")
        try:
            await init_schema()
            console.print("[green]OK SurrealDB schema initialized[/]\n")
        except Exception as e:
            console.print(f"[yellow]Note: SurrealDB schema init warning: {e}[/]\n")

        with Progress() as progress:
            task = progress.add_task("Migrating...", total=len(files))

            for file_path in files:
                try:
                    archive_data = parse_archive(file_path)
                    month = file_path.parent.name

                    result = await migrate_single(
                        archive_data,
                        month,
                        minio_client=minio_client,
                        surreal_client=None,
                        dry_run=False,
                    )

                    if result:
                        success += 1
                    else:
                        failed += 1
                        errors.append((file_path.name, "Migration returned False"))
                except Exception as e:
                    console.print(f"[red]Failed {file_path.name}: {e}[/]")
                    failed += 1
                    errors.append((file_path.name, str(e)))

                progress.update(task, advance=1)

    # Run migrations with asyncio - single event loop
    asyncio.run(run_migrations())

    console.print(f"\n[bold green]Migration complete![/]")
    console.print(f"  OK Success: {success}")
    console.print(f"  FAIL Failed: {failed}")

    if errors and failed <= 10:
        console.print(f"\n[yellow]Error details:[/]")
        for filename, error in errors:
            console.print(f"  {filename}: {error}")


@app.command()
def stats(
    limit: int = typer.Option(0, "--limit", help="Limit number of files to analyze (0 = all)"),
):
    """Show statistics about archive files."""

    console.print("[bold blue]Analyzing archive files...[/]")
    files = find_archive_files()
    console.print(f"Found {len(files)} archive files\n")

    if limit > 0:
        files = files[:limit]

    total_transcript_chars = 0
    total_llm_outputs = 0
    total_derived_outputs = 0
    files_with_tags = 0
    channels = {}
    import_types = {}

    with Progress() as progress:
        task = progress.add_task("Analyzing...", total=len(files))

        for file_path in files:
            try:
                archive_data = parse_archive(file_path)

                # Transcript stats
                transcript = archive_data.get("raw_transcript", "")
                total_transcript_chars += len(transcript)

                # LLM outputs stats
                llm_outputs = archive_data.get("llm_outputs", [])
                total_llm_outputs += len(llm_outputs)

                # Check for tags
                for output in llm_outputs:
                    if output.get("output_type") == "tags":
                        files_with_tags += 1
                        break

                # Derived outputs stats
                derived_outputs = archive_data.get("derived_outputs", [])
                total_derived_outputs += len(derived_outputs)

                # Channel stats
                youtube_meta = archive_data.get("youtube_metadata", {})
                channel_name = youtube_meta.get("channel_title", "Unknown")
                channels[channel_name] = channels.get(channel_name, 0) + 1

                # Import type stats
                import_meta = archive_data.get("import_metadata", {})
                import_type = import_meta.get("source_type", "unknown") if import_meta else "unknown"
                import_types[import_type] = import_types.get(import_type, 0) + 1

            except Exception as e:
                console.print(f"[red]Error reading {file_path.name}: {e}[/]")

            progress.update(task, advance=1)

    console.print(f"\n[bold]Overall Statistics:[/]")
    console.print(f"  Total files: {len(files)}")
    console.print(
        f"  Total transcript chars: {total_transcript_chars:,}"
    )
    console.print(
        f"  Avg transcript length: {total_transcript_chars // len(files) if files else 0:,} chars"
    )
    console.print(f"  Files with extracted tags: {files_with_tags}")
    console.print(f"  Total LLM outputs: {total_llm_outputs}")
    console.print(
        f"  Avg LLM outputs per file: {total_llm_outputs / len(files) if files else 0:.1f}"
    )
    console.print(f"  Total derived outputs: {total_derived_outputs}")

    console.print(f"\n[bold]By Channel:[/]")
    for channel, count in sorted(channels.items(), key=lambda x: x[1], reverse=True)[:10]:
        # Replace problematic Unicode characters for Windows console
        safe_channel = channel.encode('ascii', 'ignore').decode('ascii') or "Unknown"
        console.print(f"  {safe_channel}: {count}")

    console.print(f"\n[bold]By Import Type:[/]")
    for import_type, count in sorted(import_types.items(), key=lambda x: x[1], reverse=True):
        console.print(f"  {import_type}: {count}")


if __name__ == "__main__":
    app()
