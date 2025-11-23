"""Dual-collection cache for content + chunks embeddings.

This module provides a wrapper around QdrantCache that manages two collections:
- `content`: One global embedding per item (for recommendations)
- `content_chunks`: Multiple chunk embeddings per item (for precise search)

Example:
    >>> from compose.services.cache import create_dual_collection_cache
    >>> cache = create_dual_collection_cache()
    >>>
    >>> # Store global content
    >>> cache.set_content("video:abc123", video_data, metadata)
    >>>
    >>> # Store chunks
    >>> for chunk in chunks:
    ...     cache.set_chunk(chunk, metadata)
    >>>
    >>> # Search chunks (precise)
    >>> results = cache.search_chunks("specific topic", limit=10)
    >>>
    >>> # Search content (thematic)
    >>> results = cache.search_content("general theme", limit=10)
"""

from dataclasses import dataclass
from typing import Any, Optional

from .config import CacheConfig
from .qdrant_cache import QdrantCache


@dataclass
class DualCollectionConfig:
    """Configuration for dual-collection cache.

    Attributes:
        content_collection: Name of global content collection (default: "content")
        chunks_collection: Name of chunks collection (default: "content_chunks")
        qdrant_url: Qdrant HTTP URL (default: "http://localhost:6335")
        infinity_url: Infinity embedding service URL (default: "http://localhost:7997")
        global_model: Model for global embeddings (default: gte-large-en-v1.5)
        chunk_model: Model for chunk embeddings (default: bge-m3)
        cache_dir: Local cache directory (for fallback)
    """

    content_collection: str = "content"
    chunks_collection: str = "content_chunks"
    qdrant_url: str = "http://localhost:6335"
    infinity_url: str = "http://localhost:7997"
    global_model: str = "Alibaba-NLP/gte-large-en-v1.5"
    chunk_model: str = "BAAI/bge-m3"
    cache_dir: str = "compose/data/qdrant_storage"


class DualCollectionCache:
    """Manages two Qdrant collections for content and chunks.

    This enables different retrieval modes:
    - Search mode: Query chunks collection for precise passage matching
    - Recommendation mode: Query content collection for thematic matching

    The two collections use different embedding models optimized for their purpose:
    - Global (gte-large): Better at capturing overall document themes
    - Chunks (bge-m3): Better at matching specific passages/queries
    """

    def __init__(self, config: Optional[DualCollectionConfig] = None):
        """Initialize dual-collection cache.

        Args:
            config: Configuration for both collections (uses defaults if None)
        """
        self.config = config or DualCollectionConfig()

        # Create content (global) cache
        content_config = CacheConfig(
            collection_name=self.config.content_collection,
            qdrant_url=self.config.qdrant_url,
            infinity_url=self.config.infinity_url,
            infinity_model=self.config.global_model,
            cache_dir=self.config.cache_dir,
        )
        self._content_cache = QdrantCache(content_config)

        # Create chunks cache
        chunks_config = CacheConfig(
            collection_name=self.config.chunks_collection,
            qdrant_url=self.config.qdrant_url,
            infinity_url=self.config.infinity_url,
            infinity_model=self.config.chunk_model,
            cache_dir=self.config.cache_dir,
        )
        self._chunks_cache = QdrantCache(chunks_config)

    # =========================================================================
    # Content (Global) Operations
    # =========================================================================

    def set_content(
        self,
        key: str,
        value: dict[str, Any],
        metadata: Optional[dict[str, Any]] = None,
    ) -> None:
        """Store item with global embedding in content collection.

        Use this for whole-document embeddings that capture overall themes.
        One entry per video/document.

        Args:
            key: Unique identifier (e.g., "youtube:video:abc123")
            value: Data to store (should include transcript/content)
            metadata: Optional metadata for filtering
        """
        self._content_cache.set(key, value, metadata)

    def get_content(self, key: str) -> Optional[dict[str, Any]]:
        """Retrieve content by exact key.

        Args:
            key: Unique identifier

        Returns:
            Stored data or None if not found
        """
        return self._content_cache.get(key)

    def content_exists(self, key: str) -> bool:
        """Check if content exists.

        Args:
            key: Unique identifier

        Returns:
            True if exists
        """
        return self._content_cache.exists(key)

    def search_content(
        self,
        query: str,
        limit: int = 10,
        filters: Optional[dict[str, Any]] = None,
    ) -> list[dict[str, Any]]:
        """Search content collection (thematic/recommendation mode).

        Best for: "Find videos similar to this topic"

        Args:
            query: Search query
            limit: Maximum results
            filters: Optional metadata filters

        Returns:
            List of matching items with scores
        """
        return self._content_cache.search(query, limit, filters)

    def delete_content(self, key: str) -> bool:
        """Delete content by key.

        Args:
            key: Unique identifier

        Returns:
            True if deleted
        """
        return self._content_cache.delete(key)

    # =========================================================================
    # Chunks Operations
    # =========================================================================

    def set_chunk(
        self,
        chunk_key: str,
        chunk_data: dict[str, Any],
        metadata: Optional[dict[str, Any]] = None,
    ) -> None:
        """Store a single chunk with its embedding.

        Use this for chunk-level embeddings that capture specific passages.
        Multiple entries per video/document.

        Args:
            chunk_key: Unique chunk identifier (e.g., "youtube:chunk:abc123:0")
            chunk_data: Chunk data (must include 'text' field)
            metadata: Should include 'parent_video_id' for lookups
        """
        self._chunks_cache.set(chunk_key, chunk_data, metadata)

    def set_chunks(
        self,
        parent_key: str,
        chunks: list[dict[str, Any]],
        base_metadata: Optional[dict[str, Any]] = None,
    ) -> int:
        """Store multiple chunks for a single parent item.

        Convenience method for storing all chunks at once.

        Args:
            parent_key: Parent item key (e.g., "youtube:video:abc123")
            chunks: List of chunk dicts with 'text', 'chunk_index', etc.
            base_metadata: Metadata to apply to all chunks

        Returns:
            Number of chunks stored
        """
        count = 0
        for chunk in chunks:
            chunk_index = chunk.get("chunk_index", count)
            chunk_key = f"{parent_key}:chunk:{chunk_index}"

            # Build chunk metadata
            metadata = dict(base_metadata) if base_metadata else {}
            metadata["parent_key"] = parent_key
            metadata["chunk_index"] = chunk_index

            # Add timing info if available
            if "start_time" in chunk:
                metadata["start_time"] = chunk["start_time"]
            if "end_time" in chunk:
                metadata["end_time"] = chunk["end_time"]

            self._chunks_cache.set(chunk_key, chunk, metadata)
            count += 1

        return count

    def get_chunk(self, chunk_key: str) -> Optional[dict[str, Any]]:
        """Retrieve chunk by exact key.

        Args:
            chunk_key: Unique chunk identifier

        Returns:
            Chunk data or None
        """
        return self._chunks_cache.get(chunk_key)

    def search_chunks(
        self,
        query: str,
        limit: int = 10,
        filters: Optional[dict[str, Any]] = None,
    ) -> list[dict[str, Any]]:
        """Search chunks collection (precise passage matching).

        Best for: "Find where they talked about X"

        Args:
            query: Search query
            limit: Maximum results
            filters: Optional metadata filters

        Returns:
            List of matching chunks with scores and timestamps
        """
        return self._chunks_cache.search(query, limit, filters)

    def get_chunks_for_parent(
        self,
        parent_key: str,
        limit: int = 100,
    ) -> list[dict[str, Any]]:
        """Get all chunks for a parent item.

        Args:
            parent_key: Parent item key
            limit: Maximum chunks to return

        Returns:
            List of chunks sorted by chunk_index
        """
        chunks = self._chunks_cache.filter({"parent_key": parent_key}, limit=limit)

        # Sort by chunk index
        chunks.sort(key=lambda c: c.get("chunk_index", 0))

        return chunks

    def delete_chunks_for_parent(self, parent_key: str) -> int:
        """Delete all chunks for a parent item.

        Args:
            parent_key: Parent item key

        Returns:
            Number of chunks deleted
        """
        chunks = self.get_chunks_for_parent(parent_key)
        count = 0

        for chunk in chunks:
            chunk_index = chunk.get("chunk_index", count)
            chunk_key = f"{parent_key}:chunk:{chunk_index}"
            if self._chunks_cache.delete(chunk_key):
                count += 1

        return count

    # =========================================================================
    # Combined Operations
    # =========================================================================

    def delete_all_for_key(self, key: str) -> tuple[bool, int]:
        """Delete content and all associated chunks.

        Args:
            key: Content key

        Returns:
            Tuple of (content_deleted, chunks_deleted_count)
        """
        content_deleted = self.delete_content(key)
        chunks_deleted = self.delete_chunks_for_parent(key)
        return content_deleted, chunks_deleted

    def count_content(self) -> int:
        """Get count of items in content collection."""
        return self._content_cache.count()

    def count_chunks(self) -> int:
        """Get count of items in chunks collection."""
        return self._chunks_cache.count()

    def close(self) -> None:
        """Close both cache connections."""
        self._content_cache.close()
        self._chunks_cache.close()


def create_dual_collection_cache(
    config: Optional[DualCollectionConfig] = None,
    **kwargs,
) -> DualCollectionCache:
    """Factory function to create DualCollectionCache.

    Args:
        config: Full configuration object
        **kwargs: Override individual config fields

    Returns:
        Configured DualCollectionCache instance

    Example:
        >>> # Use defaults
        >>> cache = create_dual_collection_cache()
        >>>
        >>> # Override specific settings
        >>> cache = create_dual_collection_cache(
        ...     qdrant_url="http://192.168.16.241:6335",
        ...     infinity_url="http://192.168.16.241:7997",
        ... )
    """
    if config is None:
        config = DualCollectionConfig(**kwargs)
    elif kwargs:
        # Merge kwargs into config
        config_dict = {
            "content_collection": config.content_collection,
            "chunks_collection": config.chunks_collection,
            "qdrant_url": config.qdrant_url,
            "infinity_url": config.infinity_url,
            "global_model": config.global_model,
            "chunk_model": config.chunk_model,
            "cache_dir": config.cache_dir,
        }
        config_dict.update(kwargs)
        config = DualCollectionConfig(**config_dict)

    return DualCollectionCache(config)
