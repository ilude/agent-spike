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

    cache_dir: Path
    collection_name: str = "cached_content"
    embedding_model: str = "all-MiniLM-L6-v2"
    # Future: Add connection strings for remote Qdrant, Redis, etc.
    # remote_url: Optional[str] = None
    # api_key: Optional[str] = None
