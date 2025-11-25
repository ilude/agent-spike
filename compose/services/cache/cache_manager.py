"""Cache Manager protocol for dependency injection.

This module defines the CacheManager interface that allows tools to optionally
use caching without hard dependencies on specific cache implementations.

The protocol uses structural subtyping (duck typing), so any class that implements
these methods can be used as a cache manager.
"""

from typing import Protocol, Optional, Any


class CacheManager(Protocol):
    """Cache interface for dependency injection.

    This protocol defines the contract that all cache implementations must follow.
    Tools can accept an optional CacheManager parameter and will work with any
    implementation that provides these methods.

    Example usage:
        >>> def get_data(url: str, cache: Optional[CacheManager] = None) -> str:
        ...     if cache and cache.exists(url):
        ...         return cache.get(url)["data"]
        ...     data = fetch_from_api(url)
        ...     if cache:
        ...         cache.set(url, {"data": data})
        ...     return data
    """

    def get(self, key: str) -> Optional[dict[str, Any]]:
        """Retrieve cached data by exact key.

        Args:
            key: Unique identifier for the cached item

        Returns:
            Dictionary containing cached data, or None if not found
        """
        ...

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
        ...

    def exists(self, key: str) -> bool:
        """Check if key exists in cache without loading data.

        Args:
            key: Unique identifier to check

        Returns:
            True if key exists in cache, False otherwise
        """
        ...

    def delete(self, key: str) -> bool:
        """Delete an item from cache.

        Args:
            key: Unique identifier of item to delete

        Returns:
            True if item was deleted, False if not found
        """
        ...

    def search(
        self,
        query: str,
        limit: int = 10,
        filters: Optional[dict[str, Any]] = None
    ) -> list[dict[str, Any]]:
        """Semantic search with optional metadata filters.

        Note: This method is optional for basic caching implementations.
        Vector-based implementations (like SurrealDB) can provide semantic search.

        Args:
            query: Search query string
            limit: Maximum number of results to return
            filters: Optional metadata filters (e.g., {"type": "youtube_video"})

        Returns:
            List of matching items with their data and metadata
        """
        ...

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
        ...
