"""
Mem0 configuration for agent memory management.

This module provides simple configuration helpers for the Mem0 memory layer.

Note: Mem0 uses default configuration with environment variables:
- OPENAI_API_KEY for LLM and embeddings
- Default paths: ~/.mem0/qdrant (vector store), ~/.mem0/history.db (history)
- Default models: gpt-4o-mini (LLM), text-embedding-3-small (embeddings)
"""

import os


def ensure_api_key() -> str:
    """
    Ensure OpenAI API key is available.

    Returns:
        OpenAI API key from environment

    Raises:
        ValueError: If OPENAI_API_KEY is not set
    """
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise ValueError(
            "OPENAI_API_KEY not found in environment. "
            "Mem0 requires OpenAI API for embeddings. "
            "Please set OPENAI_API_KEY or copy .env from lesson-001."
        )
    return api_key
