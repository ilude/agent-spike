"""
Tests for core WebSocket chat functionality.

Tests cover:
- WebSocket /ws/chat (basic chat)
- WebSocket /ws/rag-chat (RAG-powered chat)
"""

import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from compose.api.routers import chat


# ============ WebSocket Chat Tests ============


class TestWebSocketChat:
    """Tests for /ws/chat WebSocket endpoint."""

    def setup_method(self):
        """Reset clients before each test."""
        chat.reset_clients()

    def test_websocket_chat_rejects_without_api_key(self, client):
        """WebSocket should reject if OpenRouter not configured."""
        with patch.object(chat, "get_openrouter_client", return_value=None):
            with client.websocket_connect("/chat/ws/chat") as websocket:
                response = websocket.receive_json()
                assert response["type"] == "error"
                assert "not configured" in response["content"]

    def test_websocket_chat_rejects_empty_message(self, client):
        """WebSocket should reject empty messages."""
        mock_openrouter = MagicMock()
        with patch.object(chat, "get_openrouter_client", return_value=mock_openrouter):
            with client.websocket_connect("/chat/ws/chat") as websocket:
                websocket.send_text(json.dumps({"message": "", "model": "test"}))
                response = websocket.receive_json()
                assert response["type"] == "error"
                assert "empty" in response["content"].lower()

    def test_websocket_chat_rejects_long_message(self, client):
        """WebSocket should reject messages over 10,000 chars."""
        mock_openrouter = MagicMock()
        with patch.object(chat, "get_openrouter_client", return_value=mock_openrouter):
            with client.websocket_connect("/chat/ws/chat") as websocket:
                long_message = "a" * 10001
                websocket.send_text(json.dumps({"message": long_message, "model": "test"}))
                response = websocket.receive_json()
                assert response["type"] == "error"
                assert "too long" in response["content"].lower()

    def test_websocket_chat_streams_response(self, client):
        """WebSocket should stream response tokens."""
        mock_openrouter = AsyncMock()

        # Create streaming response
        async def create_stream(*args, **kwargs):
            class MockStream:
                def __init__(self):
                    self.chunks = [
                        MagicMock(choices=[MagicMock(delta=MagicMock(content="Hello"))]),
                        MagicMock(choices=[MagicMock(delta=MagicMock(content=" world"))]),
                        MagicMock(choices=[MagicMock(delta=MagicMock(content=None))]),
                    ]
                    self.index = 0

                def __aiter__(self):
                    return self

                async def __anext__(self):
                    if self.index >= len(self.chunks):
                        raise StopAsyncIteration
                    chunk = self.chunks[self.index]
                    self.index += 1
                    return chunk

            return MockStream()

        mock_openrouter.chat.completions.create = create_stream

        with patch.object(chat, "get_openrouter_client", return_value=mock_openrouter):
            with patch.object(chat, "get_conversation_service") as mock_conv_svc:
                mock_conv_svc.return_value = MagicMock()

                with client.websocket_connect("/chat/ws/chat") as websocket:
                    websocket.send_text(json.dumps({
                        "message": "Hi",
                        "model": "test-model"
                    }))

                    # Collect responses
                    responses = []
                    while True:
                        response = websocket.receive_json()
                        responses.append(response)
                        if response["type"] == "done":
                            break

                    # Should have token responses + done
                    token_responses = [r for r in responses if r["type"] == "token"]
                    assert len(token_responses) >= 1
                    assert any("Hello" in r.get("content", "") for r in token_responses)

    def test_websocket_chat_routes_to_ollama(self, client):
        """WebSocket should route ollama: models to Ollama client."""
        mock_openrouter = MagicMock()
        mock_ollama = AsyncMock()

        async def create_stream(*args, **kwargs):
            class MockStream:
                def __aiter__(self):
                    return self

                async def __anext__(self):
                    raise StopAsyncIteration

            return MockStream()

        mock_ollama.chat.completions.create = create_stream

        with patch.object(chat, "get_openrouter_client", return_value=mock_openrouter):
            with patch.object(chat, "get_ollama_client", return_value=mock_ollama):
                with patch.object(chat, "get_conversation_service") as mock_conv_svc:
                    mock_conv_svc.return_value = MagicMock()

                    with client.websocket_connect("/chat/ws/chat") as websocket:
                        websocket.send_text(json.dumps({
                            "message": "Hi",
                            "model": "ollama:qwen3:8b"
                        }))

                        # Should get done (even if empty stream)
                        response = websocket.receive_json()
                        assert response["type"] == "done"


# ============ WebSocket RAG Chat Tests ============


class TestWebSocketRAGChat:
    """Tests for /ws/rag-chat WebSocket endpoint."""

    def setup_method(self):
        """Reset clients before each test."""
        chat.reset_clients()

    def test_websocket_rag_chat_rejects_without_api_key(self, client):
        """RAG WebSocket should reject if not configured."""
        with patch.object(chat, "get_openrouter_client", return_value=None):
            with client.websocket_connect("/chat/ws/rag-chat") as websocket:
                response = websocket.receive_json()
                assert response["type"] == "error"
                assert "not configured" in response["content"]

    def test_websocket_rag_chat_rejects_empty_message(self, client):
        """RAG WebSocket should reject empty messages."""
        mock_openrouter = MagicMock()
        with patch.object(chat, "get_openrouter_client", return_value=mock_openrouter):
            with client.websocket_connect("/chat/ws/rag-chat") as websocket:
                websocket.send_text(json.dumps({"message": "", "model": "test"}))
                response = websocket.receive_json()
                assert response["type"] == "error"
                assert "empty" in response["content"].lower()

    def test_websocket_rag_chat_falls_back_on_rag_error(self, client):
        """RAG WebSocket should fall back to direct chat on RAG error."""
        mock_openrouter = AsyncMock()

        async def create_stream(*args, **kwargs):
            class MockStream:
                def __aiter__(self):
                    return self

                async def __anext__(self):
                    raise StopAsyncIteration

            return MockStream()

        mock_openrouter.chat.completions.create = create_stream

        with patch.object(chat, "get_openrouter_client", return_value=mock_openrouter):
            with patch.object(chat, "get_embedding", side_effect=Exception("Embedding failed")):
                with patch.object(chat, "get_conversation_service") as mock_conv_svc:
                    with patch.object(chat, "get_project_service") as mock_proj_svc:
                        mock_conv_svc.return_value = MagicMock()
                        mock_proj_svc.return_value = MagicMock()
                        mock_proj_svc.return_value.get_project.return_value = None

                        with client.websocket_connect("/chat/ws/rag-chat") as websocket:
                            websocket.send_text(json.dumps({
                                "message": "Hello",
                                "model": "test-model"
                            }))

                            # Should still get done (fallback worked)
                            response = websocket.receive_json()
                            assert response["type"] == "done"

    def test_websocket_rag_chat_includes_sources(self, client):
        """RAG WebSocket should include sources in response."""
        mock_openrouter = AsyncMock()

        async def create_stream(*args, **kwargs):
            class MockStream:
                def __init__(self):
                    self.chunks = [
                        MagicMock(choices=[MagicMock(delta=MagicMock(content="Answer"))]),
                        MagicMock(choices=[MagicMock(delta=MagicMock(content=None))]),
                    ]
                    self.index = 0

                def __aiter__(self):
                    return self

                async def __anext__(self):
                    if self.index >= len(self.chunks):
                        raise StopAsyncIteration
                    chunk = self.chunks[self.index]
                    self.index += 1
                    return chunk

            return MockStream()

        mock_openrouter.chat.completions.create = create_stream

        # Mock SurrealDB search results
        from compose.services.surrealdb.models import VectorSearchResult

        mock_search_result = VectorSearchResult(
            video_id="abc123",
            title="Test Video",
            url="https://youtube.com/watch?v=abc123",
            similarity_score=0.95,
            channel_name="Test Channel",
            archive_path=None
        )

        async def mock_embedding(text):
            return [0.1] * 384

        async def mock_semantic_search(embedding, limit=5):
            return [mock_search_result]

        with patch.object(chat, "get_openrouter_client", return_value=mock_openrouter):
            with patch("compose.api.routers.chat.semantic_search", side_effect=mock_semantic_search):
                with patch.object(chat, "get_embedding", side_effect=mock_embedding):
                    with patch.object(chat, "get_conversation_service") as mock_conv_svc:
                        with patch.object(chat, "get_project_service") as mock_proj_svc:
                            mock_conv_svc.return_value = MagicMock()
                            mock_proj_svc.return_value = MagicMock()
                            mock_proj_svc.return_value.get_project.return_value = None

                            with client.websocket_connect("/chat/ws/rag-chat") as websocket:
                                websocket.send_text(json.dumps({
                                    "message": "Tell me about Python",
                                    "model": "test-model"
                                }))

                                # Collect all responses
                                responses = []
                                while True:
                                    response = websocket.receive_json()
                                    responses.append(response)
                                    if response["type"] == "done":
                                        break

                                # Check done response has sources
                                done_response = responses[-1]
                                assert done_response["type"] == "done"
                                assert "sources" in done_response
                                if done_response["sources"]:
                                    assert done_response["sources"][0]["video_title"] == "Test Video"
