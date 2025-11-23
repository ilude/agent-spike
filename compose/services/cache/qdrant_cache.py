"""Qdrant implementation of CacheManager protocol.

This module provides a production-ready cache implementation using Qdrant
vector database for storage, with support for semantic search and metadata filtering.
"""

import hashlib
import json
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
    FilterSelector,
    MatchExcept,
)

try:
    from sentence_transformers import SentenceTransformer
    _SENTENCE_TRANSFORMERS_AVAILABLE = True
except ImportError:
    _SENTENCE_TRANSFORMERS_AVAILABLE = False

try:
    import httpx
    _HTTPX_AVAILABLE = True
except ImportError:
    _HTTPX_AVAILABLE = False

from .config import CacheConfig


class QdrantCache:
    """Qdrant-based cache implementation with semantic search.

    This implementation stores cached data in Qdrant with optional embeddings
    for semantic search. It supports:
    - Exact key-value lookups
    - Semantic search by content
    - Metadata filtering
    - Persistent storage

    Example:
        >>> from compose.services.cache import create_qdrant_cache
        >>> cache = create_qdrant_cache(collection_name="content")
        >>> cache.set("key1", {"data": "AI agents tutorial"}, {"type": "youtube"})
        >>> results = cache.search("artificial intelligence tutorial", limit=5)
    """

    def __init__(self, config: CacheConfig):
        """Initialize Qdrant cache.

        Args:
            config: Cache configuration with cache_dir, collection_name, etc.
        """
        self.config = config
        self.cache_dir = Path(config.cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.collection_name = config.collection_name

        # Initialize Qdrant client (container mode preferred, fallback to local)
        if config.qdrant_url:
            # Use Qdrant container via HTTP
            self.client = QdrantClient(url=config.qdrant_url)
        else:
            # Fallback to local file-based storage (legacy mode)
            self.client = QdrantClient(path=str(self.cache_dir))

        # Initialize embedding model (lazy load)
        self._embedding_model_name = config.embedding_model
        self._embedding_model: Optional[SentenceTransformer] = None

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
        """Lazy load embedding model (only used if no Infinity URL)."""
        if not _SENTENCE_TRANSFORMERS_AVAILABLE:
            raise ImportError(
                "sentence-transformers is required for local embeddings. "
                "Either install it or configure infinity_url for remote embeddings."
            )
        if self._embedding_model is None:
            self._embedding_model = SentenceTransformer(self._embedding_model_name)
        return self._embedding_model

    def _get_embedding_dim(self) -> int:
        """Get embedding dimension for the model."""
        if self.config.infinity_url:
            # bge-m3 model dimension
            if "bge-m3" in self.config.infinity_model:
                return 1024
            # gte-large dimension
            elif "gte-large" in self.config.infinity_model:
                return 1024
            # Default: try to get from Infinity API
            test_embedding = self._generate_embedding("test")
            return len(test_embedding)
        else:
            # Local model
            model = self._get_embedding_model()
            test_embedding = model.encode("test")
            return len(test_embedding)

    def _generate_embedding(self, text: str) -> list[float]:
        """Generate embedding vector for text.

        Uses Infinity HTTP API if configured, otherwise falls back to local model.

        Args:
            text: Text to embed

        Returns:
            Embedding vector as list of floats
        """
        if self.config.infinity_url:
            # Use Infinity HTTP API
            return self._generate_embedding_via_infinity(text)
        else:
            # Use local sentence-transformers model
            model = self._get_embedding_model()
            embedding = model.encode(text)
            return embedding.tolist()

    def _generate_embedding_via_infinity(self, text: str) -> list[float]:
        """Generate embedding via Infinity HTTP API.

        Args:
            text: Text to embed

        Returns:
            Embedding vector as list of floats

        Raises:
            ConnectionError: If cannot connect to Infinity service
            ValueError: If response format is unexpected
        """
        if not _HTTPX_AVAILABLE:
            raise ImportError(
                "httpx is required for Infinity embeddings. "
                "Install with: uv sync --group platform-api"
            )

        try:
            response = httpx.post(
                f"{self.config.infinity_url}/embeddings",
                json={
                    "model": self.config.infinity_model,
                    "input": [text]
                },
                timeout=120.0  # CPU embedding can be slow for large texts
            )
            response.raise_for_status()

            data = response.json()

            # Extract embedding from response
            # Infinity format: {"data": [{"embedding": [0.1, 0.2, ...]}]}
            if "data" not in data or not data["data"]:
                raise ValueError(f"Unexpected Infinity response format: {data}")

            embedding = data["data"][0]["embedding"]
            return embedding

        except httpx.HTTPError as e:
            raise ConnectionError(f"Failed to connect to Infinity service: {e}")
        except (KeyError, IndexError) as e:
            raise ValueError(f"Unexpected response format from Infinity: {e}")

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

    def _extract_searchable_text(self, value: dict[str, Any], max_chars: int = 8000) -> str:
        """Extract text content from value for embedding.

        Looks for common text fields: transcript, markdown, content, description, etc.
        Truncates to max_chars to stay within model context limits.

        Args:
            value: Cache value dictionary
            max_chars: Maximum characters for embedding (default 8K for gte-large context)

        Returns:
            Text content for embedding (truncated if needed)
        """
        # Try common text fields
        text_fields = ["transcript", "markdown", "content", "text", "description", "title"]

        text = None
        for field in text_fields:
            if field in value and isinstance(value[field], str):
                text = value[field]
                break

        if text is None:
            # Fallback: JSON dump (not ideal but works)
            text = json.dumps(value)

        # Truncate to stay within model context limits
        if len(text) > max_chars:
            text = text[:max_chars] + "..."

        return text

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

        # Search using query_points (replaces deprecated search method)
        results = self.client.query_points(
            collection_name=self.collection_name,
            query=query_vector,
            limit=limit,
            query_filter=qdrant_filter
        )

        # Extract and return values
        output = []
        for hit in results.points:
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
        """Clear all items from cache.

        Scrolls through all points and deletes them by ID for reliability
        with embedded Qdrant on Windows.
        """
        # Scroll through all points and collect IDs
        all_ids = []
        offset = None

        while True:
            results, offset = self.client.scroll(
                collection_name=self.collection_name,
                limit=100,
                offset=offset,
                with_payload=False,
                with_vectors=False,
            )
            if not results:
                break
            all_ids.extend([p.id for p in results])
            if offset is None:
                break

        # Delete all points by ID
        if all_ids:
            self.client.delete(
                collection_name=self.collection_name,
                points_selector=all_ids,
            )

    def close(self) -> None:
        """Close the Qdrant client connection.

        This is important on Windows to release file locks on SQLite databases.
        """
        if hasattr(self, 'client') and self.client:
            try:
                self.client.close()
            except Exception:
                pass  # Ignore errors during close
