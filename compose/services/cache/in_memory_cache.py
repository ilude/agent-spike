"""In-memory cache implementation for testing.

This implementation stores cached data in Python dictionaries (no persistence).
Useful for unit tests and development without requiring Qdrant.
"""

from typing import Any, Optional
from datetime import datetime
import re


class InMemoryCache:
    """In-memory cache implementation (no persistence).

    This implementation is useful for:
    - Unit testing without external dependencies
    - Development/prototyping
    - Temporary caching needs

    Note: Does not support semantic search (uses simple text matching instead).

    Example:
        >>> from compose.services.cache import create_in_memory_cache
        >>> cache = create_in_memory_cache()
        >>> cache.set("key1", {"data": "value"})
        >>> result = cache.get("key1")
    """

    def __init__(self):
        """Initialize in-memory cache."""
        self._storage: dict[str, dict[str, Any]] = {}

    def get(self, key: str) -> Optional[dict[str, Any]]:
        """Retrieve cached data by exact key.

        Args:
            key: Unique identifier for the cached item

        Returns:
            Dictionary containing cached data, or None if not found
        """
        entry = self._storage.get(key)
        if entry:
            return entry.get("value")
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
        self._storage[key] = {
            "key": key,
            "value": value,
            "metadata": metadata or {},
            "cached_at": datetime.now().isoformat(),
        }

    def exists(self, key: str) -> bool:
        """Check if key exists in cache.

        Args:
            key: Unique identifier to check

        Returns:
            True if key exists in cache, False otherwise
        """
        return key in self._storage

    def delete(self, key: str) -> bool:
        """Delete an item from cache.

        Args:
            key: Unique identifier of item to delete

        Returns:
            True if item was deleted, False if not found
        """
        if key in self._storage:
            del self._storage[key]
            return True
        return False

    def search(
        self,
        query: str,
        limit: int = 10,
        filters: Optional[dict[str, Any]] = None
    ) -> list[dict[str, Any]]:
        """Simple text search (not semantic).

        Note: This is NOT semantic search like Qdrant. It uses simple
        case-insensitive text matching as a fallback.

        Args:
            query: Search query string
            limit: Maximum number of results to return
            filters: Optional metadata filters (e.g., {"type": "youtube_video"})

        Returns:
            List of matching items with their data and metadata
        """
        results = []
        query_lower = query.lower()

        for entry in self._storage.values():
            # Check metadata filters first
            if filters:
                metadata = entry.get("metadata", {})
                if not all(metadata.get(k) == v for k, v in filters.items()):
                    continue

            # Simple text matching in value
            value = entry["value"]
            text_content = self._extract_text(value)

            if query_lower in text_content.lower():
                item = value.copy()
                item["_score"] = 1.0  # Fake score for compatibility
                item["_metadata"] = entry.get("metadata", {})
                results.append(item)

            if len(results) >= limit:
                break

        return results[:limit]

    def filter(
        self,
        conditions: dict[str, Any],
        limit: int = 100
    ) -> list[dict[str, Any]]:
        """Filter by metadata.

        Args:
            conditions: Metadata conditions (e.g., {"type": "youtube_video"})
            limit: Maximum number of results to return

        Returns:
            List of matching items
        """
        results = []

        for entry in self._storage.values():
            metadata = entry.get("metadata", {})

            # Check if all conditions match
            if all(metadata.get(k) == v for k, v in conditions.items()):
                item = entry["value"].copy()
                item["_metadata"] = metadata
                results.append(item)

            if len(results) >= limit:
                break

        return results[:limit]

    def count(self) -> int:
        """Get total number of items in cache.

        Returns:
            Number of items stored
        """
        return len(self._storage)

    def clear(self) -> None:
        """Clear all items from cache."""
        self._storage.clear()

    def _extract_text(self, value: dict[str, Any]) -> str:
        """Extract text content from value.

        Args:
            value: Cache value dictionary

        Returns:
            Combined text content
        """
        text_fields = ["transcript", "markdown", "content", "text", "description", "title"]
        parts = []

        for field in text_fields:
            if field in value and isinstance(value[field], str):
                parts.append(value[field])

        return " ".join(parts)
