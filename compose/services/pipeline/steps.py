"""Concrete pipeline steps for YouTube video ingestion.

Each step:
1. Has automatic version tracking via @pipeline_step
2. Archives data before caching (archive-first strategy)
3. Updates SurrealDB state after successful execution

Step chain:
    fetch_transcript -> fetch_metadata -> archive_raw -> generate_tags -> cache_to_minio
"""

from datetime import datetime
from typing import Optional

from .decorator import pipeline_step
from .models import PipelineContext, StepResult


@pipeline_step(description="Fetch YouTube transcript using youtube-transcript-api")
def fetch_transcript(ctx: PipelineContext) -> StepResult[str]:
    """Fetch transcript for a YouTube video.

    This is typically the first step in the pipeline.
    Transcript is stored in ctx for downstream steps.
    """
    from compose.services.youtube import get_transcript, extract_video_id

    try:
        video_id = extract_video_id(ctx.url)
        transcript = get_transcript(ctx.url, cache=None)

        if "ERROR:" in transcript:
            return StepResult.fail(transcript)

        return StepResult.ok(transcript)

    except Exception as e:
        return StepResult.fail(f"Transcript fetch failed: {e}")


@pipeline_step(description="Fetch YouTube video metadata from API")
def fetch_metadata(ctx: PipelineContext) -> StepResult[dict]:
    """Fetch YouTube metadata (title, channel, duration, etc.).

    Can run in parallel with fetch_transcript since they're independent.
    """
    from compose.services.youtube import fetch_video_metadata

    try:
        metadata, error = fetch_video_metadata(ctx.video_id)

        if error:
            return StepResult.fail(f"Metadata fetch failed: {error}")

        return StepResult.ok(metadata or {})

    except Exception as e:
        return StepResult.fail(f"Metadata fetch failed: {e}")


@pipeline_step(
    depends_on=["fetch_transcript", "fetch_metadata"],
    description="Archive transcript and metadata to local JSON files",
)
def archive_raw(ctx: PipelineContext) -> StepResult[str]:
    """Archive raw data (transcript + metadata) to local files.

    Archives immediately after fetching to protect against data loss.
    This follows the archive-first strategy.
    """
    from compose.services.archive import (
        create_archive_manager,
        create_local_archive_writer,
        ImportMetadata,
        ChannelContext,
    )

    transcript = ctx.get_value("fetch_transcript")
    metadata = ctx.get_value("fetch_metadata") or {}

    if not transcript:
        return StepResult.fail("No transcript to archive")

    try:
        # Create archive manager
        writer = create_local_archive_writer()
        manager = create_archive_manager(writer=writer)

        # Build import metadata
        import_metadata = ImportMetadata(
            source_type=ctx.metadata.get("source_type", "single_import"),
            imported_at=datetime.now(),
            import_method=ctx.metadata.get("import_method", "pipeline"),
            channel_context=ChannelContext(
                channel_id=metadata.get("channel_id"),
                channel_name=metadata.get("channel_title"),
                is_bulk_import=ctx.metadata.get("is_bulk", False),
            ),
            recommendation_weight=ctx.metadata.get("recommendation_weight", 1.0),
        )

        # Archive transcript
        manager.update_transcript(
            video_id=ctx.video_id,
            url=ctx.url,
            transcript=transcript,
            import_metadata=import_metadata,
        )

        # Archive metadata
        if metadata:
            manager.update_metadata(
                video_id=ctx.video_id,
                url=ctx.url,
                metadata=metadata,
            )

        return StepResult.ok(f"Archived {ctx.video_id}")

    except Exception as e:
        return StepResult.fail(f"Archive failed: {e}")


@pipeline_step(
    depends_on=["fetch_transcript"],
    description="Generate topic tags from transcript using LLM",
)
def generate_tags(ctx: PipelineContext) -> StepResult[list[str]]:
    """Generate topic tags from transcript.

    Uses Claude Haiku for cost-effective tag generation.
    Tags are archived as LLM output.

    Note: Full tagger integration requires async support.
    For now, returns empty list - tags can be backfilled later.
    """
    transcript = ctx.get_value("fetch_transcript")

    if not transcript:
        return StepResult.fail("No transcript for tag generation")

    # TODO: Integrate with async tagger when pipeline supports async
    # The tagger uses: await normalizer.normalize_from_transcript(transcript)
    # For now, return empty list - can be backfilled later
    return StepResult.ok([])


@pipeline_step(
    depends_on=["archive_raw"],
    description="Cache video data to MinIO for retrieval",
)
def cache_to_minio(ctx: PipelineContext) -> StepResult[str]:
    """Cache video data to MinIO object storage.

    Only runs after archiving to ensure data is persisted first.
    """
    import os
    from compose.services.minio import create_minio_client, ArchiveStorage

    transcript = ctx.get_value("fetch_transcript")
    metadata = ctx.get_value("fetch_metadata") or {}

    if not transcript:
        return StepResult.fail("No transcript to cache")

    try:
        client = create_minio_client(
            url=os.getenv("MINIO_URL", "http://localhost:9000"),
            bucket=os.getenv("MINIO_BUCKET", "cache"),
        )
        client.ensure_bucket()
        storage = ArchiveStorage(client)

        cache_key = f"youtube:video:{ctx.video_id}"

        # Skip if already cached
        if client.exists(cache_key):
            return StepResult.ok(f"Already cached: {ctx.video_id}", cached=True)

        cache_data = {
            "video_id": ctx.video_id,
            "url": ctx.url,
            "transcript": transcript,
            "transcript_length": len(transcript),
            "type": "youtube_video",
            "source": "pipeline",
            "source_type": ctx.metadata.get("source_type", "single_import"),
            "recommendation_weight": ctx.metadata.get("recommendation_weight", 1.0),
            "imported_at": datetime.now().isoformat(),
            "youtube_title": metadata.get("title"),
            "youtube_channel": metadata.get("channel_title"),
            "youtube_channel_id": metadata.get("channel_id"),
            "youtube_duration_seconds": metadata.get("duration_seconds"),
            "youtube_view_count": metadata.get("view_count"),
            "youtube_published_at": metadata.get("published_at"),
        }

        client.put_json(cache_key, cache_data)

        return StepResult.ok(f"Cached {ctx.video_id} ({len(transcript)} chars)")

    except Exception as e:
        return StepResult.fail(f"Cache failed: {e}")


@pipeline_step(
    depends_on=["cache_to_minio"],
    description="Update SurrealDB with video relationships",
)
def update_graph(ctx: PipelineContext) -> StepResult[str]:
    """Update SurrealDB with video node and relationships.

    Creates/updates:
    - Video record with pipeline state
    - Channel relationship
    - Topic relationships (if tags available)
    """
    import asyncio
    from compose.services.surrealdb import (
        upsert_video,
        link_video_to_channel,
        link_video_to_topics,
        VideoRecord,
    )

    metadata = ctx.get_value("fetch_metadata") or {}
    tags = ctx.get_value("generate_tags") or []

    async def _update_db():
        try:
            # Create video record
            video = VideoRecord(
                video_id=ctx.video_id,
                url=ctx.url,
                fetched_at=ctx.started_at,
                title=metadata.get("title"),
                channel_id=metadata.get("channel_id"),
                channel_name=metadata.get("channel_title"),
                duration_seconds=metadata.get("duration_seconds"),
                view_count=metadata.get("view_count"),
                source_type=ctx.metadata.get("source_type"),
                import_method=ctx.metadata.get("import_method"),
                recommendation_weight=ctx.metadata.get("recommendation_weight", 1.0),
            )

            await upsert_video(video)

            # Link to channel if available
            if metadata.get("channel_id") and metadata.get("channel_title"):
                await link_video_to_channel(
                    ctx.video_id,
                    metadata["channel_id"],
                    metadata["channel_title"],
                )

            # Link to topics if tags available
            if tags:
                await link_video_to_topics(ctx.video_id, tags)

            return StepResult.ok(f"Database updated for {ctx.video_id}")

        except Exception as e:
            return StepResult.fail(f"Database update failed: {e}")

    return asyncio.run(_update_db())


@pipeline_step(
    depends_on=["archive_raw"],
    description="Chunk transcript into semantic segments for fine-grained search",
)
def chunk_transcript(ctx: PipelineContext) -> StepResult[int]:
    """Chunk a video transcript into semantic segments.

    Uses time + token hybrid chunking strategy:
    - Splits on natural pause boundaries (8+ sec gaps)
    - Targets 2500 tokens per chunk
    - Tracks start/end timestamps for each chunk

    This enables timestamp-level search ("find where they discussed X").
    """
    import asyncio
    import os

    from compose.services.chunking import chunk_youtube_transcript
    from compose.services.minio import create_minio_client
    from compose.services.surrealdb import (
        delete_chunks_for_video,
        upsert_chunks,
        VideoChunkRecord,
    )

    async def _chunk_and_store():
        try:
            # Get timed transcript from MinIO archive
            minio_client = create_minio_client(
                url=os.getenv("MINIO_URL", "http://192.168.16.241:9000"),
                bucket=os.getenv("MINIO_BUCKET", "cache"),
            )

            archive_key = f"youtube:video:{ctx.video_id}"
            if not minio_client.exists(archive_key):
                return StepResult.fail(f"Archive not found: {archive_key}")

            archive_data = minio_client.get_json(archive_key)
            timed_transcript = archive_data.get("timed_transcript")

            if not timed_transcript:
                # Fall back to raw transcript - can't chunk without timestamps
                return StepResult.fail(
                    f"No timed_transcript for {ctx.video_id} - cannot chunk"
                )

            # Chunk the transcript
            result = chunk_youtube_transcript(timed_transcript, video_id=ctx.video_id)

            if not result.chunks:
                return StepResult.fail(f"Chunking produced no chunks for {ctx.video_id}")

            # Delete existing chunks (idempotent re-chunking)
            await delete_chunks_for_video(ctx.video_id)

            # Create chunk records (without embeddings - those come later)
            chunk_records = [
                VideoChunkRecord(
                    chunk_id=f"{ctx.video_id}:{chunk.chunk_index}",
                    video_id=ctx.video_id,
                    chunk_index=chunk.chunk_index,
                    text=chunk.text,
                    start_time=chunk.start_time,
                    end_time=chunk.end_time,
                    token_count=chunk.token_count,
                    embedding=None,  # Embeddings generated in embed_chunks step
                )
                for chunk in result.chunks
            ]

            # Store chunks in SurrealDB
            count = await upsert_chunks(chunk_records)

            return StepResult.ok(
                count,
                message=f"Created {count} chunks for {ctx.video_id} "
                f"(total duration: {result.total_duration:.0f}s)",
            )

        except Exception as e:
            return StepResult.fail(f"Chunking failed: {e}")

    return asyncio.run(_chunk_and_store())


@pipeline_step(
    depends_on=["chunk_transcript"],
    description="Generate embeddings for transcript chunks using bge-m3",
)
def embed_chunks(ctx: PipelineContext) -> StepResult[int]:
    """Generate embeddings for all chunks of a video.

    Uses BAAI/bge-m3 model via Infinity service for chunk-level embeddings.
    These enable fine-grained semantic search with timestamp precision.
    """
    import asyncio

    from compose.services.embeddings import get_chunk_embedder
    from compose.services.surrealdb import get_chunks_for_video, upsert_chunk

    async def _embed_chunks():
        try:
            # Get chunks for this video
            chunks = await get_chunks_for_video(ctx.video_id)

            if not chunks:
                return StepResult.fail(f"No chunks found for {ctx.video_id}")

            # Filter to chunks without embeddings
            chunks_to_embed = [c for c in chunks if not c.embedding]

            if not chunks_to_embed:
                return StepResult.ok(
                    0, message=f"All {len(chunks)} chunks already have embeddings"
                )

            # Get embedder and generate embeddings in batch
            embedder = get_chunk_embedder()
            texts = [c.text for c in chunks_to_embed]
            embeddings = embedder.embed_batch(texts)

            # Update each chunk with its embedding
            for chunk, embedding in zip(chunks_to_embed, embeddings):
                chunk.embedding = embedding
                await upsert_chunk(chunk)

            return StepResult.ok(
                len(chunks_to_embed),
                message=f"Embedded {len(chunks_to_embed)} chunks for {ctx.video_id}",
            )

        except Exception as e:
            return StepResult.fail(f"Chunk embedding failed: {e}")

    return asyncio.run(_embed_chunks())


# Default step list for full ingestion
DEFAULT_PIPELINE_STEPS = [
    "fetch_transcript",
    "fetch_metadata",
    "archive_raw",
    "generate_tags",
    "cache_to_minio",
    "update_graph",
]

# Minimal steps (no LLM, no graph)
MINIMAL_PIPELINE_STEPS = [
    "fetch_transcript",
    "fetch_metadata",
    "archive_raw",
    "cache_to_minio",
]

# Embedding pipeline (for backfill operations)
EMBEDDING_PIPELINE_STEPS = [
    "chunk_transcript",
    "embed_chunks",
]
