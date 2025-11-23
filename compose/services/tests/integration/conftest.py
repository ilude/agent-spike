"""Fixtures for integration tests.

These tests require remote services on 192.168.16.241:
- Qdrant: port 6333
- Infinity: port 7997
- Ollama: port 11434
"""

import os
import pytest

# Remote service URLs (GPU server)
REMOTE_QDRANT_URL = "http://192.168.16.241:6333"
REMOTE_INFINITY_URL = "http://192.168.16.241:7997"
REMOTE_OLLAMA_URL = "http://192.168.16.241:11434"


@pytest.fixture
def qdrant_url():
    """Remote Qdrant URL."""
    return os.getenv("QDRANT_URL", REMOTE_QDRANT_URL)


@pytest.fixture
def infinity_url():
    """Remote Infinity embedding service URL."""
    return os.getenv("INFINITY_URL", REMOTE_INFINITY_URL)


@pytest.fixture
def ollama_url():
    """Remote Ollama URL."""
    return os.getenv("OLLAMA_URL", REMOTE_OLLAMA_URL)


@pytest.fixture
def collection_name():
    """Default Qdrant collection for cached content."""
    return os.getenv("QDRANT_COLLECTION", "content")
