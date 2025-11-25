"""Embedding service for generating vector embeddings via Infinity.

Provides a simple interface for generating embeddings without
coupling to any specific storage backend.
"""

import httpx
from typing import Optional


class EmbeddingService:
    """Generate embeddings via Infinity HTTP API.

    Example:
        >>> service = EmbeddingService()
        >>> embedding = service.embed("Hello world")
        >>> len(embedding)
        1024
    """

    def __init__(
        self,
        infinity_url: str = "http://localhost:7997",
        model: str = "BAAI/bge-m3",
        timeout: float = 120.0,
    ):
        self.infinity_url = infinity_url
        self.model = model
        self.timeout = timeout

    def embed(self, text: str) -> list[float]:
        """Generate embedding for text.

        Args:
            text: Text to embed

        Returns:
            Embedding vector as list of floats

        Raises:
            ConnectionError: If Infinity service unavailable
        """
        try:
            response = httpx.post(
                f"{self.infinity_url}/embeddings",
                json={"model": self.model, "input": [text]},
                timeout=self.timeout,
            )
            response.raise_for_status()
            data = response.json()
            return data["data"][0]["embedding"]
        except httpx.HTTPError as e:
            raise ConnectionError(f"Infinity service error: {e}")

    def embed_batch(self, texts: list[str]) -> list[list[float]]:
        """Generate embeddings for multiple texts.

        Args:
            texts: List of texts to embed

        Returns:
            List of embedding vectors
        """
        try:
            response = httpx.post(
                f"{self.infinity_url}/embeddings",
                json={"model": self.model, "input": texts},
                timeout=self.timeout,
            )
            response.raise_for_status()
            data = response.json()
            return [item["embedding"] for item in data["data"]]
        except httpx.HTTPError as e:
            raise ConnectionError(f"Infinity service error: {e}")


# Default instances for common models
_global_embedder: Optional[EmbeddingService] = None
_chunk_embedder: Optional[EmbeddingService] = None


def get_global_embedder(infinity_url: str = "http://localhost:7997") -> EmbeddingService:
    """Get embedder for global/document-level embeddings (gte-large)."""
    global _global_embedder
    if _global_embedder is None:
        _global_embedder = EmbeddingService(
            infinity_url=infinity_url,
            model="Alibaba-NLP/gte-large-en-v1.5",
        )
    return _global_embedder


def get_chunk_embedder(infinity_url: str = "http://localhost:7997") -> EmbeddingService:
    """Get embedder for chunk-level embeddings (bge-m3)."""
    global _chunk_embedder
    if _chunk_embedder is None:
        _chunk_embedder = EmbeddingService(
            infinity_url=infinity_url,
            model="BAAI/bge-m3",
        )
    return _chunk_embedder

def get_embedding_sync(
    text: str,
    infinity_url: Optional[str] = None,
    model: str = "Alibaba-NLP/gte-large-en-v1.5",
) -> list[float]:
    """Synchronous helper to get embedding for text.

    Args:
        text: Text to embed
        infinity_url: Optional Infinity service URL
        model: Embedding model to use

    Returns:
        Embedding vector as list of floats
    """
    url = infinity_url or "http://localhost:7997"

    if model == "Alibaba-NLP/gte-large-en-v1.5":
        embedder = get_global_embedder(url)
    elif model == "BAAI/bge-m3":
        embedder = get_chunk_embedder(url)
    else:
        embedder = EmbeddingService(infinity_url=url, model=model)

    return embedder.embed(text)

