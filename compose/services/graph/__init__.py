"""Neo4j graph service for pipeline state tracking.

This service tracks:
- Video nodes with pipeline step versions for backfill detection
- Channel and Topic relationships for recommendations
- Efficient queries for finding stale videos

Usage:
    from compose.services.graph import (
        init_schema,
        upsert_video,
        update_pipeline_state,
        find_stale_videos,
        verify_connection,
    )

    # Initialize schema on startup
    init_schema()

    # Update pipeline state after processing
    update_pipeline_state("dQw4w9WgXcQ", "transcript", "abc123")

    # Find videos needing reprocessing
    stale = find_stale_videos("tags", "xyz789", limit=50)
"""

from .driver import (
    get_driver,
    close_driver,
    reset_driver,
    get_session,
    execute_query,
    execute_write,
    verify_connection,
)

from .models import (
    VideoNode,
    ChannelNode,
    TopicNode,
    PipelineStepState,
    StaleVideoResult,
)

from .repository import (
    init_schema,
    upsert_video,
    get_video,
    update_pipeline_state,
    find_stale_videos,
    count_stale_videos,
    link_video_to_channel,
    link_video_to_topics,
    get_video_count,
    get_channel_count,
    get_topic_count,
)

__all__ = [
    # Driver
    "get_driver",
    "close_driver",
    "reset_driver",
    "get_session",
    "execute_query",
    "execute_write",
    "verify_connection",
    # Models
    "VideoNode",
    "ChannelNode",
    "TopicNode",
    "PipelineStepState",
    "StaleVideoResult",
    # Repository
    "init_schema",
    "upsert_video",
    "get_video",
    "update_pipeline_state",
    "find_stale_videos",
    "count_stale_videos",
    "link_video_to_channel",
    "link_video_to_topics",
    "get_video_count",
    "get_channel_count",
    "get_topic_count",
]
