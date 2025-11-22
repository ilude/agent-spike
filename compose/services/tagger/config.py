"""Configuration for tag normalization service."""

import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional


# Ollama models available on remote GPU server (192.168.16.241)
OLLAMA_MODELS = {
    "qwen2.5:7b": "ollama:qwen2.5:7b",  # Good for structured JSON output
    "qwen3:8b": "ollama:qwen3:8b",      # Alternative Qwen model
}

# Default to Ollama if available, otherwise Claude Haiku
DEFAULT_MODEL = "ollama:qwen2.5:7b"


def get_ollama_url() -> str:
    """Get Ollama URL from environment or default.

    Returns the base URL for the Ollama OpenAI-compatible API.
    pydantic-ai expects this to be the base URL (it appends /chat/completions).
    """
    base = os.getenv("OLLAMA_URL", "http://192.168.16.241:11434")
    # Ollama's OpenAI-compatible endpoint is at /v1
    if not base.endswith("/v1"):
        base = base.rstrip("/") + "/v1"
    return base


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
        ollama_url: URL for Ollama server (for ollama: models)
    """

    model: str = field(default_factory=lambda: DEFAULT_MODEL)
    vocabulary_path: Optional[Path] = None
    use_semantic_context: bool = True
    use_vocabulary: bool = True
    similar_videos_limit: int = 5

    # Qdrant configuration
    qdrant_collection: str = "cached_content"
    qdrant_path: Optional[Path] = None

    # Ollama configuration
    ollama_url: str = field(default_factory=get_ollama_url)
