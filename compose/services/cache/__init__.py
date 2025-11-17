"""Cache service for lesson-007: Content caching with dependency injection.

This module provides:
- CacheManager protocol (interface for dependency injection)
- QdrantCache implementation (vector database with semantic search)
- InMemoryCache implementation (for testing)
- Data models for structured caching
- Factory functions for creating cache instances

Example:
    >>> from tools.services.cache import create_qdrant_cache
    >>> cache = create_qdrant_cache(collection_name="content")
    >>> cache.set("key1", {"data": "value"}, metadata={"type": "youtube"})
    >>> result = cache.get("key1")
"""

from .cache_manager import CacheManager
from .in_memory_cache import InMemoryCache
from .models import CacheEntry, CacheMetadata
from .config import CacheConfig

# Lazy import for Qdrant to avoid requiring dependencies for all users
try:
    from .qdrant_cache import QdrantCache
    _QDRANT_AVAILABLE = True
except ImportError:
    _QDRANT_AVAILABLE = False
    QdrantCache = None  # type: ignore

# Factory functions
from .factory import create_in_memory_cache

if _QDRANT_AVAILABLE:
    from .factory import create_qdrant_cache
else:
    create_qdrant_cache = None  # type: ignore

__all__ = [
    "CacheManager",
    "QdrantCache",
    "InMemoryCache",
    "CacheEntry",
    "CacheMetadata",
    "CacheConfig",
    "create_qdrant_cache",
    "create_in_memory_cache",
]
