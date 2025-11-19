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
    embedding_model: str = "BAAI/bge-m3",
    qdrant_url: Optional[str] = None,
    infinity_url: Optional[str] = None,
    infinity_model: str = "BAAI/bge-m3"
):
    """Factory function to create QdrantCache with sensible defaults.

    Uses compose/data/qdrant as default cache directory (for local mode).
    Prefers Infinity HTTP API for embeddings if infinity_url is provided.
    Prefers Qdrant container if qdrant_url is provided.

    Args:
        cache_dir: Optional custom cache directory (for local mode)
        collection_name: Qdrant collection name (default: "cached_content")
        embedding_model: Model name (default: "BAAI/bge-m3")
        qdrant_url: URL for Qdrant container (e.g., "http://localhost:6335")
        infinity_url: URL for Infinity embedding server (e.g., "http://localhost:7997")
        infinity_model: Model to use via Infinity (default: "BAAI/bge-m3")

    Returns:
        Configured QdrantCache instance

    Raises:
        ImportError: If qdrant-client is not installed

    Example:
        >>> # Use Infinity + Qdrant containers (recommended)
        >>> cache = create_qdrant_cache(
        ...     qdrant_url="http://localhost:6335",
        ...     infinity_url="http://localhost:7997"
        ... )
        >>>
        >>> # Use local embedded mode (legacy, requires sentence-transformers)
        >>> cache = create_qdrant_cache()
        >>>
        >>> # Custom collection with containers
        >>> cache = create_qdrant_cache(
        ...     collection_name="my_videos",
        ...     qdrant_url="http://localhost:6335",
        ...     infinity_url="http://localhost:7997",
        ...     infinity_model="BAAI/bge-m3"
        ... )
    """
    if not _QDRANT_AVAILABLE:
        raise ImportError(
            "qdrant-client is required for QdrantCache. "
            "Install with: uv sync --group lesson-007"
        )

    if cache_dir is None:
        # Default to compose/data/qdrant in project root
        project_root = Path(__file__).parent.parent.parent.parent
        cache_dir = project_root / "compose" / "data" / "qdrant"

    config = CacheConfig(
        cache_dir=cache_dir,
        collection_name=collection_name,
        embedding_model=embedding_model,
        qdrant_url=qdrant_url,
        infinity_url=infinity_url,
        infinity_model=infinity_model
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
