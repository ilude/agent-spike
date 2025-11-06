"""Cache module for lesson-007: Content caching with dependency injection.

This module provides:
- CacheManager protocol (interface for dependency injection)
- QdrantCache implementation (vector database with semantic search)
- Data models for structured caching

Example:
    >>> from cache import CacheManager, QdrantCache
    >>> cache = QdrantCache(collection_name="content")
    >>> cache.set("key1", {"data": "value"}, metadata={"type": "youtube"})
    >>> result = cache.get("key1")
"""

from .cache_manager import CacheManager
from .qdrant_cache import QdrantCache
from .models import CacheEntry, CacheMetadata

__all__ = [
    "CacheManager",
    "QdrantCache",
    "CacheEntry",
    "CacheMetadata",
]
