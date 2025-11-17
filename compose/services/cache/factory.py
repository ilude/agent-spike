"""Factory functions for creating cache instances with sensible defaults."""

from pathlib import Path
from typing import Optional

from .config import CacheConfig
from .in_memory_cache import InMemoryCache

# Lazy import for Qdrant to avoid requiring dependencies
try:
    from .qdrant_cache import QdrantCache
    _QDRANT_AVAILABLE = True
except ImportError:
    _QDRANT_AVAILABLE = False


def create_qdrant_cache(
    cache_dir: Optional[Path] = None,
    collection_name: str = "cached_content",
    embedding_model: str = "all-MiniLM-L6-v2"
):
    """Factory function to create QdrantCache with sensible defaults.

    Uses projects/data/qdrant as default cache directory.

    Args:
        cache_dir: Optional custom cache directory
        collection_name: Qdrant collection name (default: "cached_content")
        embedding_model: SentenceTransformer model (default: "all-MiniLM-L6-v2")

    Returns:
        Configured QdrantCache instance

    Raises:
        ImportError: If qdrant-client is not installed

    Example:
        >>> # Use defaults
        >>> cache = create_qdrant_cache()
        >>>
        >>> # Custom collection
        >>> cache = create_qdrant_cache(collection_name="my_videos")
        >>>
        >>> # Custom location
        >>> cache = create_qdrant_cache(cache_dir=Path("/custom/cache"))
    """
    if not _QDRANT_AVAILABLE:
        raise ImportError(
            "qdrant-client is required for QdrantCache. "
            "Install with: uv sync --group lesson-007"
        )

    if cache_dir is None:
        # Default to projects/data/qdrant in project root
        project_root = Path(__file__).parent.parent.parent.parent
        cache_dir = project_root / "projects" / "data" / "qdrant"

    config = CacheConfig(
        cache_dir=cache_dir,
        collection_name=collection_name,
        embedding_model=embedding_model
    )

    return QdrantCache(config)


def create_in_memory_cache() -> InMemoryCache:
    """Factory function to create InMemoryCache for testing.

    This cache has no persistence and is useful for unit tests
    and development without requiring Qdrant.

    Returns:
        InMemoryCache instance

    Example:
        >>> # For testing
        >>> cache = create_in_memory_cache()
        >>> cache.set("test", {"data": "value"})
        >>> assert cache.get("test") == {"data": "value"}
    """
    return InMemoryCache()
