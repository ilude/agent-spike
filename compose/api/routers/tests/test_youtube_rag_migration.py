"""Tests for youtube_rag.py using SurrealDBRAG service.

These tests verify the migration from inline semantic_search to SurrealDBRAG service.
Following test-first development approach for Phase 3 of Qdrant → SurrealDB migration.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from fastapi import FastAPI
from fastapi.testclient import TestClient

from compose.api.routers.youtube_rag import router, SearchRequest, QueryRequest


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

    # Mock retrieve_context for search
    mock.retrieve_context = AsyncMock(
        return_value=[
            {
                "video_id": "test123",
                "title": "AI Agents Tutorial",
                "channel_name": "Tech Channel",
                "url": "https://youtube.com/watch?v=test123",
                "score": 0.850,
            },
            {
                "video_id": "test456",
                "title": "Advanced AI Techniques",
                "channel_name": "AI Research",
                "url": "https://youtube.com/watch?v=test456",
                "score": 0.720,
            },
        ]
    )

    # Mock extract_sources
    mock.extract_sources = MagicMock(
        return_value=[
            {
                "video_id": "test123",
                "title": "AI Agents Tutorial",
                "url": "https://youtube.com/watch?v=test123",
                "relevance_score": 0.850,
            },
            {
                "video_id": "test456",
                "title": "Advanced AI Techniques",
                "url": "https://youtube.com/watch?v=test456",
                "relevance_score": 0.720,
            },
        ]
    )

    return mock


@pytest.mark.unit
@pytest.mark.asyncio
async def test_search_endpoint_uses_surrealdb_rag(client, mock_surrealdb_rag):
    """Verify /search endpoint uses SurrealDBRAG service."""
    with patch(
        "compose.api.routers.youtube_rag.SurrealDBRAG",
        return_value=mock_surrealdb_rag,
    ):
        response = client.post(
            "/search",
            json={"query": "How to build AI agents?", "limit": 10},
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
    assert call_kwargs["query"] == "How to build AI agents?"
    assert call_kwargs["limit"] == 10


@pytest.mark.unit
@pytest.mark.asyncio
async def test_search_returns_formatted_results(client, mock_surrealdb_rag):
    """Verify search results are properly formatted."""
    with patch(
        "compose.api.routers.youtube_rag.SurrealDBRAG",
        return_value=mock_surrealdb_rag,
    ):
        response = client.post(
            "/search",
            json={"query": "test query", "limit": 5},
        )

    assert response.status_code == 200
    data = response.json()

    # Check results formatting
    assert data["query"] == "test query"
    assert data["total_found"] == 2
    assert len(data["results"]) == 2

    # Check individual result structure
    result = data["results"][0]
    assert result["video_id"] == "test123"
    assert result["title"] == "AI Agents Tutorial"
    assert result["channel"] == "Tech Channel"
    assert result["score"] == 0.850
    assert result["url"] == "https://youtube.com/watch?v=test123"


@pytest.mark.unit
@pytest.mark.asyncio
async def test_search_handles_empty_results(client):
    """Verify search handles empty results gracefully."""
    mock_rag = MagicMock()
    mock_rag.retrieve_context = AsyncMock(return_value=[])

    with patch(
        "compose.api.routers.youtube_rag.SurrealDBRAG",
        return_value=mock_rag,
    ):
        response = client.post(
            "/search",
            json={"query": "nonexistent query", "limit": 10},
        )

    assert response.status_code == 200
    data = response.json()
    assert data["total_found"] == 0
    assert data["results"] == []


@pytest.mark.unit
@pytest.mark.asyncio
async def test_search_supports_channel_filter(client, mock_surrealdb_rag):
    """Verify search supports channel filtering."""
    with patch(
        "compose.api.routers.youtube_rag.SurrealDBRAG",
        return_value=mock_surrealdb_rag,
    ):
        response = client.post(
            "/search",
            json={"query": "test", "limit": 5, "channel": "Tech Channel"},
        )

    assert response.status_code == 200

    # Verify channel filter was passed
    call_kwargs = mock_surrealdb_rag.retrieve_context.call_args.kwargs
    assert call_kwargs.get("channel_filter") == "Tech Channel"


@pytest.mark.unit
@pytest.mark.asyncio
async def test_query_endpoint_uses_surrealdb_rag(client, mock_surrealdb_rag):
    """Verify /query endpoint uses SurrealDBRAG service."""
    with patch(
        "compose.api.routers.youtube_rag.SurrealDBRAG",
        return_value=mock_surrealdb_rag,
    ):
        response = client.post(
            "/query",
            json={"question": "What are best practices for AI agents?", "limit": 5},
        )

    assert response.status_code == 200
    data = response.json()

    # Verify response structure
    assert "question" in data
    assert "answer" in data
    assert "sources" in data
    assert "context_used" in data

    # Verify SurrealDBRAG was called
    mock_surrealdb_rag.retrieve_context.assert_called_once()
    mock_surrealdb_rag.extract_sources.assert_called_once()


@pytest.mark.unit
@pytest.mark.asyncio
async def test_query_returns_sources(client, mock_surrealdb_rag):
    """Verify query endpoint returns source citations."""
    with patch(
        "compose.api.routers.youtube_rag.SurrealDBRAG",
        return_value=mock_surrealdb_rag,
    ):
        response = client.post(
            "/query",
            json={"question": "test question", "limit": 5},
        )

    assert response.status_code == 200
    data = response.json()

    # Check sources
    assert data["context_used"] is True
    assert len(data["sources"]) == 2
    assert data["sources"][0]["video_id"] == "test123"
    assert data["sources"][0]["relevance_score"] == 0.850


@pytest.mark.unit
@pytest.mark.asyncio
async def test_query_handles_no_context(client):
    """Verify query handles case with no relevant context."""
    mock_rag = MagicMock()
    mock_rag.retrieve_context = AsyncMock(return_value=[])
    mock_rag.extract_sources = MagicMock(return_value=[])

    with patch(
        "compose.api.routers.youtube_rag.SurrealDBRAG",
        return_value=mock_rag,
    ):
        response = client.post(
            "/query",
            json={"question": "test", "limit": 5},
        )

    assert response.status_code == 200
    data = response.json()

    assert data["context_used"] is False
    assert data["sources"] == []
    assert "No relevant video content found" in data["answer"]


@pytest.mark.unit
@pytest.mark.asyncio
async def test_search_error_handling(client):
    """Verify search endpoint handles errors gracefully."""
    mock_rag = MagicMock()
    mock_rag.retrieve_context = AsyncMock(
        side_effect=Exception("SurrealDB connection failed")
    )

    with patch(
        "compose.api.routers.youtube_rag.SurrealDBRAG",
        return_value=mock_rag,
    ):
        response = client.post(
            "/search",
            json={"query": "test", "limit": 5},
        )

    assert response.status_code == 500
    assert "Search failed" in response.json()["detail"]


@pytest.mark.unit
@pytest.mark.asyncio
async def test_query_error_handling(client):
    """Verify query endpoint handles errors gracefully."""
    mock_rag = MagicMock()
    mock_rag.retrieve_context = AsyncMock(
        side_effect=Exception("Service unavailable")
    )

    with patch(
        "compose.api.routers.youtube_rag.SurrealDBRAG",
        return_value=mock_rag,
    ):
        response = client.post(
            "/query",
            json={"question": "test", "limit": 5},
        )

    assert response.status_code == 500
    assert "Query failed" in response.json()["detail"]


@pytest.mark.unit
def test_youtube_rag_no_qdrant_imports():
    """Verify youtube_rag.py does not import Qdrant after migration."""
    import compose.api.routers.youtube_rag as rag_module
    import inspect

    source = inspect.getsource(rag_module)

    # Should not have Qdrant imports
    assert "from qdrant" not in source.lower()
    assert "import qdrant" not in source.lower()
    assert "QdrantClient" not in source


@pytest.mark.unit
def test_youtube_rag_imports_surrealdb_rag():
    """Verify youtube_rag.py imports SurrealDBRAG service."""
    import compose.api.routers.youtube_rag as rag_module
    import inspect

    source = inspect.getsource(rag_module)

    # Should import SurrealDBRAG
    assert "SurrealDBRAG" in source


@pytest.mark.unit
def test_youtube_rag_no_inline_embedding():
    """Verify youtube_rag.py does not use inline get_embedding (uses service)."""
    import compose.api.routers.youtube_rag as rag_module
    import inspect

    source = inspect.getsource(rag_module)

    # Should not call get_embedding inline (SurrealDBRAG handles this)
    # Old pattern: query_vector = await get_embedding(request.query)
    # New pattern: results = await rag.retrieve_context(request.query)
    assert "query_vector = await get_embedding" not in source
