"""Configuration for tag normalization service."""

from dataclasses import dataclass
from pathlib import Path
from typing import Optional


@dataclass
class TaggerConfig:
    """Configuration for tag normalization service.

    Attributes:
        model: LLM model to use for normalization
        vocabulary_path: Path to vocabulary JSON file (optional)
        use_semantic_context: Enable semantic similarity context
        use_vocabulary: Use canonical vocabulary for normalization
        similar_videos_limit: Number of similar videos for context
        qdrant_collection: Collection name for semantic search
        qdrant_path: Path to Qdrant database (optional)
    """

    model: str = "claude-3-5-haiku-20241022"
    vocabulary_path: Optional[Path] = None
    use_semantic_context: bool = True
    use_vocabulary: bool = True
    similar_videos_limit: int = 5

    # Qdrant configuration
    qdrant_collection: str = "cached_content"
    qdrant_path: Optional[Path] = None
