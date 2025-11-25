#!/usr/bin/env python
"""Validate archive migration to SurrealDB.

This script validates that the migration from archives to SurrealDB completed successfully
by comparing archive files with database records and sampling videos for data integrity.

Usage:
    # Full validation with detailed report
    uv run python compose/cli/validate_migration.py validate

    # Quick count comparison only
    uv run python compose/cli/validate_migration.py quick

    # Sample N random videos and validate them
    uv run python compose/cli/validate_migration.py sample 10
"""

import asyncio
import json
import sys
from pathlib import Path
from typing import Optional

# Setup script environment
sys.path.insert(0, str(Path(__file__).parent))
from compose.cli.base import setup_script_environment

setup_script_environment(load_env=False)

import typer
from rich.console import Console
from rich.table import Table
from rich.panel import Panel

from compose.services.surrealdb import repository

app = typer.Typer(help="Validate archive migration to SurrealDB")
console = Console(force_terminal=True, force_interactive=False, width=120)

# Configuration
ARCHIVE_DIR = Path("compose/data/archive/youtube")
EXPECTED_EMBEDDING_DIM = 1024


def count_archive_files(base_dir: Optional[Path] = None) -> int:
    """Count total archive JSON files in month subdirectories.

    Args:
        base_dir: Base archive directory (defaults to ARCHIVE_DIR)

    Returns:
        Total number of archive files
    """
    if base_dir is None:
        base_dir = ARCHIVE_DIR

    if not base_dir.exists():
        console.print(f"[yellow]Archive directory not found: {base_dir}[/]")
        return 0

    count = 0
    # Iterate through month directories (e.g., 2025-11)
    for month_dir in base_dir.iterdir():
        if month_dir.is_dir():
            count += len(list(month_dir.glob("*.json")))

    return count


def get_archive_video_ids(base_dir: Optional[Path] = None) -> set[str]:
    """Get all video IDs from archive files.

    Args:
        base_dir: Base archive directory (defaults to ARCHIVE_DIR)

    Returns:
        Set of video IDs found in archives
    """
    if base_dir is None:
        base_dir = ARCHIVE_DIR

    if not base_dir.exists():
        return set()

    video_ids = set()
    for month_dir in base_dir.iterdir():
        if month_dir.is_dir():
            for json_file in month_dir.glob("*.json"):
                # Extract video_id from filename (format: {video_id}.json)
                video_id = json_file.stem
                video_ids.add(video_id)

    return video_ids


async def get_surrealdb_count() -> int:
    """Get total video count from SurrealDB.

    Returns:
        Total number of videos in SurrealDB
    """
    return await repository.get_video_count()


async def get_random_video_ids(limit: int) -> list[str]:
    """Get random video IDs for sampling.

    Args:
        limit: Number of random videos to sample

    Returns:
        List of random video IDs
    """
    return await repository.get_random_video_ids(limit)


async def validate_video_embedding(video_id: str) -> dict:
    """Validate that a video has a correct embedding.

    Args:
        video_id: YouTube video ID to validate

    Returns:
        Validation results dict with:
        - has_embedding: bool
        - embedding_dimension: int or None
        - dimension_correct: bool
    """
    video = await repository.get_video(video_id)

    if not video:
        return {
            "has_embedding": False,
            "embedding_dimension": None,
            "dimension_correct": False,
        }

    has_embedding = video.embedding is not None and len(video.embedding) > 0
    embedding_dim = len(video.embedding) if has_embedding else None
    dimension_correct = embedding_dim == EXPECTED_EMBEDDING_DIM if has_embedding else False

    return {
        "has_embedding": has_embedding,
        "embedding_dimension": embedding_dim,
        "dimension_correct": dimension_correct,
    }


async def validate_video_metadata(video_id: str) -> dict:
    """Validate that a video has required metadata fields.

    Args:
        video_id: YouTube video ID to validate

    Returns:
        Validation results dict with:
        - has_video_id: bool
        - has_title: bool
        - has_url: bool
        - has_channel_name: bool
        - has_archive_path: bool
        - missing_fields: list[str]
    """
    video = await repository.get_video(video_id)

    if not video:
        return {
            "has_video_id": False,
            "has_title": False,
            "has_url": False,
            "has_channel_name": False,
            "has_archive_path": False,
            "missing_fields": ["video_id", "title", "url", "channel_name", "archive_path"],
        }

    has_video_id = bool(video.video_id)
    has_title = video.title is not None and video.title != ""
    has_url = bool(video.url)
    has_channel_name = video.channel_name is not None and video.channel_name != ""
    has_archive_path = video.archive_path is not None and video.archive_path != ""

    missing = []
    if not has_video_id:
        missing.append("video_id")
    if not has_title:
        missing.append("title")
    if not has_url:
        missing.append("url")
    if not has_channel_name:
        missing.append("channel_name")
    if not has_archive_path:
        missing.append("archive_path")

    return {
        "has_video_id": has_video_id,
        "has_title": has_title,
        "has_url": has_url,
        "has_channel_name": has_channel_name,
        "has_archive_path": has_archive_path,
        "missing_fields": missing,
    }


def generate_validation_report(validation_results: dict) -> dict:
    """Generate validation report from results.

    Args:
        validation_results: Dict containing validation data

    Returns:
        Report dict with summary statistics
    """
    archive_count = validation_results["archive_count"]
    surrealdb_count = validation_results["surrealdb_count"]
    missing_count = len(validation_results["missing_videos"])
    embedding_issues = (
        len(validation_results["videos_without_embeddings"])
        + len(validation_results["videos_with_wrong_dimension"])
    )
    metadata_issues = len(validation_results["videos_with_missing_metadata"])

    # Calculate health percentage
    total_issues = missing_count + embedding_issues + metadata_issues
    total_expected = archive_count
    health_percentage = (
        ((total_expected - total_issues) / total_expected * 100.0)
        if total_expected > 0
        else 0.0
    )

    return {
        "total_archives": archive_count,
        "total_surrealdb": surrealdb_count,
        "count_match": archive_count == surrealdb_count,
        "missing_count": missing_count,
        "embedding_issues": embedding_issues,
        "metadata_issues": metadata_issues,
        "health_percentage": health_percentage,
    }


async def quick_validate():
    """Perform quick validation: count comparison only."""
    console.print("\n[bold cyan]Quick Validation: Archive vs SurrealDB Count[/]\n")

    console.print("[yellow]Counting archive files...[/]")
    archive_count = count_archive_files()
    console.print(f"[green]Archive files: {archive_count:,}[/]\n")

    console.print("[yellow]Counting SurrealDB videos...[/]")
    db_count = await get_surrealdb_count()
    console.print(f"[green]SurrealDB videos: {db_count:,}[/]\n")

    # Create comparison table
    table = Table(title="Count Comparison")
    table.add_column("Source", style="cyan")
    table.add_column("Count", justify="right", style="magenta")
    table.add_column("Status", style="green")

    table.add_row("Archive Files", f"{archive_count:,}", "")
    table.add_row("SurrealDB Videos", f"{db_count:,}", "")

    if archive_count == db_count:
        table.add_row("Match", "", "[green]✓ Counts match[/]")
    else:
        diff = archive_count - db_count
        table.add_row("Difference", f"{diff:,}", "[red]✗ Counts don't match[/]")

    console.print(table)
    console.print()


async def sample_validate(sample_size: int = 10):
    """Perform sample validation on random videos.

    Args:
        sample_size: Number of random videos to validate
    """
    console.print(f"\n[bold cyan]Sample Validation: {sample_size} Random Videos[/]\n")

    console.print(f"[yellow]Getting {sample_size} random video IDs...[/]")
    video_ids = await get_random_video_ids(sample_size)
    console.print(f"[green]Retrieved {len(video_ids)} video IDs[/]\n")

    if not video_ids:
        console.print("[red]No videos found in database for sampling[/]")
        return

    # Validate embeddings and metadata
    console.print("[yellow]Validating embeddings and metadata...[/]\n")

    videos_without_embeddings = []
    videos_with_wrong_dimension = []
    videos_with_missing_metadata = []

    for video_id in video_ids:
        # Validate embedding
        embedding_result = await validate_video_embedding(video_id)
        if not embedding_result["has_embedding"]:
            videos_without_embeddings.append(video_id)
        elif not embedding_result["dimension_correct"]:
            videos_with_wrong_dimension.append(
                (video_id, embedding_result["embedding_dimension"])
            )

        # Validate metadata
        metadata_result = await validate_video_metadata(video_id)
        if metadata_result["missing_fields"]:
            videos_with_missing_metadata.append(
                (video_id, metadata_result["missing_fields"])
            )

    # Create results table
    table = Table(title="Sample Validation Results")
    table.add_column("Check", style="cyan")
    table.add_column("Result", justify="right", style="magenta")
    table.add_column("Status", style="green")

    # Embedding checks
    table.add_row(
        "Videos Sampled",
        str(len(video_ids)),
        "",
    )
    table.add_row(
        "Missing Embeddings",
        str(len(videos_without_embeddings)),
        "[green]✓[/]" if len(videos_without_embeddings) == 0 else "[red]✗[/]",
    )
    table.add_row(
        "Wrong Embedding Dimension",
        str(len(videos_with_wrong_dimension)),
        "[green]✓[/]" if len(videos_with_wrong_dimension) == 0 else "[red]✗[/]",
    )
    table.add_row(
        "Missing Metadata Fields",
        str(len(videos_with_missing_metadata)),
        "[green]✓[/]" if len(videos_with_missing_metadata) == 0 else "[red]✗[/]",
    )

    console.print(table)
    console.print()

    # Show details if issues found
    if videos_without_embeddings:
        console.print("[red]Videos without embeddings:[/]")
        for video_id in videos_without_embeddings:
            console.print(f"  - {video_id}")
        console.print()

    if videos_with_wrong_dimension:
        console.print("[red]Videos with wrong embedding dimension:[/]")
        for video_id, dim in videos_with_wrong_dimension:
            console.print(f"  - {video_id} (dimension: {dim}, expected: {EXPECTED_EMBEDDING_DIM})")
        console.print()

    if videos_with_missing_metadata:
        console.print("[red]Videos with missing metadata:[/]")
        for video_id, missing_fields in videos_with_missing_metadata:
            console.print(f"  - {video_id}: {', '.join(missing_fields)}")
        console.print()


async def full_validate():
    """Perform full validation with detailed report."""
    console.print("\n[bold cyan]Full Validation: Archive Migration[/]\n")

    # Step 1: Count comparison
    console.print("[yellow]Step 1/4: Counting archive files and SurrealDB videos...[/]")
    archive_count = count_archive_files()
    db_count = await get_surrealdb_count()
    console.print(f"[green]Archive: {archive_count:,}, SurrealDB: {db_count:,}[/]\n")

    # Step 2: Find missing videos
    console.print("[yellow]Step 2/4: Checking for missing videos...[/]")
    archive_ids = get_archive_video_ids()
    db_ids = set(await repository.get_all_video_ids())
    missing_videos = list(archive_ids - db_ids)
    console.print(f"[green]Missing videos: {len(missing_videos)}[/]\n")

    # Step 3: Sample random videos for validation
    sample_size = min(50, db_count)  # Sample up to 50 videos
    console.print(f"[yellow]Step 3/4: Sampling {sample_size} videos for validation...[/]")
    sample_ids = await get_random_video_ids(sample_size)

    videos_without_embeddings = []
    videos_with_wrong_dimension = []
    videos_with_missing_metadata = []

    for video_id in sample_ids:
        # Validate embedding
        embedding_result = await validate_video_embedding(video_id)
        if not embedding_result["has_embedding"]:
            videos_without_embeddings.append(video_id)
        elif not embedding_result["dimension_correct"]:
            videos_with_wrong_dimension.append(video_id)

        # Validate metadata
        metadata_result = await validate_video_metadata(video_id)
        if metadata_result["missing_fields"]:
            videos_with_missing_metadata.append(video_id)

    console.print(f"[green]Validated {len(sample_ids)} videos[/]\n")

    # Step 4: Generate report
    console.print("[yellow]Step 4/4: Generating validation report...[/]\n")

    validation_results = {
        "archive_count": archive_count,
        "surrealdb_count": db_count,
        "missing_videos": missing_videos,
        "videos_without_embeddings": videos_without_embeddings,
        "videos_with_wrong_dimension": videos_with_wrong_dimension,
        "videos_with_missing_metadata": videos_with_missing_metadata,
    }

    report = generate_validation_report(validation_results)

    # Display report
    table = Table(title="Migration Validation Report")
    table.add_column("Metric", style="cyan")
    table.add_column("Value", justify="right", style="magenta")
    table.add_column("Status", style="green")

    # Counts
    table.add_row("Archive Files", f"{report['total_archives']:,}", "")
    table.add_row("SurrealDB Videos", f"{report['total_surrealdb']:,}", "")
    table.add_row(
        "Counts Match",
        "Yes" if report["count_match"] else "No",
        "[green]✓[/]" if report["count_match"] else "[red]✗[/]",
    )

    # Issues
    table.add_row("Missing Videos", f"{report['missing_count']:,}", "")
    table.add_row("Embedding Issues", f"{report['embedding_issues']:,}", "")
    table.add_row("Metadata Issues", f"{report['metadata_issues']:,}", "")

    # Health
    table.add_row(
        "Overall Health",
        f"{report['health_percentage']:.1f}%",
        "[green]✓[/]" if report["health_percentage"] == 100.0 else "[yellow]⚠[/]",
    )

    console.print(table)
    console.print()

    # Show details if issues found
    if missing_videos:
        console.print(f"[red]Missing videos (showing first 10 of {len(missing_videos)}):[/]")
        for video_id in missing_videos[:10]:
            console.print(f"  - {video_id}")
        console.print()

    if videos_without_embeddings:
        console.print("[red]Videos without embeddings (from sample):[/]")
        for video_id in videos_without_embeddings:
            console.print(f"  - {video_id}")
        console.print()

    if videos_with_wrong_dimension:
        console.print("[red]Videos with wrong embedding dimension (from sample):[/]")
        for video_id in videos_with_wrong_dimension:
            console.print(f"  - {video_id}")
        console.print()

    if videos_with_missing_metadata:
        console.print("[red]Videos with missing metadata (from sample):[/]")
        for video_id in videos_with_missing_metadata:
            console.print(f"  - {video_id}")
        console.print()


@app.command()
def validate():
    """Perform full validation with detailed report."""
    asyncio.run(full_validate())


@app.command()
def quick():
    """Quick count comparison only."""
    asyncio.run(quick_validate())


@app.command()
def sample(
    n: int = typer.Argument(10, help="Number of videos to sample"),
):
    """Sample N random videos and validate them."""
    asyncio.run(sample_validate(n))


def main():
    """Main entry point."""
    try:
        app()
    except KeyboardInterrupt:
        console.print("\n\n[yellow]Keyboard Interrupt Received... Exiting![/]")
        sys.exit(0)


if __name__ == "__main__":
    main()
