#!/usr/bin/env python
"""
Migration script: Local archives -> MinIO only

Uploads all archive JSON files from compose/data/archive/youtube/
to MinIO without touching SurrealDB. Useful for:
- Initial migration to MinIO
- Re-syncing after local changes
- Verifying MinIO has all archives

Usage:
    uv run python compose/cli/migrate_archive_to_minio.py [--dry-run] [--limit N]

Examples:
    # Preview first 10
    uv run python compose/cli/migrate_archive_to_minio.py --limit 10 --dry-run

    # Migrate all archives
    uv run python compose/cli/migrate_archive_to_minio.py

    # Show statistics
    uv run python compose/cli/migrate_archive_to_minio.py stats

    # Verify MinIO has all local archives
    uv run python compose/cli/migrate_archive_to_minio.py verify
"""

import json
import sys
from pathlib import Path

# Setup script environment before imports
sys.path.insert(0, str(Path(__file__).parent))
from compose.cli.base import setup_script_environment
setup_script_environment(load_env=True)

import typer
from rich.console import Console
from rich.progress import Progress, TaskID
from rich.table import Table

from compose.services.minio import create_minio_client

app = typer.Typer(help="Migrate local YouTube archives to MinIO")
console = Console(force_terminal=True, force_interactive=False, width=120)

ARCHIVE_DIR = Path("compose/data/archive/youtube")


def find_archive_files() -> list[tuple[Path, str]]:
    """Find all archive JSON files with their month directory.

    Returns:
        List of (file_path, month) tuples
    """
    files = []
    if not ARCHIVE_DIR.exists():
        console.print(f"[yellow]Archive directory not found: {ARCHIVE_DIR}[/]")
        return files

    for month_dir in sorted(ARCHIVE_DIR.iterdir()):
        if month_dir.is_dir():
            month = month_dir.name
            for json_file in sorted(month_dir.glob("*.json")):
                files.append((json_file, month))
    return files


def parse_archive(file_path: Path) -> dict:
    """Parse archive JSON file with encoding fallbacks."""
    # Try multiple encodings
    for encoding in ["utf-8", "utf-8-sig", "latin-1", "cp1252"]:
        try:
            with open(file_path, encoding=encoding) as f:
                return json.load(f)
        except (UnicodeDecodeError, json.JSONDecodeError):
            continue

    # Last resort: read as bytes and decode with error handling
    with open(file_path, "rb") as f:
        content = f.read()
    # Try to decode with errors='replace'
    text = content.decode("utf-8", errors="replace")
    return json.loads(text)


@app.command()
def migrate(
    dry_run: bool = typer.Option(False, "--dry-run", help="Preview without uploading"),
    limit: int = typer.Option(0, "--limit", help="Limit number of files (0=all)"),
    skip_existing: bool = typer.Option(True, "--skip-existing/--force", help="Skip files already in MinIO"),
):
    """Migrate local archives to MinIO."""
    files = find_archive_files()

    if not files:
        console.print("[red]No archive files found[/]")
        raise typer.Exit(1)

    if limit > 0:
        files = files[:limit]

    console.print(f"\n[bold]Found {len(files)} archive files to process[/]")

    if dry_run:
        console.print("[yellow]DRY RUN - no files will be uploaded[/]\n")

    # Initialize MinIO client
    minio = None
    if not dry_run:
        try:
            minio = create_minio_client()
            console.print("[green]Connected to MinIO[/]\n")
        except Exception as e:
            console.print(f"[red]Failed to connect to MinIO: {e}[/]")
            raise typer.Exit(1)

    uploaded = 0
    skipped = 0
    failed = 0

    with Progress(console=console) as progress:
        task = progress.add_task("Uploading archives...", total=len(files))

        for file_path, month in files:
            video_id = file_path.stem
            minio_path = f"archives/youtube/{month}/{video_id}.json"

            # Check if already exists
            if skip_existing and minio and not dry_run:
                if minio.exists(minio_path):
                    skipped += 1
                    progress.advance(task)
                    continue

            # Parse and upload
            try:
                archive_data = parse_archive(file_path)

                if not dry_run and minio:
                    minio.put_json(minio_path, archive_data)

                uploaded += 1

            except Exception as e:
                console.print(f"[red]Failed: {video_id} - {e}[/]")
                failed += 1

            progress.advance(task)

    # Summary
    console.print()
    table = Table(title="Migration Summary")
    table.add_column("Status", style="bold")
    table.add_column("Count", justify="right")
    table.add_row("Uploaded", f"[green]{uploaded}[/]")
    table.add_row("Skipped (existing)", f"[yellow]{skipped}[/]")
    table.add_row("Failed", f"[red]{failed}[/]")
    table.add_row("Total", str(len(files)))
    console.print(table)


@app.command()
def stats():
    """Show statistics about local archives."""
    files = find_archive_files()

    if not files:
        console.print("[red]No archive files found[/]")
        raise typer.Exit(1)

    # Group by month
    by_month: dict[str, int] = {}
    total_size = 0

    for file_path, month in files:
        by_month[month] = by_month.get(month, 0) + 1
        total_size += file_path.stat().st_size

    console.print(f"\n[bold]Archive Statistics[/]")
    console.print(f"Total files: {len(files)}")
    console.print(f"Total size: {total_size / 1024 / 1024:.1f} MB")
    console.print(f"\nBy month:")

    for month in sorted(by_month.keys()):
        console.print(f"  {month}: {by_month[month]} files")


@app.command()
def verify():
    """Verify MinIO has all local archives."""
    files = find_archive_files()

    if not files:
        console.print("[red]No archive files found[/]")
        raise typer.Exit(1)

    try:
        minio = create_minio_client()
        console.print("[green]Connected to MinIO[/]\n")
    except Exception as e:
        console.print(f"[red]Failed to connect to MinIO: {e}[/]")
        raise typer.Exit(1)

    missing = []
    present = 0

    with Progress(console=console) as progress:
        task = progress.add_task("Verifying archives...", total=len(files))

        for file_path, month in files:
            video_id = file_path.stem
            minio_path = f"archives/youtube/{month}/{video_id}.json"

            if minio.exists(minio_path):
                present += 1
            else:
                missing.append((video_id, month))

            progress.advance(task)

    console.print()
    console.print(f"[green]Present in MinIO: {present}[/]")
    console.print(f"[red]Missing from MinIO: {len(missing)}[/]")

    if missing and len(missing) <= 20:
        console.print("\nMissing videos:")
        for video_id, month in missing:
            console.print(f"  - {month}/{video_id}")
    elif missing:
        console.print(f"\n(First 20 missing: {[f'{m}/{v}' for v, m in missing[:20]]})")

    if missing:
        console.print("\n[yellow]Run 'migrate' command to upload missing archives[/]")


if __name__ == "__main__":
    app()
