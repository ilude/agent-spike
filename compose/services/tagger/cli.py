"""CLI for tag normalization system."""

import asyncio
import json
import sys
from pathlib import Path
from typing import Optional

import typer
from rich.console import Console
from rich.table import Table
from rich import print as rprint

from compose.services.archive.local_reader import LocalArchiveReader
from compose.services.archive.config import ArchiveConfig

from .normalizer import create_normalizer
from .retriever import create_retriever
from .vocabulary import load_vocabulary


app = typer.Typer(help="Tag normalization system for consistent vocabulary")
console = Console()


@app.command()
def analyze():
    """Analyze archive and generate seed vocabulary."""
    console.print("[bold blue]Running archive analysis...[/bold blue]")

    # Import and run analyzer
    from pathlib import Path
    import subprocess

    script_path = Path(__file__).parent.parent / "scripts" / "analyze_archive.py"
    result = subprocess.run(
        [sys.executable, str(script_path)],
        capture_output=True,
        text=True
    )

    if result.returncode == 0:
        console.print(result.stdout)
        console.print("[bold green]Analysis complete![/bold green]")
    else:
        console.print(f"[bold red]Error:[/bold red] {result.stderr}")
        raise typer.Exit(1)


@app.command()
def normalize_video(
    video_id: str = typer.Argument(..., help="Video ID to normalize"),
    use_context: bool = typer.Option(True, "--context/--no-context", help="Use semantic context"),
    use_vocab: bool = typer.Option(True, "--vocab/--no-vocab", help="Use vocabulary"),
):
    """Normalize tags for a single video."""
    asyncio.run(_normalize_video(video_id, use_context, use_vocab))


async def _normalize_video(video_id: str, use_context: bool, use_vocab: bool):
    """Async implementation of normalize_video."""
    console.print(f"[bold blue]Normalizing video: {video_id}[/bold blue]\n")

    # Load components
    with console.status("[bold yellow]Loading components..."):
        # Load archive
        archive_path = project_root / "projects" / "data" / "archive"
        archive_config = ArchiveConfig(base_dir=archive_path, organize_by_month=True)
        archive = LocalArchiveReader(config=archive_config)

        # Load vocabulary
        vocab_path = Path(__file__).parent.parent / "data" / "seed_vocabulary_v1.json"
        vocabulary = load_vocabulary(vocab_path) if use_vocab else None

        # Create retriever
        retriever = create_retriever() if use_context else None

        # Create normalizer
        normalizer = create_normalizer(retriever=retriever, vocabulary=vocabulary)

    # Get video from archive
    video_archive = archive.get(video_id)
    if not video_archive:
        console.print(f"[bold red]Video not found in archive: {video_id}[/bold red]")
        raise typer.Exit(1)

    # Get transcript (YouTubeArchive object)
    transcript = video_archive.raw_transcript
    if not transcript:
        console.print("[bold red]No transcript found for video[/bold red]")
        raise typer.Exit(1)

    # Run normalization
    with console.status("[bold yellow]Running two-phase normalization..."):
        result = await normalizer.normalize_from_transcript(
            transcript,
            use_semantic_context=use_context,
            use_vocabulary=use_vocab
        )

    # Display results
    console.print("\n[bold green]Normalization Complete![/bold green]\n")

    # Raw metadata
    console.print("[bold cyan]Phase 1: Raw Extraction[/bold cyan]")
    raw = result["raw"]
    console.print(f"  Title: {raw.title}")
    console.print(f"  Subject Matter: {', '.join(raw.subject_matter)}")
    console.print(f"  Techniques: {', '.join(raw.techniques_or_concepts)}")
    console.print(f"  Tools: {', '.join(raw.tools_or_materials)}")
    console.print(f"  Difficulty: {raw.difficulty}")
    console.print(f"  Style: {raw.content_style}\n")

    # Normalized metadata
    console.print("[bold cyan]Phase 2: Normalized[/bold cyan]")
    norm = result["normalized"]
    console.print(f"  Title: {norm.title}")
    console.print(f"  Subject Matter: {', '.join(norm.subject_matter)}")
    console.print(f"  Techniques: {', '.join(norm.techniques_or_concepts)}")
    console.print(f"  Tools: {', '.join(norm.tools_or_materials)}")
    console.print(f"  Difficulty: {norm.difficulty}")
    console.print(f"  Style: {norm.content_style}\n")

    # Show differences
    raw_tags = set(raw.subject_matter + raw.techniques_or_concepts + raw.tools_or_materials)
    norm_tags = set(norm.subject_matter + norm.techniques_or_concepts + norm.tools_or_materials)

    if raw_tags != norm_tags:
        console.print("[bold yellow]Changes:[/bold yellow]")
        added = norm_tags - raw_tags
        removed = raw_tags - norm_tags
        if added:
            console.print(f"  Added: {', '.join(added)}")
        if removed:
            console.print(f"  Removed: {', '.join(removed)}")
    else:
        console.print("[dim]No changes made (tags already normalized)[/dim]")


@app.command()
def vocab_stats():
    """Show vocabulary statistics."""
    vocab_path = Path(__file__).parent.parent / "data" / "seed_vocabulary_v1.json"

    if not vocab_path.exists():
        console.print("[bold red]Vocabulary not found. Run 'analyze' first.[/bold red]")
        raise typer.Exit(1)

    vocabulary = load_vocabulary(vocab_path)
    stats = vocabulary.get_stats()

    console.print("\n[bold blue]Vocabulary Statistics[/bold blue]\n")

    table = Table(show_header=True, header_style="bold magenta")
    table.add_column("Metric", style="cyan")
    table.add_column("Value", style="white")

    for key, value in stats.items():
        table.add_row(key.replace("_", " ").title(), str(value))

    console.print(table)

    # Show top tags
    console.print("\n[bold blue]Top 20 Tags[/bold blue]\n")
    tag_counts = [
        (tag, info["count"])
        for tag, info in vocabulary.seed_tags.items()
    ]
    tag_counts.sort(key=lambda x: x[1], reverse=True)

    for i, (tag, count) in enumerate(tag_counts[:20], 1):
        console.print(f"  {i:2d}. {tag:40s} ({count:3d})")


@app.command()
def test_sample(
    limit: int = typer.Option(3, "--limit", "-n", help="Number of videos to test"),
):
    """Test normalization on sample videos from archive."""
    asyncio.run(_test_sample(limit))


async def _test_sample(limit: int):
    """Async implementation of test_sample."""
    console.print(f"[bold blue]Testing normalization on {limit} sample videos[/bold blue]\n")

    # Load archive
    archive_path = project_root / "projects" / "data" / "archive"
    archive_config = ArchiveConfig(base_dir=archive_path, organize_by_month=True)
    archive = LocalArchiveReader(config=archive_config)

    # Get all video IDs
    all_videos = []
    youtube_dir = archive.youtube_dir
    if youtube_dir.exists():
        for month_dir in youtube_dir.iterdir():
            if month_dir.is_dir():
                for video_file in month_dir.glob("*.json"):
                    video_id = video_file.stem
                    all_videos.append(video_id)

    if not all_videos:
        console.print("[bold red]No videos found in archive[/bold red]")
        raise typer.Exit(1)

    # Sample videos
    import random
    sample_ids = random.sample(all_videos, min(limit, len(all_videos)))

    console.print(f"Selected videos: {', '.join(sample_ids)}\n")

    # Test each video
    for i, video_id in enumerate(sample_ids, 1):
        console.print(f"\n[bold cyan]=== Video {i}/{len(sample_ids)}: {video_id} ===[/bold cyan]")
        await _normalize_video(video_id, use_context=True, use_vocab=True)

        if i < len(sample_ids):
            console.print("\n" + "="*60)


if __name__ == "__main__":
    app()
