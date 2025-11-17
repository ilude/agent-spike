"""Data models for cache entries and metadata."""

from datetime import datetime
from typing import Any, Optional
from pydantic import BaseModel, Field


class CacheMetadata(BaseModel):
    """Metadata attached to cached items for filtering and search.

    This model defines common metadata fields that can be used to filter
    and organize cached content. Additional fields can be added via the
    `extra` dictionary.
    """

    type: str = Field(..., description="Content type (e.g., 'youtube_video', 'webpage')")
    source: Optional[str] = Field(None, description="Source of the content (e.g., 'Nate Jones', 'docling')")
    created_at: datetime = Field(default_factory=datetime.now, description="When this item was cached")
    tags: list[str] = Field(default_factory=list, description="Tags for categorization")
    extra: dict[str, Any] = Field(default_factory=dict, description="Additional metadata fields")

    class Config:
        """Pydantic configuration."""
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


class CacheEntry(BaseModel):
    """Complete cache entry including key, value, and metadata.

    This model represents a full cache entry as stored in the cache backend.

    Note: Currently not used in practice - scripts use plain dicts instead.
    Kept for backwards compatibility but may be removed in future.
    """

    key: str = Field(..., description="Unique cache key")
    value: dict[str, Any] = Field(..., description="Cached data")
    metadata: Optional[CacheMetadata] = Field(None, description="Optional metadata for filtering")
    vector: Optional[list[float]] = Field(None, description="Embedding vector for semantic search")

    class Config:
        """Pydantic configuration."""
        arbitrary_types_allowed = True
