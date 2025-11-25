"""Tests for cache.py using SurrealDBRAG service.

These tests verify the migration from inline semantic_search to SurrealDBRAG service.
Following test-first development approach for Phase 3 of Qdrant → SurrealDB migration.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from fastapi import FastAPI
from fastapi.testclient import TestClient

from compose.api.routers.cache import router


# Create test app
app = FastAPI()
app.include_router(router)


@pytest.fixture
def client():
    """Create test client."""
    return TestClient(app)


@pytest.fixture
def mock_surrealdb_rag():
    """Mock SurrealDBRAG service."""
    mock = MagicMock()

    # Mock retrieve_context
    mock.retrieve_context = AsyncMock(
        return_value=[
            {
                "video_id": "test123",
                "title": "Cached Video",
                "channel_name": "Test Channel",
                "url": "https://youtube.com/watch?v=test123",
                "score": 0.850,
            },
        ]
    )

    return mock


@pytest.mark.unit
@pytest.mark.asyncio
async def test_cache_search_uses_surrealdb_rag(client, mock_surrealdb_rag):
    """Verify cache search endpoint uses SurrealDBRAG service."""
    with patch(
        "compose.api.routers.cache.SurrealDBRAG",
        return_value=mock_surrealdb_rag,
    ):
        response = client.post(
            "/search",
            json={"query": "test query", "limit": 10},
        )

    assert response.status_code == 200
    data = response.json()

    # Verify response structure
    assert "query" in data
    assert "results" in data
    assert "total_found" in data

    # Verify SurrealDBRAG was called
    mock_surrealdb_rag.retrieve_context.assert_called_once()
    call_kwargs = mock_surrealdb_rag.retrieve_context.call_args.kwargs
    assert call_kwargs["query"] == "test query"
    assert call_kwargs["limit"] == 10


@pytest.mark.unit
@pytest.mark.asyncio
async def test_cache_search_returns_results(client, mock_surrealdb_rag):
    """Verify cache search returns formatted results."""
    with patch(
        "compose.api.routers.cache.SurrealDBRAG",
        return_value=mock_surrealdb_rag,
    ):
        response = client.post(
            "/search",
            json={"query": "test", "limit": 5},
        )

    assert response.status_code == 200
    data = response.json()

    # Check results
    assert data["query"] == "test"
    assert data["total_found"] == 1
    assert len(data["results"]) == 1

    result = data["results"][0]
    assert result["video_id"] == "test123"
    assert result["title"] == "Cached Video"
    assert result["score"] == 0.850


@pytest.mark.unit
@pytest.mark.asyncio
async def test_cache_search_handles_empty_results(client):
    """Verify cache search handles empty results."""
    mock_rag = MagicMock()
    mock_rag.retrieve_context = AsyncMock(return_value=[])

    with patch(
        "compose.api.routers.cache.SurrealDBRAG",
        return_value=mock_rag,
    ):
        response = client.post(
            "/search",
            json={"query": "nonexistent", "limit": 5},
        )

    assert response.status_code == 200
    data = response.json()
    assert data["total_found"] == 0
    assert data["results"] == []


@pytest.mark.unit
@pytest.mark.asyncio
async def test_cache_search_error_handling(client):
    """Verify cache search handles errors gracefully."""
    mock_rag = MagicMock()
    mock_rag.retrieve_context = AsyncMock(
        side_effect=Exception("SurrealDB unavailable")
    )

    with patch(
        "compose.api.routers.cache.SurrealDBRAG",
        return_value=mock_rag,
    ):
        response = client.post(
            "/search",
            json={"query": "test", "limit": 5},
        )

    assert response.status_code == 500
    assert "Cache search failed" in response.json()["detail"]


@pytest.mark.unit
@pytest.mark.asyncio
async def test_get_cached_item_still_works(client):
    """Verify get cached item endpoint still works (unchanged)."""
    mock_video = MagicMock()
    mock_video.video_id = "test123"
    mock_video.url = "https://youtube.com/watch?v=test123"
    mock_video.title = "Test Video"
    mock_video.channel_id = "UC123"
    mock_video.channel_name = "Test Channel"

    with patch("compose.api.routers.cache.get_video", return_value=mock_video):
        response = client.get("/youtube:video:test123")

    assert response.status_code == 200
    data = response.json()
    assert data["key"] == "youtube:video:test123"
    assert data["data"]["video_id"] == "test123"


@pytest.mark.unit
def test_cache_no_qdrant_imports():
    """Verify cache.py does not import Qdrant after migration."""
    import compose.api.routers.cache as cache_module
    import inspect

    source = inspect.getsource(cache_module)

    # Should not have Qdrant imports
    assert "from qdrant" not in source.lower()
    assert "import qdrant" not in source.lower()
    assert "QdrantClient" not in source


@pytest.mark.unit
def test_cache_imports_surrealdb_rag():
    """Verify cache.py imports SurrealDBRAG service."""
    import compose.api.routers.cache as cache_module
    import inspect

    source = inspect.getsource(cache_module)

    # Should import SurrealDBRAG
    assert "SurrealDBRAG" in source


@pytest.mark.unit
def test_cache_no_inline_embedding():
    """Verify cache.py does not use inline embedding (uses service)."""
    import compose.api.routers.cache as cache_module
    import inspect

    source = inspect.getsource(cache_module)

    # Should not generate embeddings inline
    assert "get_embedding(" not in source or "# OLD:" in source
