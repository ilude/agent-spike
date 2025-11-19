"""Configuration for cache services."""

from dataclasses import dataclass
from pathlib import Path
from typing import Optional


@dataclass
class CacheConfig:
    """Configuration for cache implementations.

    This config uses dependency injection to make cache implementations
    testable and flexible.

    Example:
        >>> config = CacheConfig(
        ...     cache_dir=Path("./data/cache"),
        ...     collection_name="my_content",
        ...     embedding_model="all-MiniLM-L6-v2"
        ... )
        >>> cache = QdrantCache(config)
    """

    cache_dir: Path  # Used for fallback/legacy local storage
    collection_name: str = "cached_content"
    embedding_model: str = "BAAI/bge-m3"  # Default to bge-m3 (1024-dim, 8K context)
    qdrant_url: Optional[str] = None  # URL for Qdrant server (e.g., "http://qdrant:6333")
    infinity_url: Optional[str] = None  # URL for Infinity embedding server (e.g., "http://infinity:7997")
    infinity_model: str = "BAAI/bge-m3"  # Embedding model to use via Infinity
    # Future: Add API key for remote Qdrant cloud
    # api_key: Optional[str] = None
