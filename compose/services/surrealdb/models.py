"""Pydantic models for SurrealDB data structures.

Models for:
- VideoRecord: Video with embeddings and archive path
- ChannelRecord: YouTube channels
- TopicRecord: Tags/topics for semantic clustering
"""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


class VideoRecord(BaseModel):
    """Video record with embeddings and pipeline tracking.

    Extends the Neo4j VideoNode with:
    - embedding: Vector embedding for similarity search
    - archive_path: Location of archived data
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
    pipeline_state: dict[str, str] = Field(default_factory=dict)

    # Vector embedding for similarity search
    embedding: Optional[list[float]] = None

    # Archive path for data retrieval
    archive_path: Optional[str] = None

    # Processing timestamps
    last_processed_at: Optional[datetime] = None
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)

    class Config:
        """Pydantic configuration."""

        use_enum_values = True


class ChannelRecord(BaseModel):
    """YouTube channel record for recommendations and clustering."""

    channel_id: str
    channel_name: str
    video_count: int = 0
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)


class TopicRecord(BaseModel):
    """Topic/tag record for semantic clustering."""

    name: str
    normalized_name: str  # Lowercase, trimmed
    video_count: int = 0
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)


class PipelineStepState(BaseModel):
    """Tracks the version of a pipeline step that was run on a video."""

    step_name: str
    version_hash: str
    processed_at: datetime
    success: bool = True
    error_message: Optional[str] = None


class StaleVideoResult(BaseModel):
    """Result from querying videos that need reprocessing."""

    video_id: str
    url: str
    current_version: Optional[str] = None
    required_version: str
    step_name: str


class VectorSearchResult(BaseModel):
    """Result from vector similarity search."""

    video_id: str
    title: str
    url: str
    similarity_score: float
    channel_name: Optional[str] = None
    archive_path: Optional[str] = None
