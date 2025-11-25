"""Tests for chat.py RAG endpoint using SurrealDBRAG service.

These tests verify the migration from inline RAG code to the SurrealDBRAG service.
Following test-first development approach for Phase 3 of Qdrant → SurrealDB migration.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from fastapi import WebSocket
from fastapi.websockets import WebSocketDisconnect


@pytest.fixture
def mock_surrealdb_rag():
    """Mock SurrealDBRAG service."""
    mock = MagicMock()

    # Mock get_context_and_sources method
    mock.get_context_and_sources = AsyncMock(
        return_value=(
            # Context string
            '[Video: "Building AI Agents"]\nChannel: Tech Channel\nRelevance: 0.850\n\nTranscript:\nThis is a test transcript about AI agents...',
            # Sources list
            [
                {
                    "video_id": "test123",
                    "title": "Building AI Agents",
                    "url": "https://youtube.com/watch?v=test123",
                    "relevance_score": 0.850,
                }
            ],
        )
    )

    return mock


@pytest.fixture
def mock_openai_client():
    """Mock OpenAI client for streaming responses."""
    mock_client = MagicMock()

    # Mock streaming response
    async def mock_stream():
        chunks = [
            MagicMock(choices=[MagicMock(delta=MagicMock(content="This "))]),
            MagicMock(choices=[MagicMock(delta=MagicMock(content="is "))]),
            MagicMock(choices=[MagicMock(delta=MagicMock(content="a "))]),
            MagicMock(choices=[MagicMock(delta=MagicMock(content="test."))]),
        ]
        for chunk in chunks:
            yield chunk

    mock_completion = MagicMock()
    mock_completion.__aiter__ = lambda self: mock_stream()

    mock_client.chat.completions.create = AsyncMock(return_value=mock_completion)

    return mock_client


@pytest.mark.unit
@pytest.mark.asyncio
async def test_rag_chat_uses_surrealdb_rag_service(mock_surrealdb_rag, mock_openai_client):
    """Verify RAG chat endpoint uses SurrealDBRAG service instead of inline code."""
    from compose.api.routers.chat import websocket_rag_chat

    # Mock WebSocket
    mock_ws = MagicMock(spec=WebSocket)
    mock_ws.accept = AsyncMock()
    mock_ws.receive_text = AsyncMock(
        side_effect=[
            '{"message": "How to build AI agents?", "model": "test-model"}',
            WebSocketDisconnect(),
        ]
    )
    mock_ws.send_json = AsyncMock()
    mock_ws.close = AsyncMock()

    with (
        patch("compose.api.routers.chat.SurrealDBRAG", return_value=mock_surrealdb_rag),
        patch("compose.api.routers.chat.get_openrouter_client", return_value=mock_openai_client),
        patch("compose.api.routers.chat.get_conversation_service"),
        patch("compose.api.routers.chat.get_project_service"),
        patch("compose.api.routers.chat.get_styles_service"),
        patch("compose.api.routers.chat.get_memory_service"),
    ):
        try:
            await websocket_rag_chat(mock_ws)
        except WebSocketDisconnect:
            pass

    # Verify SurrealDBRAG was called
    mock_surrealdb_rag.get_context_and_sources.assert_called_once()
    call_kwargs = mock_surrealdb_rag.get_context_and_sources.call_args.kwargs
    assert call_kwargs["query"] == "How to build AI agents?"
    assert call_kwargs["limit"] == 5  # Default limit


@pytest.mark.unit
@pytest.mark.asyncio
async def test_rag_chat_handles_empty_context(mock_surrealdb_rag, mock_openai_client):
    """Verify RAG chat handles empty context gracefully."""
    # Mock empty context
    mock_surrealdb_rag.get_context_and_sources = AsyncMock(
        return_value=("", [])  # Empty context and sources
    )

    mock_ws = MagicMock(spec=WebSocket)
    mock_ws.accept = AsyncMock()
    mock_ws.receive_text = AsyncMock(
        side_effect=[
            '{"message": "Test question", "model": "test-model"}',
            WebSocketDisconnect(),
        ]
    )
    mock_ws.send_json = AsyncMock()
    mock_ws.close = AsyncMock()

    with (
        patch("compose.api.routers.chat.SurrealDBRAG", return_value=mock_surrealdb_rag),
        patch("compose.api.routers.chat.get_openrouter_client", return_value=mock_openai_client),
        patch("compose.api.routers.chat.get_conversation_service"),
        patch("compose.api.routers.chat.get_project_service"),
        patch("compose.api.routers.chat.get_styles_service"),
        patch("compose.api.routers.chat.get_memory_service"),
    ):
        try:
            await websocket_rag_chat(mock_ws)
        except WebSocketDisconnect:
            pass

    # Should still call LLM even without context
    mock_openai_client.chat.completions.create.assert_called_once()


@pytest.mark.unit
@pytest.mark.asyncio
async def test_rag_chat_sends_sources_in_done_message(mock_surrealdb_rag, mock_openai_client):
    """Verify sources are sent in the 'done' WebSocket message."""
    mock_ws = MagicMock(spec=WebSocket)
    mock_ws.accept = AsyncMock()
    mock_ws.receive_text = AsyncMock(
        side_effect=[
            '{"message": "Test", "model": "test-model"}',
            WebSocketDisconnect(),
        ]
    )
    mock_ws.send_json = AsyncMock()
    mock_ws.close = AsyncMock()

    with (
        patch("compose.api.routers.chat.SurrealDBRAG", return_value=mock_surrealdb_rag),
        patch("compose.api.routers.chat.get_openrouter_client", return_value=mock_openai_client),
        patch("compose.api.routers.chat.get_conversation_service"),
        patch("compose.api.routers.chat.get_project_service"),
        patch("compose.api.routers.chat.get_styles_service"),
        patch("compose.api.routers.chat.get_memory_service"),
    ):
        try:
            await websocket_rag_chat(mock_ws)
        except WebSocketDisconnect:
            pass

    # Find the 'done' message
    done_calls = [
        call for call in mock_ws.send_json.call_args_list
        if call[0][0].get("type") == "done"
    ]

    assert len(done_calls) == 1
    done_message = done_calls[0][0][0]
    assert "sources" in done_message
    assert len(done_message["sources"]) == 1
    assert done_message["sources"][0]["video_id"] == "test123"


@pytest.mark.unit
@pytest.mark.asyncio
async def test_rag_chat_fallback_on_service_error(mock_surrealdb_rag, mock_openai_client):
    """Verify graceful fallback when SurrealDBRAG service fails."""
    # Mock service failure
    mock_surrealdb_rag.get_context_and_sources = AsyncMock(
        side_effect=Exception("SurrealDB connection failed")
    )

    mock_ws = MagicMock(spec=WebSocket)
    mock_ws.accept = AsyncMock()
    mock_ws.receive_text = AsyncMock(
        side_effect=[
            '{"message": "Test", "model": "test-model"}',
            WebSocketDisconnect(),
        ]
    )
    mock_ws.send_json = AsyncMock()
    mock_ws.close = AsyncMock()

    with (
        patch("compose.api.routers.chat.SurrealDBRAG", return_value=mock_surrealdb_rag),
        patch("compose.api.routers.chat.get_openrouter_client", return_value=mock_openai_client),
        patch("compose.api.routers.chat.get_conversation_service"),
        patch("compose.api.routers.chat.get_project_service"),
        patch("compose.api.routers.chat.get_styles_service"),
        patch("compose.api.routers.chat.get_memory_service"),
    ):
        try:
            await websocket_rag_chat(mock_ws)
        except WebSocketDisconnect:
            pass

    # Should still complete (fallback to non-RAG)
    mock_openai_client.chat.completions.create.assert_called_once()

    # Done message should have empty sources
    done_calls = [
        call for call in mock_ws.send_json.call_args_list
        if call[0][0].get("type") == "done"
    ]
    assert len(done_calls) == 1
    assert done_calls[0][0][0]["sources"] == []


@pytest.mark.unit
@pytest.mark.asyncio
async def test_rag_chat_formats_context_in_prompt(mock_surrealdb_rag, mock_openai_client):
    """Verify context from SurrealDBRAG is formatted into LLM prompt."""
    mock_ws = MagicMock(spec=WebSocket)
    mock_ws.accept = AsyncMock()
    mock_ws.receive_text = AsyncMock(
        side_effect=[
            '{"message": "Test question", "model": "test-model"}',
            WebSocketDisconnect(),
        ]
    )
    mock_ws.send_json = AsyncMock()
    mock_ws.close = AsyncMock()

    with (
        patch("compose.api.routers.chat.SurrealDBRAG", return_value=mock_surrealdb_rag),
        patch("compose.api.routers.chat.get_openrouter_client", return_value=mock_openai_client),
        patch("compose.api.routers.chat.get_conversation_service"),
        patch("compose.api.routers.chat.get_project_service"),
        patch("compose.api.routers.chat.get_styles_service"),
        patch("compose.api.routers.chat.get_memory_service"),
    ):
        try:
            await websocket_rag_chat(mock_ws)
        except WebSocketDisconnect:
            pass

    # Check the prompt sent to LLM includes context
    create_call = mock_openai_client.chat.completions.create.call_args
    messages = create_call.kwargs["messages"]

    # Should have user message with context
    assert len(messages) > 0
    user_message = messages[-1]
    assert user_message["role"] == "user"
    assert "Building AI Agents" in user_message["content"]  # Context from mock


@pytest.mark.unit
@pytest.mark.asyncio
async def test_rag_chat_supports_custom_limit(mock_surrealdb_rag, mock_openai_client):
    """Verify RAG chat supports custom result limit in request."""
    mock_ws = MagicMock(spec=WebSocket)
    mock_ws.accept = AsyncMock()
    mock_ws.receive_text = AsyncMock(
        side_effect=[
            '{"message": "Test", "model": "test-model", "rag_limit": 10}',
            WebSocketDisconnect(),
        ]
    )
    mock_ws.send_json = AsyncMock()
    mock_ws.close = AsyncMock()

    with (
        patch("compose.api.routers.chat.SurrealDBRAG", return_value=mock_surrealdb_rag),
        patch("compose.api.routers.chat.get_openrouter_client", return_value=mock_openai_client),
        patch("compose.api.routers.chat.get_conversation_service"),
        patch("compose.api.routers.chat.get_project_service"),
        patch("compose.api.routers.chat.get_styles_service"),
        patch("compose.api.routers.chat.get_memory_service"),
    ):
        try:
            await websocket_rag_chat(mock_ws)
        except WebSocketDisconnect:
            pass

    # Verify custom limit was used
    call_kwargs = mock_surrealdb_rag.get_context_and_sources.call_args.kwargs
    assert call_kwargs["limit"] == 10


@pytest.mark.unit
@pytest.mark.asyncio
async def test_rag_chat_no_qdrant_imports():
    """Verify chat.py does not import Qdrant after migration."""
    import compose.api.routers.chat as chat_module
    import inspect

    source = inspect.getsource(chat_module)

    # Should not have Qdrant imports (case-insensitive)
    assert "from qdrant" not in source.lower()
    assert "import qdrant" not in source.lower()
    assert "QdrantClient" not in source


@pytest.mark.unit
@pytest.mark.asyncio
async def test_rag_chat_imports_surrealdb_rag():
    """Verify chat.py imports SurrealDBRAG service."""
    import compose.api.routers.chat as chat_module
    import inspect

    source = inspect.getsource(chat_module)

    # Should import SurrealDBRAG
    assert "SurrealDBRAG" in source
