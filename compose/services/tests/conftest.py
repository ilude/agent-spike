"""Shared pytest fixtures for tools/services tests."""

import pytest
import tempfile
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch
from typing import Any


# =============================================================================
# Mock Factories - Create configurable mocks for external dependencies
# =============================================================================

def create_mock_openai_client(
    response_content: str = "This is a mock response",
    stream_chunks: list[str] | None = None,
) -> MagicMock:
    """Create a mock AsyncOpenAI client.

    Args:
        response_content: Content for non-streaming responses
        stream_chunks: List of strings for streaming responses (simulates delta.content)

    Returns:
        Mock client that can be used in place of AsyncOpenAI
    """
    mock_client = MagicMock()

    if stream_chunks:
        # Streaming response
        async def stream_generator():
            for chunk_text in stream_chunks:
                chunk = MagicMock()
                chunk.choices = [MagicMock()]
                chunk.choices[0].delta.content = chunk_text
                yield chunk

        mock_stream = AsyncMock(return_value=stream_generator())
        mock_client.chat.completions.create = mock_stream
    else:
        # Non-streaming response
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = response_content
        mock_client.chat.completions.create = AsyncMock(return_value=mock_response)

    return mock_client


def create_mock_qdrant_client(
    collection_exists: bool = True,
    points_count: int = 100,
    search_results: list[dict] | None = None,
    scroll_results: list[dict] | None = None,
) -> MagicMock:
    """Create a mock QdrantClient.

    Args:
        collection_exists: Whether the collection should appear to exist
        points_count: Number of points in the collection
        search_results: Results for query_points calls
        scroll_results: Results for scroll calls

    Returns:
        Mock client that can be used in place of QdrantClient
    """
    mock_client = MagicMock()

    # get_collection
    if collection_exists:
        collection_info = MagicMock()
        collection_info.points_count = points_count
        mock_client.get_collection.return_value = collection_info
    else:
        mock_client.get_collection.side_effect = Exception("Collection not found")

    # query_points (for RAG search)
    if search_results is None:
        search_results = [
            {
                "payload": {
                    "text": "Sample video content about AI agents",
                    "video_id": "youtube:test123",
                    "video_title": "Test Video Title",
                    "url": "https://youtube.com/watch?v=test123",
                    "tags": ["ai", "agents"],
                }
            }
        ]

    mock_search = MagicMock()
    mock_search.points = [
        MagicMock(payload=r["payload"]) for r in search_results
    ]
    mock_client.query_points.return_value = mock_search

    # scroll (for random questions)
    if scroll_results is None:
        scroll_results = search_results

    scroll_points = [MagicMock(payload=r["payload"]) for r in scroll_results]
    mock_client.scroll.return_value = (scroll_points, None)

    # upsert
    mock_client.upsert.return_value = MagicMock()

    return mock_client


def create_mock_websocket(
    messages: list[str] | None = None,
) -> MagicMock:
    """Create a mock WebSocket for testing WebSocket handlers.

    Args:
        messages: List of JSON strings the client will "send"

    Returns:
        Mock WebSocket that can be used in place of FastAPI WebSocket
    """
    mock_ws = AsyncMock()
    mock_ws.accept = AsyncMock()
    mock_ws.send_json = AsyncMock()
    mock_ws.close = AsyncMock()

    if messages:
        # Simulate receiving messages then disconnect
        from starlette.websockets import WebSocketDisconnect
        side_effects = list(messages) + [WebSocketDisconnect()]
        mock_ws.receive_text = AsyncMock(side_effect=side_effects)
    else:
        from starlette.websockets import WebSocketDisconnect
        mock_ws.receive_text = AsyncMock(side_effect=WebSocketDisconnect())

    mock_ws.client = MagicMock()
    mock_ws.client.host = "127.0.0.1"

    return mock_ws


def create_mock_httpx_client(
    responses: dict[str, dict] | None = None,
) -> MagicMock:
    """Create a mock httpx.AsyncClient.

    Args:
        responses: Dict mapping URL patterns to response data

    Returns:
        Mock client for httpx operations
    """
    mock_client = MagicMock()

    if responses is None:
        responses = {
            "/embeddings": {
                "data": [{"embedding": [0.1] * 1024}]  # 1024-dim embedding
            }
        }

    async def mock_post(url, **kwargs):
        response = MagicMock()
        response.raise_for_status = MagicMock()

        for pattern, data in responses.items():
            if pattern in url:
                response.json.return_value = data
                return response

        response.json.return_value = {}
        return response

    async def mock_get(url, **kwargs):
        response = MagicMock()
        response.raise_for_status = MagicMock()

        for pattern, data in responses.items():
            if pattern in url:
                response.json.return_value = data
                return response

        response.json.return_value = {}
        return response

    mock_client.post = mock_post
    mock_client.get = mock_get
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=None)

    return mock_client


# =============================================================================
# Pytest Fixtures
# =============================================================================

@pytest.fixture
def mock_openai():
    """Fixture providing a mock OpenAI client."""
    return create_mock_openai_client()


@pytest.fixture
def mock_openai_streaming():
    """Fixture providing a mock OpenAI client with streaming."""
    return create_mock_openai_client(
        stream_chunks=["Hello", " ", "world", "!"]
    )


@pytest.fixture
def mock_qdrant():
    """Fixture providing a mock Qdrant client."""
    return create_mock_qdrant_client()


@pytest.fixture
def mock_websocket():
    """Fixture providing a mock WebSocket."""
    return create_mock_websocket()


@pytest.fixture
def mock_httpx():
    """Fixture providing a mock httpx client."""
    return create_mock_httpx_client()


@pytest.fixture
def temp_dir():
    """Temporary directory for tests.

    Automatically cleaned up after test completes.
    Note: ignore_cleanup_errors=True handles Windows file locking issues
    with embedded Qdrant SQLite storage.
    """
    with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as tmpdir:
        yield Path(tmpdir)


@pytest.fixture
def sample_transcript():
    """Sample YouTube transcript for testing."""
    return (
        "This is a sample transcript about AI agents. "
        "We discuss composability, dependency injection, and clean architecture. "
        "The goal is to build reusable services that can be composed together."
    )


@pytest.fixture
def sample_video_id():
    """Sample YouTube video ID."""
    return "dQw4w9WgXcQ"


@pytest.fixture
def sample_video_url(sample_video_id):
    """Sample YouTube video URL."""
    return f"https://www.youtube.com/watch?v={sample_video_id}"


@pytest.fixture
def sample_youtube_metadata():
    """Sample YouTube video metadata."""
    return {
        "title": "Test Video",
        "channel": "Test Channel",
        "upload_date": "2024-11-09",
        "duration": 180,
    }
