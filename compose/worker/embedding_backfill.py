#!/usr/bin/env python
"""Embedding backfill worker - generates chunk embeddings for archived videos.

Processes videos that have been archived but don't yet have chunk embeddings.
Tracks progress via SurrealDB pipeline_state field.

Usage:
    # Show backfill status
    uv run python -m compose.worker.embedding_backfill status

    # Run backfill (chunk + embed)
    uv run python -m compose.worker.embedding_backfill run --batch 100

    # Run only chunking step
    uv run python -m compose.worker.embedding_backfill run --step chunk --batch 50

    # Run only embedding step
    uv run python -m compose.worker.embedding_backfill run --step embed --batch 50

    # Dry run (preview what would be processed)
    uv run python -m compose.worker.embedding_backfill run --dry-run --batch 10

Environment variables:
    MINIO_URL: MinIO server URL (default: http://192.168.16.241:9000)
    MINIO_BUCKET: MinIO bucket name (default: cache)
    INFINITY_URL: Infinity embedding service URL (default: http://192.168.16.241:7997)
    OTLP_ENDPOINT: OpenTelemetry endpoint (default: http://192.168.16.241:4318)
"""

import asyncio
import logging
import os
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Literal

import typer
from rich.console import Console
from rich.progress import Progress, TextColumn, BarColumn, TaskProgressColumn
from rich.table import Table

# Setup Python path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from compose.lib.telemetry import setup_telemetry
from compose.services.chunking import chunk_youtube_transcript, chunk_plain_transcript
from compose.services.embeddings import get_chunk_embedder
from compose.services.minio import create_minio_client
from compose.services.surrealdb.driver import execute_query
from compose.services.surrealdb.models import VideoChunkRecord
from compose.services.surrealdb.repository import (
    delete_chunks_for_video,
    get_chunks_for_video,
    upsert_chunk,
    upsert_chunks,
    get_chunk_count,
)

# Initialize OpenTelemetry
_, meter = setup_telemetry("embedding-backfill", enable_instrumentation=False)

# Metrics instruments
videos_chunked_counter = meter.create_counter(
    "backfill.videos.chunked",
    description="Videos successfully chunked",
    unit="1",
)
videos_embedded_counter = meter.create_counter(
    "backfill.videos.embedded",
    description="Videos with embeddings generated",
    unit="1",
)
chunks_embedded_counter = meter.create_counter(
    "backfill.chunks.embedded",
    description="Total chunks embedded",
    unit="1",
)
backfill_errors_counter = meter.create_counter(
    "backfill.errors",
    description="Backfill errors by step and reason",
    unit="1",
)
video_duration_histogram = meter.create_histogram(
    "backfill.video.duration",
    description="Time to process a single video",
    unit="s",
)
infinity_latency_histogram = meter.create_histogram(
    "backfill.infinity.latency",
    description="Infinity API call latency per video",
    unit="s",
)

# CLI setup
app = typer.Typer(help="Embedding backfill worker for chunk embeddings")
# Use ascii-only spinner for Windows compatibility
console = Console(force_terminal=True, force_interactive=False, width=120, legacy_windows=True)
logger = logging.getLogger(__name__)

# Configuration
MINIO_URL = os.getenv("MINIO_URL", "http://192.168.16.241:9000")
MINIO_BUCKET = os.getenv("MINIO_BUCKET", "cache")


async def get_videos_needing_chunks(limit: int = 100) -> list[dict]:
    """Get videos that have been archived but don't have chunks yet."""
    query = """
    SELECT video_id, url, title, archive_path, updated_at
    FROM video
    WHERE archive_path IS NOT NONE
    AND (pipeline_state['chunk_transcript'] IS NONE)
    ORDER BY updated_at ASC
    """
    if limit > 0:
        query += f" LIMIT {limit}"
    query += ";"

    return await execute_query(query)


async def get_videos_needing_embeddings(limit: int = 100) -> list[dict]:
    """Get videos that have chunks but those chunks don't have embeddings."""
    # Find videos that have been chunked but not embedded
    query = """
    SELECT video_id, url, title, updated_at
    FROM video
    WHERE pipeline_state['chunk_transcript'] IS NOT NONE
    AND (pipeline_state['embed_chunks'] IS NONE)
    ORDER BY updated_at ASC
    """
    if limit > 0:
        query += f" LIMIT {limit}"
    query += ";"

    return await execute_query(query)


async def update_pipeline_state(video_id: str, step: str, version: str) -> None:
    """Update the pipeline_state for a video."""
    query = """
    UPDATE type::thing('video', $video_id) SET
        pipeline_state[$step] = $version,
        updated_at = time::now();
    """
    await execute_query(query, {"video_id": video_id, "step": step, "version": version})


async def process_chunk_video(video_id: str, archive_path: str, minio_client) -> tuple[bool, str, int]:
    """Chunk a single video's transcript.

    Args:
        video_id: YouTube video ID
        archive_path: Path/key in MinIO where archive is stored
        minio_client: MinIO client instance

    Returns:
        (success, message, chunk_count)
    """
    start_time = time.perf_counter()

    try:
        # Get archive from MinIO using the archive_path from DB
        if not minio_client.exists(archive_path):
            return False, f"Archive not found: {archive_path}", 0

        archive_data = minio_client.get_json(archive_path)
        timed_transcript = archive_data.get("timed_transcript")
        raw_transcript = archive_data.get("raw_transcript")

        # Try timed transcript first, fall back to raw transcript
        if timed_transcript:
            result = chunk_youtube_transcript(timed_transcript, video_id=video_id)
        elif raw_transcript:
            # Use plain text chunker (no timestamp seeking available)
            result = chunk_plain_transcript(raw_transcript, video_id=video_id)
        else:
            backfill_errors_counter.add(1, {"step": "chunk", "reason": "no_transcript"})
            return False, "No timed_transcript or raw_transcript in archive", 0

        if not result.chunks:
            backfill_errors_counter.add(1, {"step": "chunk", "reason": "no_chunks_produced"})
            return False, "Chunking produced no chunks", 0

        # Delete existing chunks (idempotent)
        await delete_chunks_for_video(video_id)

        # Create chunk records without embeddings
        chunk_records = [
            VideoChunkRecord(
                chunk_id=f"{video_id}:{chunk.chunk_index}",
                video_id=video_id,
                chunk_index=chunk.chunk_index,
                text=chunk.text,
                start_time=chunk.start_time,
                end_time=chunk.end_time,
                token_count=chunk.token_count,
                embedding=None,
            )
            for chunk in result.chunks
        ]

        # Store chunks
        count = await upsert_chunks(chunk_records)

        # Update pipeline state
        await update_pipeline_state(video_id, "chunk_transcript", "v1.0")

        # Record metrics
        duration = time.perf_counter() - start_time
        video_duration_histogram.record(duration, {"step": "chunk"})
        videos_chunked_counter.add(1)

        return True, f"Created {count} chunks", count

    except Exception as e:
        backfill_errors_counter.add(1, {"step": "chunk", "reason": "exception"})
        logger.exception(f"Error chunking {video_id}")
        return False, str(e), 0


async def process_embed_video(video_id: str) -> tuple[bool, str, int]:
    """Generate embeddings for a video's chunks.

    Returns:
        (success, message, chunks_embedded)
    """
    start_time = time.perf_counter()

    try:
        # Get chunks for this video
        chunks = await get_chunks_for_video(video_id)

        if not chunks:
            backfill_errors_counter.add(1, {"step": "embed", "reason": "no_chunks"})
            return False, "No chunks found", 0

        # Filter to chunks without embeddings
        chunks_to_embed = [c for c in chunks if not c.embedding]

        if not chunks_to_embed:
            # Already embedded, just update state
            await update_pipeline_state(video_id, "embed_chunks", "bge-m3.1024")
            return True, "All chunks already embedded", 0

        # Generate embeddings
        embedder = get_chunk_embedder()
        texts = [c.text for c in chunks_to_embed]

        infinity_start = time.perf_counter()
        embeddings = embedder.embed_batch(texts)
        infinity_latency_histogram.record(time.perf_counter() - infinity_start)

        # Update chunks with embeddings
        for chunk, embedding in zip(chunks_to_embed, embeddings):
            chunk.embedding = embedding
            await upsert_chunk(chunk)

        # Update pipeline state
        await update_pipeline_state(video_id, "embed_chunks", "bge-m3.1024")

        # Record metrics
        duration = time.perf_counter() - start_time
        video_duration_histogram.record(duration, {"step": "embed"})
        videos_embedded_counter.add(1)
        chunks_embedded_counter.add(len(chunks_to_embed))

        return True, f"Embedded {len(chunks_to_embed)} chunks", len(chunks_to_embed)

    except Exception as e:
        backfill_errors_counter.add(1, {"step": "embed", "reason": "exception"})
        logger.exception(f"Error embedding {video_id}")
        return False, str(e), 0


@app.command()
def status():
    """Show backfill progress statistics."""

    async def _status():
        console.print("[bold blue]Checking backfill status...[/]\n")

        # Get total videos
        total_result = await execute_query(
            "SELECT COUNT() AS count FROM video GROUP ALL;"
        )
        total = total_result[0].get("count", 0) if total_result else 0

        # Videos with archives
        archived_result = await execute_query(
            "SELECT COUNT() AS count FROM video WHERE archive_path IS NOT NONE GROUP ALL;"
        )
        archived = archived_result[0].get("count", 0) if archived_result else 0

        # Videos chunked
        chunked_result = await execute_query(
            "SELECT COUNT() AS count FROM video WHERE pipeline_state['chunk_transcript'] IS NOT NONE GROUP ALL;"
        )
        chunked = chunked_result[0].get("count", 0) if chunked_result else 0

        # Videos with chunk embeddings
        embedded_result = await execute_query(
            "SELECT COUNT() AS count FROM video WHERE pipeline_state['embed_chunks'] IS NOT NONE GROUP ALL;"
        )
        embedded = embedded_result[0].get("count", 0) if embedded_result else 0

        # Total chunks
        chunk_count = await get_chunk_count()

        # Chunks with embeddings
        chunks_embedded_result = await execute_query(
            "SELECT COUNT() AS count FROM video_chunk WHERE embedding IS NOT NONE GROUP ALL;"
        )
        chunks_embedded = chunks_embedded_result[0].get("count", 0) if chunks_embedded_result else 0

        # Build table
        table = Table(title="Embedding Backfill Status")
        table.add_column("Metric", style="cyan")
        table.add_column("Count", justify="right", style="green")
        table.add_column("Percentage", justify="right")

        table.add_row("Total videos", str(total), "")
        table.add_row(
            "With archives",
            str(archived),
            f"{archived / total * 100:.1f}%" if total > 0 else "N/A",
        )
        table.add_row(
            "Chunked",
            str(chunked),
            f"{chunked / archived * 100:.1f}%" if archived > 0 else "N/A",
        )
        table.add_row(
            "Chunk embeddings",
            str(embedded),
            f"{embedded / chunked * 100:.1f}%" if chunked > 0 else "N/A",
        )
        table.add_row("", "", "")
        table.add_row("Total chunks", str(chunk_count), "")
        table.add_row(
            "Chunks with embeddings",
            str(chunks_embedded),
            f"{chunks_embedded / chunk_count * 100:.1f}%" if chunk_count > 0 else "N/A",
        )

        console.print(table)

        # Show what needs processing
        console.print("\n[bold]Pending work:[/]")
        need_chunking = archived - chunked
        need_embedding = chunked - embedded
        console.print(f"  Videos needing chunking: {need_chunking}")
        console.print(f"  Videos needing embedding: {need_embedding}")

    asyncio.run(_status())


@app.command()
def run(
    step: str = typer.Option(
        "all",
        "--step",
        "-s",
        help="Which step to run: 'chunk', 'embed', or 'all'",
    ),
    batch: int = typer.Option(
        100,
        "--batch",
        "-b",
        help="Number of videos to process",
    ),
    dry_run: bool = typer.Option(
        False,
        "--dry-run",
        help="Preview what would be processed without making changes",
    ),
):
    """Run backfill for chunking and/or embedding."""

    async def _run():
        console.print(f"[bold blue]Starting backfill (step={step}, batch={batch})...[/]\n")

        # Initialize MinIO client (reads from env vars)
        try:
            minio_client = create_minio_client()
            console.print(f"[green]OK[/] MinIO connected")
        except Exception as e:
            console.print(f"[red]ERROR[/] MinIO connection failed: {e}")
            return

        # Process chunking
        if step in ("all", "chunk"):
            videos = await get_videos_needing_chunks(batch)
            console.print(f"\n[bold]Chunking:[/] Found {len(videos)} videos needing chunks")

            if dry_run:
                for v in videos[:10]:
                    console.print(f"  Would chunk: {v.get('video_id')} - {v.get('title', 'Unknown')[:50]}")
                if len(videos) > 10:
                    console.print(f"  ... and {len(videos) - 10} more")
            else:
                success_count = 0
                fail_count = 0

                with Progress(
                    TextColumn("[progress.description]{task.description}"),
                    BarColumn(),
                    TaskProgressColumn(),
                    console=console,
                ) as progress:
                    task = progress.add_task("Chunking videos...", total=len(videos))

                    for video in videos:
                        video_id = video.get("video_id")
                        archive_path = video.get("archive_path")
                        success, msg, count = await process_chunk_video(video_id, archive_path, minio_client)

                        if success:
                            success_count += 1
                        else:
                            fail_count += 1
                            progress.console.print(f"  [yellow]Skip[/] {video_id}: {msg}")

                        progress.update(task, advance=1)

                console.print(f"[green]Chunking complete:[/] {success_count} success, {fail_count} failed")

        # Process embedding
        if step in ("all", "embed"):
            videos = await get_videos_needing_embeddings(batch)
            console.print(f"\n[bold]Embedding:[/] Found {len(videos)} videos needing embeddings")

            if dry_run:
                for v in videos[:10]:
                    console.print(f"  Would embed: {v.get('video_id')} - {v.get('title', 'Unknown')[:50]}")
                if len(videos) > 10:
                    console.print(f"  ... and {len(videos) - 10} more")
            else:
                success_count = 0
                fail_count = 0
                total_chunks = 0

                with Progress(
                    TextColumn("[progress.description]{task.description}"),
                    BarColumn(),
                    TaskProgressColumn(),
                    console=console,
                ) as progress:
                    task = progress.add_task("Embedding videos...", total=len(videos))

                    for video in videos:
                        video_id = video.get("video_id")
                        success, msg, count = await process_embed_video(video_id)

                        if success:
                            success_count += 1
                            total_chunks += count
                        else:
                            fail_count += 1
                            progress.console.print(f"  [yellow]Skip[/] {video_id}: {msg}")

                        progress.update(task, advance=1)

                console.print(
                    f"[green]Embedding complete:[/] {success_count} videos, "
                    f"{total_chunks} chunks, {fail_count} failed"
                )

        console.print("\n[bold green]Backfill complete![/]")

    asyncio.run(_run())


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    app()
