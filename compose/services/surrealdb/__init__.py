"""SurrealDB service module for video graph storage and vector search.

Provides:
- Connection management (async with retry logic)
- Pydantic models for VideoRecord, ChannelRecord, TopicRecord
- CRUD operations for videos with pipeline state tracking
- Vector similarity search for content recommendations
"""

from .config import SurrealDBConfig
from .driver import (
    close_db,
    execute_query,
    get_db,
    get_transaction,
    reset_db,
    verify_connection,
)
from .models import (
    ChannelRecord,
    PipelineStepState,
    StaleVideoResult,
    TopicRecord,
    VideoRecord,
    VectorSearchResult,
)
from .repository import (
    find_stale_videos,
    get_channel_count,
    get_topic_count,
    get_video,
    get_video_count,
    init_schema,
    link_video_to_channel,
    link_video_to_topics,
    semantic_search,
    update_pipeline_state,
    upsert_video,
)

__all__ = [
    # Config
    "SurrealDBConfig",
    # Driver
    "get_db",
    "close_db",
    "reset_db",
    "get_transaction",
    "execute_query",
    "verify_connection",
    # Models
    "VideoRecord",
    "ChannelRecord",
    "TopicRecord",
    "PipelineStepState",
    "StaleVideoResult",
    "VectorSearchResult",
    # Repository
    "init_schema",
    "upsert_video",
    "get_video",
    "update_pipeline_state",
    "find_stale_videos",
    "link_video_to_channel",
    "link_video_to_topics",
    "semantic_search",
    "get_video_count",
    "get_channel_count",
    "get_topic_count",
]
