"""Fixtures for integration tests.

These tests require remote services on 192.168.16.241:
- SurrealDB: port 8080
- Infinity: port 7997
- Ollama: port 11434
"""

import os
import pytest

# Remote service URLs (GPU server)
REMOTE_INFINITY_URL = "http://192.168.16.241:7997"
REMOTE_OLLAMA_URL = "http://192.168.16.241:11434"
REMOTE_SURREALDB_URL = "ws://192.168.16.241:8080"


@pytest.fixture
def infinity_url():
    """Remote Infinity embedding service URL."""
    return os.getenv("INFINITY_URL", REMOTE_INFINITY_URL)


@pytest.fixture
def ollama_url():
    """Remote Ollama URL."""
    return os.getenv("OLLAMA_URL", REMOTE_OLLAMA_URL)


@pytest.fixture
def surrealdb_url():
    """Remote SurrealDB URL."""
    return os.getenv("SURREALDB_URL", REMOTE_SURREALDB_URL)
