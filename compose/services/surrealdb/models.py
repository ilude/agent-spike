"""Pydantic models for SurrealDB data structures.

Models for:
- VideoRecord: Video with embeddings and archive path
- ChannelRecord: YouTube channels
- TopicRecord: Tags/topics for semantic clustering
"""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field


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

    model_config = ConfigDict(use_enum_values=True)


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


class VideoChunkRecord(BaseModel):
    """Video chunk for fine-grained semantic search.

    Each video can have multiple chunks, enabling timestamp-level search
    ("find where they discussed X").
    """

    chunk_id: str  # Format: {video_id}:{chunk_index}
    video_id: str
    chunk_index: int
    text: str
    start_time: float  # Seconds from video start
    end_time: float
    token_count: int
    embedding: Optional[list[float]] = None
    created_at: datetime = Field(default_factory=datetime.now)

    @property
    def timestamp_range(self) -> str:
        """Human-readable timestamp range."""
        return f"{_format_time(self.start_time)}-{_format_time(self.end_time)}"


class ChunkSearchResult(BaseModel):
    """Result from chunk-level semantic search."""

    chunk_id: str
    video_id: str
    chunk_index: int
    text: str
    start_time: float
    end_time: float
    similarity_score: float
    # Parent video info (optional, from join)
    video_title: Optional[str] = None
    video_url: Optional[str] = None


def _format_time(seconds: float) -> str:
    """Format seconds as MM:SS or H:MM:SS."""
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    secs = int(seconds % 60)
    if hours > 0:
        return f"{hours}:{minutes:02d}:{secs:02d}"
    return f"{minutes}:{secs:02d}"

class ConversationRecord(BaseModel):
    """Conversation record for chat storage."""

    id: Optional[str] = None  # SurrealDB assigns this
    title: str = "New conversation"
    model: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)


class MessageRecord(BaseModel):
    """Message within a conversation."""

    id: Optional[str] = None
    conversation_id: str
    role: str  # "user" or "assistant"
    content: str
    sources: list[dict] = Field(default_factory=list)
    timestamp: datetime = Field(default_factory=datetime.now)


class ProjectRecord(BaseModel):
    """Project for organizing conversations and files."""

    id: Optional[str] = None
    name: str = "New Project"
    description: Optional[str] = None
    custom_instructions: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)


class ProjectFileRecord(BaseModel):
    """File uploaded to a project (metadata only, content in MinIO)."""

    id: Optional[str] = None
    project_id: str
    filename: str
    original_filename: str
    content_type: str
    size_bytes: int
    minio_key: str  # Path in MinIO bucket
    processed: bool = False
    vector_indexed: bool = False
    processing_error: Optional[str] = None
    uploaded_at: datetime = Field(default_factory=datetime.now)


class ProjectConversationRecord(BaseModel):
    """Relationship between project and conversation."""

    id: Optional[str] = None
    project_id: str
    conversation_id: str
    created_at: datetime = Field(default_factory=datetime.now)


class ArtifactRecord(BaseModel):
    """Artifact (canvas document) linked to conversations/projects."""

    id: Optional[str] = None
    title: str
    artifact_type: str = "document"  # "document", "code", "markdown"
    language: Optional[str] = None  # For code artifacts
    content: str
    preview: Optional[str] = None  # First 200 chars
    conversation_id: Optional[str] = None
    project_id: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)


class BackupRecord(BaseModel):
    """Backup job metadata."""

    id: Optional[str] = None
    started_at: datetime = Field(default_factory=datetime.now)
    completed_at: Optional[datetime] = None
    status: str = "running"  # "running", "completed", "failed"
    backup_type: str = "full"  # "full", "incremental"
    minio_path: Optional[str] = None
    size_bytes: Optional[int] = None
    error_message: Optional[str] = None
    tables_backed_up: list[str] = Field(default_factory=list)
