"""Cache service for content caching with dependency injection.

This module provides:
- CacheManager protocol (interface for dependency injection)
- InMemoryCache implementation (for testing)
- Data models for structured caching
- Factory functions for creating cache instances

Example:
    >>> from compose.services.cache import create_in_memory_cache
    >>> cache = create_in_memory_cache()
    >>> cache.set("key1", {"data": "value"}, metadata={"type": "youtube"})
    >>> result = cache.get("key1")
"""

from .cache_manager import CacheManager
from .in_memory_cache import InMemoryCache
from .models import CacheEntry, CacheMetadata
from .config import CacheConfig
from .factory import create_in_memory_cache

__all__ = [
    "CacheManager",
    "InMemoryCache",
    "CacheEntry",
    "CacheMetadata",
    "CacheConfig",
    "create_in_memory_cache",
]
