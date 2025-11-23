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
    StaleVideoResult,
    TopicRecord,
    VideoRecord,
    VectorSearchResult,
)

logger = logging.getLogger(__name__)


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
        fetched_at=datetime.fromisoformat(record.get("fetched_at", datetime.now().isoformat())),
        title=record.get("title"),
        channel_id=record.get("channel_id"),
        channel_name=record.get("channel_name"),
        duration_seconds=record.get("duration_seconds"),
        view_count=record.get("view_count"),
        published_at=(
            datetime.fromisoformat(record.get("published_at"))
            if record.get("published_at")
            else None
        ),
        source_type=record.get("source_type"),
        import_method=record.get("import_method"),
        recommendation_weight=record.get("recommendation_weight", 1.0),
        pipeline_state=record.get("pipeline_state") or {},
        embedding=record.get("embedding"),
        archive_path=record.get("archive_path"),
        last_processed_at=(
            datetime.fromisoformat(record.get("last_processed_at"))
            if record.get("last_processed_at")
            else None
        ),
        created_at=datetime.fromisoformat(record.get("created_at", datetime.now().isoformat())),
        updated_at=datetime.fromisoformat(record.get("updated_at", datetime.now().isoformat())),
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
