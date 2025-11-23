"""Pydantic models for Neo4j graph data structures.

Graph schema:
- Video nodes: Core content with pipeline state tracking
- Channel nodes: YouTube channels for recommendations
- Topic nodes: Tags/topics for semantic clustering
- Relationships track pipeline processing versions
"""

from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field


class PipelineStepState(BaseModel):
    """Tracks the version of a pipeline step that was run on a video."""

    step_name: str
    version_hash: str  # Git-based hash of the step code
    processed_at: datetime
    success: bool = True
    error_message: Optional[str] = None


class VideoNode(BaseModel):
    """Video node with pipeline state for backfill tracking.

    Pipeline state is stored as a dict mapping step names to version hashes.
    When a step's code changes, its version hash changes, and videos with
    outdated hashes need reprocessing.
    """

    video_id: str
    url: str
    fetched_at: datetime

    # YouTube metadata
    title: Optional[str] = None
    channel_id: Optional[str] = None
    channel_name: Optional[str] = None
    duration_seconds: Optional[int] = None
    view_count: Optional[int] = None
    published_at: Optional[datetime] = None

    # Import tracking
    source_type: Optional[str] = None
    import_method: Optional[str] = None
    recommendation_weight: float = 1.0

    # Pipeline state: {step_name: version_hash}
    # This enables efficient backfill queries
    pipeline_state: dict[str, str] = Field(default_factory=dict)

    # Processing timestamps
    last_processed_at: Optional[datetime] = None
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)


class ChannelNode(BaseModel):
    """YouTube channel for recommendations and clustering."""

    channel_id: str
    channel_name: str
    video_count: int = 0
    created_at: datetime = Field(default_factory=datetime.now)


class TopicNode(BaseModel):
    """Topic/tag node for semantic clustering."""

    name: str
    normalized_name: str  # Lowercase, trimmed
    video_count: int = 0
    created_at: datetime = Field(default_factory=datetime.now)


class StaleVideoResult(BaseModel):
    """Result from querying videos that need reprocessing."""

    video_id: str
    url: str
    current_version: Optional[str] = None
    required_version: str
    step_name: str
