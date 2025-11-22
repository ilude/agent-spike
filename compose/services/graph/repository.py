"""Neo4j repository for pipeline state tracking and backfill queries.

Provides CRUD operations for:
- Video nodes with pipeline state
- Channel and Topic relationships
- Efficient backfill queries for stale videos
"""

import json
from datetime import datetime
from typing import Optional

from .driver import execute_query, execute_write, get_session
from .models import VideoNode, ChannelNode, TopicNode, StaleVideoResult


def init_schema() -> None:
    """Initialize Neo4j schema with constraints and indexes.

    Creates:
    - Unique constraint on Video.video_id
    - Unique constraint on Channel.channel_id
    - Unique constraint on Topic.normalized_name
    - Index on Video.pipeline_state for backfill queries
    """
    queries = [
        "CREATE CONSTRAINT video_id IF NOT EXISTS FOR (v:Video) REQUIRE v.video_id IS UNIQUE",
        "CREATE CONSTRAINT channel_id IF NOT EXISTS FOR (c:Channel) REQUIRE c.channel_id IS UNIQUE",
        "CREATE CONSTRAINT topic_name IF NOT EXISTS FOR (t:Topic) REQUIRE t.normalized_name IS UNIQUE",
        "CREATE INDEX video_updated IF NOT EXISTS FOR (v:Video) ON (v.updated_at)",
        "CREATE INDEX video_channel IF NOT EXISTS FOR (v:Video) ON (v.channel_id)",
    ]

    for query in queries:
        try:
            execute_write(query)
        except Exception:
            pass  # Constraint/index may already exist


def upsert_video(video: VideoNode) -> dict:
    """Create or update a video node.

    Args:
        video: VideoNode to upsert

    Returns:
        Query summary
    """
    query = """
    MERGE (v:Video {video_id: $video_id})
    ON CREATE SET v.created_at = datetime()
    SET v.url = $url,
        v.fetched_at = datetime($fetched_at),
        v.title = $title,
        v.channel_id = $channel_id,
        v.channel_name = $channel_name,
        v.duration_seconds = $duration_seconds,
        v.view_count = $view_count,
        v.published_at = CASE WHEN $published_at IS NOT NULL THEN datetime($published_at) ELSE NULL END,
        v.source_type = $source_type,
        v.import_method = $import_method,
        v.recommendation_weight = $recommendation_weight,
        v.pipeline_state = $pipeline_state_json,
        v.last_processed_at = CASE WHEN $last_processed_at IS NOT NULL THEN datetime($last_processed_at) ELSE NULL END,
        v.updated_at = datetime()
    RETURN v
    """

    params = {
        "video_id": video.video_id,
        "url": video.url,
        "fetched_at": video.fetched_at.isoformat(),
        "title": video.title,
        "channel_id": video.channel_id,
        "channel_name": video.channel_name,
        "duration_seconds": video.duration_seconds,
        "view_count": video.view_count,
        "published_at": video.published_at.isoformat() if video.published_at else None,
        "source_type": video.source_type,
        "import_method": video.import_method,
        "recommendation_weight": video.recommendation_weight,
        "pipeline_state_json": json.dumps(video.pipeline_state),
        "last_processed_at": video.last_processed_at.isoformat() if video.last_processed_at else None,
    }

    return execute_write(query, params)


def get_video(video_id: str) -> Optional[VideoNode]:
    """Get a video by ID.

    Args:
        video_id: YouTube video ID

    Returns:
        VideoNode if found, None otherwise
    """
    query = """
    MATCH (v:Video {video_id: $video_id})
    RETURN v
    """

    results = execute_query(query, {"video_id": video_id})
    if not results:
        return None

    node = results[0]["v"]
    return VideoNode(
        video_id=node["video_id"],
        url=node["url"],
        fetched_at=node["fetched_at"].to_native(),
        title=node.get("title"),
        channel_id=node.get("channel_id"),
        channel_name=node.get("channel_name"),
        duration_seconds=node.get("duration_seconds"),
        view_count=node.get("view_count"),
        published_at=node["published_at"].to_native() if node.get("published_at") else None,
        source_type=node.get("source_type"),
        import_method=node.get("import_method"),
        recommendation_weight=node.get("recommendation_weight", 1.0),
        pipeline_state=json.loads(node.get("pipeline_state", "{}")) if node.get("pipeline_state") else {},
        last_processed_at=node["last_processed_at"].to_native() if node.get("last_processed_at") else None,
        created_at=node["created_at"].to_native(),
        updated_at=node["updated_at"].to_native(),
    )


def update_pipeline_state(video_id: str, step_name: str, version_hash: str) -> dict:
    """Update the pipeline state for a specific step.

    This is the key operation for tracking what version of each step
    has been run on a video.

    Args:
        video_id: YouTube video ID
        step_name: Pipeline step name (e.g., "transcript", "tags", "embeddings")
        version_hash: Git-based hash of the step code

    Returns:
        Query summary
    """
    # Read current state, update, write back (JSON string workaround)
    read_query = """
    MATCH (v:Video {video_id: $video_id})
    RETURN v.pipeline_state AS pipeline_state
    """
    results = execute_query(read_query, {"video_id": video_id})
    if not results:
        return {"nodes_created": 0, "properties_set": 0}

    current_state = json.loads(results[0].get("pipeline_state", "{}") or "{}")
    current_state[step_name] = version_hash

    write_query = """
    MATCH (v:Video {video_id: $video_id})
    SET v.pipeline_state = $pipeline_state_json,
        v.last_processed_at = datetime(),
        v.updated_at = datetime()
    RETURN v
    """

    return execute_write(write_query, {
        "video_id": video_id,
        "pipeline_state_json": json.dumps(current_state),
    })


def find_stale_videos(
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
    # Fetch all videos and filter in Python (pipeline_state is JSON string)
    query = """
    MATCH (v:Video)
    RETURN v.video_id AS video_id,
           v.url AS url,
           v.pipeline_state AS pipeline_state
    ORDER BY v.updated_at ASC
    """

    results = execute_query(query)
    stale = []

    for r in results:
        if len(stale) >= limit:
            break

        pipeline_state = json.loads(r.get("pipeline_state", "{}") or "{}")
        video_version = pipeline_state.get(step_name)

        # Video is stale if step never ran or version is outdated
        if video_version != current_version:
            stale.append(StaleVideoResult(
                video_id=r["video_id"],
                url=r["url"],
                current_version=video_version,
                required_version=current_version,
                step_name=step_name,
            ))

    return stale


def count_stale_videos(step_name: str, current_version: str) -> int:
    """Count videos needing reprocessing for a step.

    Args:
        step_name: Pipeline step name
        current_version: Current version hash

    Returns:
        Count of stale videos
    """
    # Fetch all videos and count in Python (pipeline_state is JSON string)
    query = """
    MATCH (v:Video)
    RETURN v.pipeline_state AS pipeline_state
    """

    results = execute_query(query)
    count = 0

    for r in results:
        pipeline_state = json.loads(r.get("pipeline_state", "{}") or "{}")
        video_version = pipeline_state.get(step_name)
        if video_version != current_version:
            count += 1

    return count


def link_video_to_channel(video_id: str, channel_id: str, channel_name: str) -> dict:
    """Create or update channel relationship.

    Args:
        video_id: YouTube video ID
        channel_id: YouTube channel ID
        channel_name: Channel display name

    Returns:
        Query summary
    """
    query = """
    MATCH (v:Video {video_id: $video_id})
    MERGE (c:Channel {channel_id: $channel_id})
    ON CREATE SET c.channel_name = $channel_name, c.video_count = 0, c.created_at = datetime()
    MERGE (v)-[:FROM_CHANNEL]->(c)
    SET c.video_count = c.video_count + 1
    RETURN c
    """

    return execute_write(query, {
        "video_id": video_id,
        "channel_id": channel_id,
        "channel_name": channel_name,
    })


def link_video_to_topics(video_id: str, topics: list[str]) -> dict:
    """Create topic nodes and link to video.

    Args:
        video_id: YouTube video ID
        topics: List of topic/tag names

    Returns:
        Query summary
    """
    query = """
    MATCH (v:Video {video_id: $video_id})
    UNWIND $topics AS topic_name
    MERGE (t:Topic {normalized_name: toLower(trim(topic_name))})
    ON CREATE SET t.name = trim(topic_name), t.video_count = 0, t.created_at = datetime()
    MERGE (v)-[:HAS_TOPIC]->(t)
    SET t.video_count = t.video_count + 1
    RETURN t
    """

    return execute_write(query, {
        "video_id": video_id,
        "topics": topics,
    })


def get_video_count() -> int:
    """Get total number of videos in the graph."""
    results = execute_query("MATCH (v:Video) RETURN count(v) AS count")
    return results[0]["count"] if results else 0


def get_channel_count() -> int:
    """Get total number of channels in the graph."""
    results = execute_query("MATCH (c:Channel) RETURN count(c) AS count")
    return results[0]["count"] if results else 0


def get_topic_count() -> int:
    """Get total number of topics in the graph."""
    results = execute_query("MATCH (t:Topic) RETURN count(t) AS count")
    return results[0]["count"] if results else 0
