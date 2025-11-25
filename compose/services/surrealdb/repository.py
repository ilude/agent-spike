"""SurrealDB repository for video CRUD operations and semantic search.

Provides:
- Schema initialization with tables and indexes
- CRUD operations for videos with pipeline state tracking
- Vector similarity search using SurrealDB vector functions
- Channel and topic relationship management
"""

import json
import logging
from datetime import datetime
from typing import Optional

from .driver import execute_query
from .models import (
    ChannelRecord,
    ChunkSearchResult,
    StaleVideoResult,
    TopicRecord,
    VideoChunkRecord,
    VideoRecord,
    VectorSearchResult,
)

logger = logging.getLogger(__name__)


def _parse_datetime(value, default: datetime | None = None) -> datetime:
    """Parse datetime from SurrealDB result.

    SurrealDB can return datetimes as either ISO strings or native datetime objects.
    This handles both cases safely.
    """
    if isinstance(value, datetime):
        return value
    if isinstance(value, str):
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    return default if default is not None else datetime.now()


def _parse_datetime_optional(value) -> datetime | None:
    """Parse optional datetime from SurrealDB result."""
    if value is None:
        return None
    if isinstance(value, datetime):
        return value
    if isinstance(value, str):
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    return None


async def init_schema() -> None:
    """Initialize SurrealDB schema with tables and indexes.

    Creates:
    - video table with video_id unique index
    - channel table with channel_id unique index
    - topic table with normalized_name unique index
    - Indexes on video.updated_at, video.channel_id, video.embedding
    """
    queries = [
        # Video table
        """
        DEFINE TABLE video SCHEMAFULL;
        DEFINE FIELD video_id ON TABLE video TYPE string;
        DEFINE FIELD url ON TABLE video TYPE string;
        DEFINE FIELD fetched_at ON TABLE video TYPE datetime;
        DEFINE FIELD title ON TABLE video TYPE option<string>;
        DEFINE FIELD channel_id ON TABLE video TYPE option<string>;
        DEFINE FIELD channel_name ON TABLE video TYPE option<string>;
        DEFINE FIELD duration_seconds ON TABLE video TYPE option<int>;
        DEFINE FIELD view_count ON TABLE video TYPE option<int>;
        DEFINE FIELD published_at ON TABLE video TYPE option<datetime>;
        DEFINE FIELD source_type ON TABLE video TYPE option<string>;
        DEFINE FIELD import_method ON TABLE video TYPE option<string>;
        DEFINE FIELD recommendation_weight ON TABLE video TYPE float DEFAULT 1.0;
        DEFINE FIELD pipeline_state ON TABLE video TYPE option<object>;
        DEFINE FIELD embedding ON TABLE video TYPE option<array<float>>;
        DEFINE FIELD archive_path ON TABLE video TYPE option<string>;
        DEFINE FIELD last_processed_at ON TABLE video TYPE option<datetime>;
        DEFINE FIELD created_at ON TABLE video TYPE datetime VALUE time::now();
        DEFINE FIELD updated_at ON TABLE video TYPE datetime VALUE time::now();
        DEFINE INDEX idx_video_id ON TABLE video COLUMNS video_id UNIQUE;
        DEFINE INDEX idx_video_updated ON TABLE video COLUMNS updated_at;
        DEFINE INDEX idx_video_channel ON TABLE video COLUMNS channel_id;
        DEFINE INDEX idx_video_embedding ON TABLE video FIELDS embedding HNSW DIMENSION 1024 DIST COSINE;
        """,
        # Video chunk table for chunk-level embeddings
        """
        DEFINE TABLE video_chunk SCHEMAFULL;
        DEFINE FIELD chunk_id ON TABLE video_chunk TYPE string;
        DEFINE FIELD video_id ON TABLE video_chunk TYPE string;
        DEFINE FIELD chunk_index ON TABLE video_chunk TYPE int;
        DEFINE FIELD text ON TABLE video_chunk TYPE string;
        DEFINE FIELD start_time ON TABLE video_chunk TYPE float;
        DEFINE FIELD end_time ON TABLE video_chunk TYPE float;
        DEFINE FIELD token_count ON TABLE video_chunk TYPE int;
        DEFINE FIELD embedding ON TABLE video_chunk TYPE option<array<float>>;
        DEFINE FIELD created_at ON TABLE video_chunk TYPE datetime VALUE time::now();
        DEFINE INDEX idx_chunk_id ON TABLE video_chunk COLUMNS chunk_id UNIQUE;
        DEFINE INDEX idx_chunk_video ON TABLE video_chunk COLUMNS video_id;
        DEFINE INDEX idx_chunk_embedding ON TABLE video_chunk FIELDS embedding HNSW DIMENSION 1024 DIST COSINE;
        """,
        # Channel table
        """
        DEFINE TABLE channel SCHEMAFULL;
        DEFINE FIELD channel_id ON TABLE channel TYPE string;
        DEFINE FIELD channel_name ON TABLE channel TYPE string;
        DEFINE FIELD video_count ON TABLE channel TYPE int DEFAULT 0;
        DEFINE FIELD created_at ON TABLE channel TYPE datetime VALUE time::now();
        DEFINE FIELD updated_at ON TABLE channel TYPE datetime VALUE time::now();
        DEFINE INDEX idx_channel_id ON TABLE channel COLUMNS channel_id UNIQUE;
        """,
        # Topic table
        """
        DEFINE TABLE topic SCHEMAFULL;
        DEFINE FIELD name ON TABLE topic TYPE string;
        DEFINE FIELD normalized_name ON TABLE topic TYPE string;
        DEFINE FIELD video_count ON TABLE topic TYPE int DEFAULT 0;
        DEFINE FIELD created_at ON TABLE topic TYPE datetime VALUE time::now();
        DEFINE FIELD updated_at ON TABLE topic TYPE datetime VALUE time::now();
        DEFINE INDEX idx_topic_name ON TABLE topic COLUMNS normalized_name UNIQUE;
        """,
        # Relationship tables
        """
        DEFINE TABLE video_channel SCHEMAFULL;
        DEFINE FIELD video_id ON TABLE video_channel TYPE string;
        DEFINE FIELD channel_id ON TABLE video_channel TYPE string;
        DEFINE FIELD created_at ON TABLE video_channel TYPE datetime VALUE time::now();
        """,
        """
        DEFINE TABLE video_topic SCHEMAFULL;
        DEFINE FIELD video_id ON TABLE video_topic TYPE string;
        DEFINE FIELD topic_id ON TABLE video_topic TYPE string;
        DEFINE FIELD created_at ON TABLE video_topic TYPE datetime VALUE time::now();
        """,
        # Conversation table
        """
        DEFINE TABLE conversation SCHEMAFULL;
        DEFINE FIELD id ON TABLE conversation TYPE string;
        DEFINE FIELD title ON TABLE conversation TYPE string;
        DEFINE FIELD model ON TABLE conversation TYPE option<string>;
        DEFINE FIELD created_at ON TABLE conversation TYPE datetime VALUE time::now();
        DEFINE FIELD updated_at ON TABLE conversation TYPE datetime VALUE time::now();
        DEFINE INDEX idx_conversation_id ON TABLE conversation COLUMNS id UNIQUE;
        """,
        # Message table
        """
        DEFINE TABLE message SCHEMAFULL;
        DEFINE FIELD id ON TABLE message TYPE string;
        DEFINE FIELD conversation_id ON TABLE message TYPE string;
        DEFINE FIELD role ON TABLE message TYPE string;
        DEFINE FIELD content ON TABLE message TYPE string;
        DEFINE FIELD sources ON TABLE message TYPE option<array>;
        DEFINE FIELD timestamp ON TABLE message TYPE datetime VALUE time::now();
        DEFINE INDEX idx_message_id ON TABLE message COLUMNS id UNIQUE;
        DEFINE INDEX idx_message_conversation ON TABLE message COLUMNS conversation_id;
        """,
        # Project table
        """
        DEFINE TABLE project SCHEMAFULL;
        DEFINE FIELD id ON TABLE project TYPE string;
        DEFINE FIELD name ON TABLE project TYPE string;
        DEFINE FIELD description ON TABLE project TYPE option<string>;
        DEFINE FIELD custom_instructions ON TABLE project TYPE option<string>;
        DEFINE FIELD created_at ON TABLE project TYPE datetime VALUE time::now();
        DEFINE FIELD updated_at ON TABLE project TYPE datetime VALUE time::now();
        DEFINE INDEX idx_project_id ON TABLE project COLUMNS id UNIQUE;
        """,
        # Project file table
        """
        DEFINE TABLE project_file SCHEMAFULL;
        DEFINE FIELD id ON TABLE project_file TYPE string;
        DEFINE FIELD project_id ON TABLE project_file TYPE string;
        DEFINE FIELD filename ON TABLE project_file TYPE string;
        DEFINE FIELD original_filename ON TABLE project_file TYPE string;
        DEFINE FIELD content_type ON TABLE project_file TYPE string;
        DEFINE FIELD size_bytes ON TABLE project_file TYPE int;
        DEFINE FIELD minio_key ON TABLE project_file TYPE string;
        DEFINE FIELD uploaded_at ON TABLE project_file TYPE datetime VALUE time::now();
        DEFINE FIELD processed ON TABLE project_file TYPE bool DEFAULT false;
        DEFINE FIELD vector_indexed ON TABLE project_file TYPE bool DEFAULT false;
        DEFINE FIELD processing_error ON TABLE project_file TYPE option<string>;
        DEFINE INDEX idx_project_file_id ON TABLE project_file COLUMNS id UNIQUE;
        DEFINE INDEX idx_project_file_project ON TABLE project_file COLUMNS project_id;
        """,
        # Project-conversation relationship table
        """
        DEFINE TABLE project_conversation SCHEMAFULL;
        DEFINE FIELD project_id ON TABLE project_conversation TYPE string;
        DEFINE FIELD conversation_id ON TABLE project_conversation TYPE string;
        DEFINE FIELD created_at ON TABLE project_conversation TYPE datetime VALUE time::now();
        """,
        # Artifact table
        """
        DEFINE TABLE artifact SCHEMAFULL;
        DEFINE FIELD id ON TABLE artifact TYPE string;
        DEFINE FIELD title ON TABLE artifact TYPE string;
        DEFINE FIELD artifact_type ON TABLE artifact TYPE string;
        DEFINE FIELD language ON TABLE artifact TYPE option<string>;
        DEFINE FIELD content ON TABLE artifact TYPE string;
        DEFINE FIELD preview ON TABLE artifact TYPE string;
        DEFINE FIELD conversation_id ON TABLE artifact TYPE option<string>;
        DEFINE FIELD project_id ON TABLE artifact TYPE option<string>;
        DEFINE FIELD created_at ON TABLE artifact TYPE datetime VALUE time::now();
        DEFINE FIELD updated_at ON TABLE artifact TYPE datetime VALUE time::now();
        DEFINE INDEX idx_artifact_id ON TABLE artifact COLUMNS id UNIQUE;
        DEFINE INDEX idx_artifact_conversation ON TABLE artifact COLUMNS conversation_id;
        DEFINE INDEX idx_artifact_project ON TABLE artifact COLUMNS project_id;
        """,
    ]

    for query in queries:
        try:
            await execute_query(query.strip())
        except Exception as e:
            # Table/index may already exist
            logger.debug(f"Schema initialization note: {e}")


async def upsert_video(video: VideoRecord) -> dict:
    """Create or update a video record.

    Uses SurrealDB record ID syntax for efficient upserts.

    Args:
        video: VideoRecord to upsert

    Returns:
        Query result with created record
    """
    # Use record ID syntax: UPSERT video:[$video_id]
    # This handles both insert and update atomically
    query = """
    UPSERT type::thing('video', $video_id) SET
        video_id = $video_id,
        url = $url,
        fetched_at = $fetched_at,
        title = $title,
        channel_id = $channel_id,
        channel_name = $channel_name,
        duration_seconds = $duration_seconds,
        view_count = $view_count,
        published_at = $published_at,
        source_type = $source_type,
        import_method = $import_method,
        recommendation_weight = $recommendation_weight,
        pipeline_state = $pipeline_state,
        embedding = $embedding,
        archive_path = $archive_path,
        last_processed_at = $last_processed_at,
        updated_at = time::now();
    """

    # Pass datetime objects directly - SurrealDB Python client handles serialization
    params = {
        "video_id": video.video_id,
        "url": video.url,
        "fetched_at": video.fetched_at,
        "title": video.title,
        "channel_id": video.channel_id,
        "channel_name": video.channel_name,
        "duration_seconds": video.duration_seconds,
        "view_count": video.view_count,
        "published_at": video.published_at,
        "source_type": video.source_type,
        "import_method": video.import_method,
        "recommendation_weight": video.recommendation_weight or 1.0,
        "pipeline_state": video.pipeline_state or {},
        "embedding": video.embedding,
        "archive_path": video.archive_path,
        "last_processed_at": video.last_processed_at,
    }

    result = await execute_query(query, params)
    return {"created": len(result) > 0}


async def get_video(video_id: str) -> Optional[VideoRecord]:
    """Get a video by ID.

    Args:
        video_id: YouTube video ID

    Returns:
        VideoRecord if found, None otherwise
    """
    query = "SELECT * FROM video WHERE video_id = $video_id LIMIT 1;"

    results = await execute_query(query, {"video_id": video_id})
    if not results:
        return None

    record = results[0]
    return VideoRecord(
        video_id=record.get("video_id"),
        url=record.get("url"),
        fetched_at=_parse_datetime(record.get("fetched_at")),
        title=record.get("title"),
        channel_id=record.get("channel_id"),
        channel_name=record.get("channel_name"),
        duration_seconds=record.get("duration_seconds"),
        view_count=record.get("view_count"),
        published_at=_parse_datetime_optional(record.get("published_at")),
        source_type=record.get("source_type"),
        import_method=record.get("import_method"),
        recommendation_weight=record.get("recommendation_weight", 1.0),
        pipeline_state=record.get("pipeline_state") or {},
        embedding=record.get("embedding"),
        archive_path=record.get("archive_path"),
        last_processed_at=_parse_datetime_optional(record.get("last_processed_at")),
        created_at=_parse_datetime(record.get("created_at")),
        updated_at=_parse_datetime(record.get("updated_at")),
    )


async def update_pipeline_state(
    video_id: str,
    step_name: str,
    version_hash: str,
) -> dict:
    """Update the pipeline state for a specific step.

    Tracks which version of each processing step has been run on a video,
    enabling efficient backfill queries.

    Args:
        video_id: YouTube video ID
        step_name: Pipeline step name (e.g., "transcript", "tags", "embeddings")
        version_hash: Git-based hash of the step code

    Returns:
        Query result
    """
    query = """
    UPDATE video SET
        pipeline_state[$(step_name)] = $(version_hash),
        last_processed_at = time::now(),
        updated_at = time::now()
    WHERE video_id = $(video_id);
    """

    result = await execute_query(query, {
        "video_id": video_id,
        "step_name": step_name,
        "version_hash": version_hash,
    })
    return {"updated": len(result) > 0}


async def find_stale_videos(
    step_name: str,
    current_version: str,
    limit: int = 100,
) -> list[StaleVideoResult]:
    """Find videos that need reprocessing for a specific step.

    Returns videos where:
    1. The step has never been run (pipeline_state doesn't have the step)
    2. The step was run with an outdated version

    Args:
        step_name: Pipeline step name
        current_version: Current version hash of the step
        limit: Maximum number of results

    Returns:
        List of stale videos needing reprocessing
    """
    query = """
    SELECT
        video_id,
        url,
        pipeline_state.$(step_name) AS current_version
    FROM video
    ORDER BY updated_at ASC
    LIMIT $(limit);
    """

    results = await execute_query(query, {
        "step_name": step_name,
        "limit": limit,
    })

    stale = []
    for r in results:
        video_version = r.get("current_version")
        if video_version != current_version:
            stale.append(StaleVideoResult(
                video_id=r.get("video_id"),
                url=r.get("url"),
                current_version=video_version,
                required_version=current_version,
                step_name=step_name,
            ))

    return stale


async def link_video_to_channel(
    video_id: str,
    channel_id: str,
    channel_name: str,
) -> dict:
    """Create or update channel and link video to it.

    Args:
        video_id: YouTube video ID
        channel_id: YouTube channel ID
        channel_name: Channel display name

    Returns:
        Query result
    """
    # Upsert channel
    channel_query = """
    UPSERT channel SET
        channel_id = $channel_id,
        channel_name = $channel_name,
        updated_at = time::now()
    WHERE channel_id = $channel_id;
    """

    await execute_query(channel_query, {
        "channel_id": channel_id,
        "channel_name": channel_name,
    })

    # Create relationship
    rel_query = """
    INSERT INTO video_channel {
        video_id: $video_id,
        channel_id: $channel_id
    };
    """

    result = await execute_query(rel_query, {
        "video_id": video_id,
        "channel_id": channel_id,
    })

    return {"linked": len(result) > 0}


async def link_video_to_topics(
    video_id: str,
    topics: list[str],
) -> dict:
    """Create topic nodes and link to video.

    Args:
        video_id: YouTube video ID
        topics: List of topic/tag names

    Returns:
        Query result
    """
    for topic_name in topics:
        normalized = topic_name.lower().strip()

        # Upsert topic
        topic_query = """
        UPSERT topic SET
            name = $name,
            normalized_name = $normalized_name,
            updated_at = time::now()
        WHERE normalized_name = $normalized_name;
        """

        await execute_query(topic_query, {
            "name": topic_name,
            "normalized_name": normalized,
        })

        # Create relationship
        rel_query = """
        INSERT INTO video_topic {
            video_id: $video_id,
            topic_id: $normalized_name
        };
        """

        await execute_query(rel_query, {
            "video_id": video_id,
            "normalized_name": normalized,
        })

    return {"linked": len(topics) > 0}


async def semantic_search(
    embedding: list[float],
    limit: int = 10,
) -> list[VectorSearchResult]:
    """Search for similar videos using vector embeddings.

    Uses SurrealDB vector similarity to find semantically similar content.

    Args:
        embedding: Vector embedding (float list)
        limit: Maximum number of results

    Returns:
        List of similar videos with similarity scores
    """
    query = """
    SELECT
        video_id,
        title,
        url,
        channel_name,
        archive_path,
        vector::similarity::cosine(embedding, $embedding) AS similarity_score
    FROM video
    WHERE embedding IS NOT NONE AND array::len(embedding) > 0
    ORDER BY similarity_score DESC
    LIMIT $limit;
    """

    results = await execute_query(query, {
        "embedding": embedding,
        "limit": limit,
    })

    search_results = []
    for r in results:
        search_results.append(VectorSearchResult(
            video_id=r.get("video_id"),
            title=r.get("title", ""),
            url=r.get("url", ""),
            similarity_score=float(r.get("similarity_score", 0.0)),
            channel_name=r.get("channel_name"),
            archive_path=r.get("archive_path"),
        ))

    return search_results


async def get_video_count() -> int:
    """Get total number of videos in the database."""
    query = "SELECT COUNT() AS count FROM video GROUP ALL;"
    results = await execute_query(query)
    return int(results[0].get("count", 0)) if results else 0


async def get_channel_count() -> int:
    """Get total number of channels in the database."""
    query = "SELECT COUNT() AS count FROM channel GROUP ALL;"
    results = await execute_query(query)
    return int(results[0].get("count", 0)) if results else 0


async def get_topic_count() -> int:
    """Get total number of topics in the database."""
    query = "SELECT COUNT() AS count FROM topic GROUP ALL;"
    results = await execute_query(query)
    return int(results[0].get("count", 0)) if results else 0


# =============================================================================
# Video Chunk Operations (for fine-grained semantic search)
# =============================================================================


async def upsert_chunk(chunk: VideoChunkRecord) -> dict:
    """Create or update a video chunk.

    Args:
        chunk: VideoChunkRecord to upsert

    Returns:
        Query result with created record
    """
    query = """
    UPSERT type::thing('video_chunk', $chunk_id) SET
        chunk_id = $chunk_id,
        video_id = $video_id,
        chunk_index = $chunk_index,
        text = $text,
        start_time = $start_time,
        end_time = $end_time,
        token_count = $token_count,
        embedding = $embedding;
    """

    params = {
        "chunk_id": chunk.chunk_id,
        "video_id": chunk.video_id,
        "chunk_index": chunk.chunk_index,
        "text": chunk.text,
        "start_time": chunk.start_time,
        "end_time": chunk.end_time,
        "token_count": chunk.token_count,
        "embedding": chunk.embedding,
    }

    result = await execute_query(query, params)
    return {"created": len(result) > 0}


async def upsert_chunks(chunks: list[VideoChunkRecord]) -> int:
    """Upsert multiple chunks for a video.

    Args:
        chunks: List of VideoChunkRecord to upsert

    Returns:
        Number of chunks upserted
    """
    count = 0
    for chunk in chunks:
        await upsert_chunk(chunk)
        count += 1
    return count


async def get_chunks_for_video(video_id: str) -> list[VideoChunkRecord]:
    """Get all chunks for a video, ordered by chunk_index.

    Args:
        video_id: YouTube video ID

    Returns:
        List of VideoChunkRecord ordered by chunk_index
    """
    query = """
    SELECT * FROM video_chunk
    WHERE video_id = $video_id
    ORDER BY chunk_index ASC;
    """

    results = await execute_query(query, {"video_id": video_id})

    chunks = []
    for r in results:
        chunks.append(VideoChunkRecord(
            chunk_id=r.get("chunk_id"),
            video_id=r.get("video_id"),
            chunk_index=r.get("chunk_index"),
            text=r.get("text"),
            start_time=r.get("start_time"),
            end_time=r.get("end_time"),
            token_count=r.get("token_count"),
            embedding=r.get("embedding"),
            created_at=_parse_datetime(r.get("created_at")),
        ))

    return chunks


async def delete_chunks_for_video(video_id: str) -> int:
    """Delete all chunks for a video.

    Args:
        video_id: YouTube video ID

    Returns:
        Number of chunks deleted
    """
    query = "DELETE FROM video_chunk WHERE video_id = $video_id RETURN BEFORE;"
    results = await execute_query(query, {"video_id": video_id})
    return len(results) if results else 0


async def semantic_search_chunks(
    embedding: list[float],
    limit: int = 10,
) -> list[ChunkSearchResult]:
    """Search for similar chunks using vector embeddings.

    Enables timestamp-level search: "find where they discussed X"

    Args:
        embedding: Query embedding vector
        limit: Maximum number of results

    Returns:
        List of matching chunks with similarity scores and parent video info
    """
    query = """
    SELECT
        chunk_id,
        video_id,
        chunk_index,
        text,
        start_time,
        end_time,
        vector::similarity::cosine(embedding, $embedding) AS similarity_score,
        (SELECT title, url FROM video WHERE video_id = $parent.video_id)[0] AS parent_video
    FROM video_chunk
    WHERE embedding IS NOT NONE AND array::len(embedding) > 0
    ORDER BY similarity_score DESC
    LIMIT $limit;
    """

    results = await execute_query(query, {
        "embedding": embedding,
        "limit": limit,
    })

    search_results = []
    for r in results:
        parent = r.get("parent_video") or {}
        search_results.append(ChunkSearchResult(
            chunk_id=r.get("chunk_id"),
            video_id=r.get("video_id"),
            chunk_index=r.get("chunk_index"),
            text=r.get("text", ""),
            start_time=float(r.get("start_time", 0)),
            end_time=float(r.get("end_time", 0)),
            similarity_score=float(r.get("similarity_score", 0)),
            video_title=parent.get("title"),
            video_url=parent.get("url"),
        ))

    return search_results


async def get_chunk_count() -> int:
    """Get total number of chunks in the database."""
    query = "SELECT COUNT() AS count FROM video_chunk GROUP ALL;"
    results = await execute_query(query)
    return int(results[0].get("count", 0)) if results else 0


# =============================================================================
# Validation and Migration Helpers
# =============================================================================


async def get_random_video_ids(limit: int = 10) -> list[str]:
    """Get random video IDs for sampling validation.

    Args:
        limit: Maximum number of random video IDs to return

    Returns:
        List of random video IDs
    """
    query = """
    SELECT video_id FROM video
    ORDER BY rand()
    LIMIT $limit;
    """

    results = await execute_query(query, {"limit": limit})
    return [r.get("video_id") for r in results if r.get("video_id")]


async def get_all_video_ids() -> list[str]:
    """Get all video IDs from the database.

    Useful for comparing archive contents with database records.

    Returns:
        List of all video IDs
    """
    query = "SELECT video_id FROM video;"
    results = await execute_query(query)
    return [r.get("video_id") for r in results if r.get("video_id")]


# =============================================================================
# Vector Search (SurrealDB Migration - Phase 1)
# =============================================================================


async def search_videos_by_embedding(
    query_embedding: list[float],
    limit: int = 10,
    offset: int = 0,
    channel_filter: str | None = None,
    min_date: datetime | None = None,
    max_date: datetime | None = None,
) -> list[dict]:
    """Search videos by embedding similarity using HNSW index.

    Uses SurrealDB's native vector similarity search with cosine distance.

    Args:
        query_embedding: Query embedding vector (1024-dim, gte-large-en-v1.5)
        limit: Maximum number of results (default: 10)
        offset: Skip first N results for pagination (default: 0)
        channel_filter: Filter by channel_name (optional)
        min_date: Filter by created_at >= min_date (optional)
        max_date: Filter by created_at <= max_date (optional)

    Returns:
        List of video records with similarity scores, ordered by score DESC

    Raises:
        ValueError: If embedding dimension is incorrect or parameters invalid
    """
    # Validate inputs
    if len(query_embedding) != 1024:
        raise ValueError(
            f"Embedding dimension must be 1024, got {len(query_embedding)}"
        )

    if limit < 0:
        raise ValueError(f"limit must be non-negative, got {limit}")

    if offset < 0:
        raise ValueError(f"offset must be non-negative, got {offset}")

    if min_date and max_date and min_date > max_date:
        raise ValueError("min_date must be <= max_date")

    # Build query with optional filters
    where_clauses = ["embedding IS NOT NONE"]

    if channel_filter:
        where_clauses.append("channel_name = $channel_filter")

    if min_date:
        where_clauses.append("created_at >= $min_date")

    if max_date:
        where_clauses.append("created_at <= $max_date")

    where_clause = " AND ".join(where_clauses)

    query = f"""
    SELECT
        video_id,
        title,
        url,
        channel_name,
        created_at,
        archive_path,
        vector::similarity::cosine(embedding, $query_embedding) AS score
    FROM video
    WHERE {where_clause}
    ORDER BY score DESC
    LIMIT $limit
    START $offset;
    """

    params = {
        "query_embedding": query_embedding,
        "limit": limit,
        "offset": offset,
    }

    if channel_filter:
        params["channel_filter"] = channel_filter

    if min_date:
        params["min_date"] = min_date

    if max_date:
        params["max_date"] = max_date

    results = await execute_query(query, params)
    return results


async def search_videos_by_text(
    query_text: str,
    limit: int = 10,
    offset: int = 0,
    channel_filter: str | None = None,
) -> list[dict]:
    """Search videos by text - generates embedding and searches.

    Integrates with Infinity API to generate embeddings from text queries,
    then performs vector similarity search.

    Args:
        query_text: Text query to search for
        limit: Maximum number of results (default: 10)
        offset: Skip first N results for pagination (default: 0)
        channel_filter: Filter by channel_name (optional)

    Returns:
        List of video records with similarity scores, ordered by score DESC

    Raises:
        ValueError: If query_text is empty or parameters invalid
        Exception: If Infinity API call fails
    """
    import httpx

    # Validate input
    if not query_text or not query_text.strip():
        raise ValueError("query_text cannot be empty")

    if limit < 0:
        raise ValueError(f"limit must be non-negative, got {limit}")

    if offset < 0:
        raise ValueError(f"offset must be non-negative, got {offset}")

    # Generate embedding using Infinity API
    infinity_url = "http://192.168.16.241:7997/embeddings"
    model = "Alibaba-NLP/gte-large-en-v1.5"

    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                infinity_url,
                json={
                    "model": model,
                    "input": [query_text],
                },
            )
            response.raise_for_status()

            data = response.json()
            query_embedding = data["data"][0]["embedding"]

    except httpx.HTTPError as e:
        logger.error(f"Infinity API call failed: {e}")
        raise Exception(f"Failed to generate embedding: {e}")
    except (KeyError, IndexError) as e:
        logger.error(f"Unexpected Infinity API response format: {e}")
        raise Exception(f"Invalid response from embedding service: {e}")

    # Use embedding search
    return await search_videos_by_embedding(
        query_embedding=query_embedding,
        limit=limit,
        offset=offset,
        channel_filter=channel_filter,
    )
