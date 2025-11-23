#!/usr/bin/env python
"""Backfill embeddings for videos in SurrealDB.

Reads transcripts from MinIO archives and generates embeddings via Infinity,
then stores them in SurrealDB for semantic search.

Usage:
    uv run python compose/cli/backfill_embeddings.py [--dry-run] [--limit N]

Examples:
    # Preview what would be embedded
    uv run python compose/cli/backfill_embeddings.py --dry-run --limit 10

    # Embed first 100 videos
    uv run python compose/cli/backfill_embeddings.py --limit 100

    # Embed all videos missing embeddings
    uv run python compose/cli/backfill_embeddings.py
"""

import asyncio
import logging
import os
import sys
from pathlib import Path

# Setup script environment before imports
sys.path.insert(0, str(Path(__file__).parent))
from compose.cli.base import setup_script_environment
setup_script_environment(load_env=True)

import httpx
import typer
from rich.console import Console
from rich.progress import Progress

from compose.services.surrealdb.driver import execute_query
from compose.services.surrealdb.repository import init_schema
from compose.services.minio import create_minio_client

logger = logging.getLogger(__name__)

app = typer.Typer(help="Backfill embeddings for SurrealDB videos")
console = Console(force_terminal=True, force_interactive=False, width=120)

# Configuration
INFINITY_URL = os.getenv("INFINITY_URL", "http://192.168.16.241:7997")
INFINITY_MODEL = os.getenv("INFINITY_MODEL", "Alibaba-NLP/gte-large-en-v1.5")


def generate_embedding(text: str, max_chars: int = 8000) -> list[float]:
    """Generate embedding via Infinity API.

    Args:
        text: Text to embed
        max_chars: Max characters to send (Infinity has token limits)

    Returns:
        Embedding vector as list of floats
    """
    # Truncate text if too long
    if len(text) > max_chars:
        text = text[:max_chars]

    response = httpx.post(
        f"{INFINITY_URL}/embeddings",
        json={
            "model": INFINITY_MODEL,
            "input": [text]
        },
        timeout=120.0
    )
    response.raise_for_status()

    data = response.json()
    return data["data"][0]["embedding"]


async def get_videos_without_embeddings(limit: int = 0) -> list[dict]:
    """Get videos that need embeddings."""
    query = """
    SELECT video_id, url, title, archive_path, updated_at
    FROM video
    WHERE embedding IS NONE OR array::len(embedding) = 0
    ORDER BY updated_at ASC
    """
    if limit > 0:
        query += f" LIMIT {limit}"
    query += ";"

    results = await execute_query(query)
    return results


async def update_video_embedding(video_id: str, embedding: list[float]) -> bool:
    """Store embedding in SurrealDB."""
    query = """
    UPDATE type::thing('video', $video_id) SET
        embedding = $embedding,
        last_processed_at = time::now(),
        updated_at = time::now();
    """

    result = await execute_query(query, {
        "video_id": video_id,
        "embedding": embedding,
    })
    return len(result) > 0


def get_transcript_from_minio(archive_path: str, minio_client) -> str | None:
    """Fetch transcript from MinIO archive."""
    try:
        archive_data = minio_client.get_json(archive_path)
        return archive_data.get("raw_transcript", "")
    except Exception as e:
        logger.warning(f"Failed to get transcript from {archive_path}: {e}")
        return None


@app.command()
def backfill(
    dry_run: bool = typer.Option(
        False,
        "--dry-run",
        help="Show what would be embedded without doing it",
    ),
    limit: int = typer.Option(0, "--limit", help="Limit number of videos (0 = all)"),
):
    """Generate embeddings for videos missing them."""

    async def run():
        console.print("[bold blue]Initializing...[/]")

        # Initialize schema
        try:
            await init_schema()
            console.print("[green]OK SurrealDB schema ready[/]")
        except Exception as e:
            console.print(f"[yellow]Schema init note: {e}[/]")

        # Get videos needing embeddings
        console.print("[bold blue]Finding videos without embeddings...[/]")
        videos = await get_videos_without_embeddings(limit)
        console.print(f"Found {len(videos)} videos needing embeddings")

        if not videos:
            console.print("[green]All videos already have embeddings![/]")
            return

        if dry_run:
            console.print("[yellow]DRY RUN - no changes will be made[/]")
            for v in videos[:10]:
                console.print(f"  Would embed: {v.get('video_id')} - {v.get('title', 'Unknown')[:50]}")
            if len(videos) > 10:
                console.print(f"  ... and {len(videos) - 10} more")
            return

        # Initialize MinIO client
        try:
            minio_client = create_minio_client()
            console.print("[green]OK MinIO client ready[/]")
        except Exception as e:
            console.print(f"[red]Failed to connect to MinIO: {e}[/]")
            return

        # Test Infinity connection
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
            task = progress.add_task("Generating embeddings...", total=len(videos))

            for video in videos:
                video_id = video.get("video_id")
                archive_path = video.get("archive_path")

                if not archive_path:
                    progress.console.print(f"[yellow]Skipping {video_id}: no archive_path[/]")
                    skipped += 1
                    progress.update(task, advance=1)
                    continue

                try:
                    # Get transcript from MinIO
                    transcript = get_transcript_from_minio(archive_path, minio_client)

                    if not transcript:
                        progress.console.print(f"[yellow]Skipping {video_id}: no transcript[/]")
                        skipped += 1
                        progress.update(task, advance=1)
                        continue

                    # Generate embedding
                    embedding = generate_embedding(transcript)

                    # Store in SurrealDB
                    await update_video_embedding(video_id, embedding)

                    success += 1

                except Exception as e:
                    progress.console.print(f"[red]Failed {video_id}: {e}[/]")
                    failed += 1

                progress.update(task, advance=1)

        console.print(f"\n[bold green]Backfill complete![/]")
        console.print(f"  Success: {success}")
        console.print(f"  Failed: {failed}")
        console.print(f"  Skipped: {skipped}")

    asyncio.run(run())


@app.command()
def stats():
    """Show embedding statistics."""

    async def run():
        console.print("[bold blue]Checking embedding status...[/]")

        # Total videos
        total_result = await execute_query("SELECT COUNT() AS count FROM video GROUP ALL;")
        total = total_result[0].get("count", 0) if total_result else 0

        # Videos with embeddings (check array length > 0)
        embedded_result = await execute_query(
            "SELECT COUNT() AS count FROM video WHERE embedding IS NOT NONE AND array::len(embedding) > 0 GROUP ALL;"
        )
        embedded = embedded_result[0].get("count", 0) if embedded_result else 0

        # Videos without embeddings
        missing = total - embedded

        console.print(f"\n[bold]Embedding Statistics:[/]")
        console.print(f"  Total videos: {total}")
        console.print(f"  With embeddings: {embedded}")
        console.print(f"  Missing embeddings: {missing}")

        if total > 0:
            pct = (embedded / total) * 100
            console.print(f"  Coverage: {pct:.1f}%")

    asyncio.run(run())


if __name__ == "__main__":
    app()
