"""Qdrant implementation of CacheManager protocol.

This module provides a production-ready cache implementation using Qdrant
vector database for storage, with support for semantic search and metadata filtering.
"""

import hashlib
import json
import os
from pathlib import Path
from typing import Any, Optional
from datetime import datetime
import uuid

from qdrant_client import QdrantClient
from qdrant_client.models import (
    Distance,
    VectorParams,
    PointStruct,
    Filter,
    FieldCondition,
    MatchValue,
    SearchParams,
)
from sentence_transformers import SentenceTransformer


class QdrantCache:
    """Qdrant-based cache implementation with semantic search.

    This implementation stores cached data in Qdrant with optional embeddings
    for semantic search. It supports:
    - Exact key-value lookups
    - Semantic search by content
    - Metadata filtering
    - Persistent storage

    Example:
        >>> cache = QdrantCache(collection_name="content")
        >>> cache.set("key1", {"data": "AI agents tutorial"}, {"type": "youtube"})
        >>> results = cache.search("artificial intelligence tutorial", limit=5)
    """

    def __init__(
        self,
        collection_name: str = "content",
        cache_dir: Optional[Path] = None,
        embedding_model: str = "all-MiniLM-L6-v2",
    ):
        """Initialize Qdrant cache.

        Args:
            collection_name: Name of the Qdrant collection
            cache_dir: Directory for Qdrant storage (default: projects/data/qdrant)
            embedding_model: SentenceTransformer model for embeddings
        """
        if cache_dir is None:
            # Default to projects/data/qdrant in project root
            cache_dir = Path(__file__).parent.parent.parent.parent / "projects" / "data" / "qdrant"

        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.collection_name = collection_name

        # Initialize Qdrant client (local mode)
        self.client = QdrantClient(path=str(self.cache_dir))

        # Initialize embedding model
        self._embedding_model_name = embedding_model
        self._embedding_model: Optional[SentenceTransformer] = None  # Lazy load

        # Create collection if it doesn't exist
        self._ensure_collection()

    def _ensure_collection(self):
        """Ensure the collection exists, create if not."""
        collections = self.client.get_collections().collections
        collection_names = [c.name for c in collections]

        if self.collection_name not in collection_names:
            # Get embedding dimension
            embedding_dim = self._get_embedding_dim()

            self.client.create_collection(
                collection_name=self.collection_name,
                vectors_config=VectorParams(
                    size=embedding_dim,
                    distance=Distance.COSINE
                )
            )

    def _get_embedding_model(self) -> SentenceTransformer:
        """Lazy load embedding model."""
        if self._embedding_model is None:
            self._embedding_model = SentenceTransformer(self._embedding_model_name)
        return self._embedding_model

    def _get_embedding_dim(self) -> int:
        """Get embedding dimension for the model."""
        model = self._get_embedding_model()
        # Get dimension from a test encoding
        test_embedding = model.encode("test")
        return len(test_embedding)

    def _generate_embedding(self, text: str) -> list[float]:
        """Generate embedding vector for text.

        Args:
            text: Text to embed

        Returns:
            Embedding vector as list of floats
        """
        model = self._get_embedding_model()
        embedding = model.encode(text)
        return embedding.tolist()

    def _key_to_id(self, key: str) -> str:
        """Convert cache key to Qdrant point ID.

        Uses SHA-256 hash for deterministic IDs.

        Args:
            key: Cache key

        Returns:
            Deterministic UUID string
        """
        # Use first 32 chars of hex digest to create UUID
        hash_hex = hashlib.sha256(key.encode()).hexdigest()[:32]
        return str(uuid.UUID(hash_hex))

    def get(self, key: str) -> Optional[dict[str, Any]]:
        """Retrieve cached data by exact key.

        Args:
            key: Unique identifier for the cached item

        Returns:
            Dictionary containing cached data, or None if not found
        """
        point_id = self._key_to_id(key)

        try:
            points = self.client.retrieve(
                collection_name=self.collection_name,
                ids=[point_id]
            )

            if not points:
                return None

            payload = points[0].payload
            if payload and "value" in payload:
                return payload["value"]

            return None

        except Exception:
            return None

    def set(
        self,
        key: str,
        value: dict[str, Any],
        metadata: Optional[dict[str, Any]] = None
    ) -> None:
        """Store data in cache with optional metadata.

        Args:
            key: Unique identifier for the cached item
            value: Data to store (must be JSON-serializable dict)
            metadata: Optional metadata for filtering/searching
        """
        point_id = self._key_to_id(key)

        # Generate embedding from searchable content
        # Try to find text content in value for embedding
        searchable_text = self._extract_searchable_text(value)
        vector = self._generate_embedding(searchable_text)

        # Build payload
        payload = {
            "key": key,
            "value": value,
            "cached_at": datetime.now().isoformat(),
        }

        # Add metadata if provided
        if metadata:
            payload["metadata"] = metadata
            # Flatten metadata for filtering
            for k, v in metadata.items():
                payload[f"meta_{k}"] = v

        # Upsert point
        self.client.upsert(
            collection_name=self.collection_name,
            points=[
                PointStruct(
                    id=point_id,
                    vector=vector,
                    payload=payload
                )
            ]
        )

    def _extract_searchable_text(self, value: dict[str, Any]) -> str:
        """Extract text content from value for embedding.

        Looks for common text fields: transcript, markdown, content, description, etc.

        Args:
            value: Cache value dictionary

        Returns:
            Text content for embedding
        """
        # Try common text fields
        text_fields = ["transcript", "markdown", "content", "text", "description", "title"]

        for field in text_fields:
            if field in value and isinstance(value[field], str):
                return value[field]

        # Fallback: JSON dump (not ideal but works)
        return json.dumps(value)

    def exists(self, key: str) -> bool:
        """Check if key exists in cache.

        Args:
            key: Unique identifier to check

        Returns:
            True if key exists in cache, False otherwise
        """
        result = self.get(key)
        return result is not None

    def delete(self, key: str) -> bool:
        """Delete an item from cache.

        Args:
            key: Unique identifier of item to delete

        Returns:
            True if item was deleted, False if not found
        """
        point_id = self._key_to_id(key)

        try:
            self.client.delete(
                collection_name=self.collection_name,
                points_selector=[point_id]
            )
            return True
        except Exception:
            return False

    def search(
        self,
        query: str,
        limit: int = 10,
        filters: Optional[dict[str, Any]] = None
    ) -> list[dict[str, Any]]:
        """Semantic search with optional metadata filters.

        Args:
            query: Search query string
            limit: Maximum number of results to return
            filters: Optional metadata filters (e.g., {"type": "youtube_video"})

        Returns:
            List of matching items with their data and metadata
        """
        # Generate query embedding
        query_vector = self._generate_embedding(query)

        # Build filter if provided
        qdrant_filter = None
        if filters:
            conditions = []
            for key, value in filters.items():
                conditions.append(
                    FieldCondition(
                        key=f"meta_{key}",
                        match=MatchValue(value=value)
                    )
                )
            if conditions:
                qdrant_filter = Filter(must=conditions)

        # Search
        results = self.client.search(
            collection_name=self.collection_name,
            query_vector=query_vector,
            limit=limit,
            query_filter=qdrant_filter
        )

        # Extract and return values
        output = []
        for hit in results:
            if hit.payload and "value" in hit.payload:
                item = hit.payload["value"].copy()
                item["_score"] = hit.score
                item["_metadata"] = hit.payload.get("metadata", {})
                output.append(item)

        return output

    def filter(
        self,
        conditions: dict[str, Any],
        limit: int = 100
    ) -> list[dict[str, Any]]:
        """Filter by metadata without semantic search.

        Args:
            conditions: Metadata conditions (e.g., {"type": "youtube_video"})
            limit: Maximum number of results to return

        Returns:
            List of matching items
        """
        # Build filter conditions
        filter_conditions = []
        for key, value in conditions.items():
            filter_conditions.append(
                FieldCondition(
                    key=f"meta_{key}",
                    match=MatchValue(value=value)
                )
            )

        qdrant_filter = Filter(must=filter_conditions) if filter_conditions else None

        # Scroll through results (no vector search, just filter)
        results, _ = self.client.scroll(
            collection_name=self.collection_name,
            scroll_filter=qdrant_filter,
            limit=limit
        )

        # Extract values
        output = []
        for point in results:
            if point.payload and "value" in point.payload:
                item = point.payload["value"].copy()
                item["_metadata"] = point.payload.get("metadata", {})
                output.append(item)

        return output

    def count(self) -> int:
        """Get total number of items in cache.

        Returns:
            Number of items stored
        """
        collection_info = self.client.get_collection(self.collection_name)
        return collection_info.points_count

    def clear(self) -> None:
        """Clear all items from cache."""
        self.client.delete_collection(self.collection_name)
        self._ensure_collection()
