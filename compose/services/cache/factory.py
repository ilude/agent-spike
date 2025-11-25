"""Factory functions for creating cache instances with sensible defaults."""

from .in_memory_cache import InMemoryCache


def create_in_memory_cache() -> InMemoryCache:
    """Factory function to create InMemoryCache for testing.

    This cache has no persistence and is useful for unit tests
    and development without requiring SurrealDB.

    Returns:
        InMemoryCache instance

    Example:
        >>> # For testing
        >>> cache = create_in_memory_cache()
        >>> cache.set("test", {"data": "value"})
        >>> assert cache.get("test") == {"data": "value"}
    """
    return InMemoryCache()
