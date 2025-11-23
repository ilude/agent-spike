"""
Tests for chat router WebSocket endpoints and HTTP endpoints.

Tests cover:
- Client initialization and reset
- /models endpoint (caching, fallback, error handling)
- /random-question endpoint
- WebSocket /ws/chat (basic chat)
- WebSocket /ws/rag-chat (RAG-powered chat)
"""

import json
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from compose.api.routers import chat


# ============ Client Management Tests ============


class TestClientManagement:
    """Tests for lazy client initialization."""

    def setup_method(self):
        """Reset clients before each test."""
        chat.reset_clients()

    def test_reset_clients(self):
        """reset_clients() should set all clients to None."""
        chat.reset_clients()

        # Access internal state
        assert chat._openrouter_client is None
        assert chat._ollama_client is None
        assert chat._qdrant_client is None

    def test_get_openrouter_client_creates_on_first_use(self):
        """get_openrouter_client() should create client on first use."""
        chat.reset_clients()
        # Module-level var is read at import time, so patch it directly
        original_key = chat.OPENROUTER_API_KEY
        chat.OPENROUTER_API_KEY = "test-key"

        try:
            with patch("compose.api.routers.chat.AsyncOpenAI") as mock_openai:
                mock_client = MagicMock()
                mock_openai.return_value = mock_client

                client = chat.get_openrouter_client()

                assert client is not None
                mock_openai.assert_called_once_with(
                    base_url="https://openrouter.ai/api/v1",
                    api_key="test-key",
                )
        finally:
            chat.OPENROUTER_API_KEY = original_key

    @patch.dict("os.environ", {"OPENROUTER_API_KEY": ""}, clear=True)
    def test_get_openrouter_client_returns_none_without_key(self):
        """get_openrouter_client() should return None if no API key."""
        chat.reset_clients()
        # Clear the module-level variable
        chat.OPENROUTER_API_KEY = None

        client = chat.get_openrouter_client()

        assert client is None

    def test_get_ollama_client_creates_on_first_use(self):
        """get_ollama_client() should create client on first use."""
        chat.reset_clients()

        with patch("compose.api.routers.chat.AsyncOpenAI") as mock_openai:
            mock_client = MagicMock()
            mock_openai.return_value = mock_client

            client = chat.get_ollama_client()

            assert client is not None
            mock_openai.assert_called_once()

    def test_get_qdrant_client_creates_on_first_use(self):
        """get_qdrant_client() should create client on first use."""
        chat.reset_clients()

        with patch("compose.api.routers.chat.QdrantClient") as mock_qdrant:
            mock_client = MagicMock()
            mock_qdrant.return_value = mock_client

            client = chat.get_qdrant_client()

            assert client is not None
            mock_qdrant.assert_called_once()


# ============ Models Endpoint Tests ============


class TestModelsEndpoint:
    """Tests for /models endpoint."""

    def setup_method(self):
        """Clear cache before each test."""
        chat.models_cache["data"] = None
        chat.models_cache["timestamp"] = None

    def test_fallback_models_structure(self):
        """_fallback_models() should return valid structure."""
        result = chat._fallback_models()

        assert "models" in result
        assert len(result["models"]) > 0
        for model in result["models"]:
            assert "id" in model
            assert "name" in model
            assert "is_free" in model

    def test_fallback_models_includes_ollama(self):
        """_fallback_models() should include local Ollama models."""
        result = chat._fallback_models()

        ollama_models = [m for m in result["models"] if m["id"].startswith("ollama:")]
        assert len(ollama_models) >= 2

    @pytest.mark.asyncio
    async def test_list_models_returns_cached_if_fresh(self):
        """list_models() should return cached data if fresh."""
        now = datetime.now(timezone.utc).timestamp()
        chat.models_cache["data"] = {"models": [{"id": "cached", "name": "Cached"}]}
        chat.models_cache["timestamp"] = now

        result = await chat.list_models()

        assert result["models"][0]["id"] == "cached"

    @pytest.mark.asyncio
    async def test_list_models_returns_fallback_without_api_key(self):
        """list_models() should return fallback if no API key."""
        chat.models_cache["data"] = None
        original_key = chat.OPENROUTER_API_KEY
        chat.OPENROUTER_API_KEY = None

        try:
            result = await chat.list_models()
            assert "models" in result
            assert len(result["models"]) > 0
        finally:
            chat.OPENROUTER_API_KEY = original_key

    @pytest.mark.asyncio
    @patch("httpx.AsyncClient")
    async def test_list_models_fetches_from_openrouter(self, mock_client_class):
        """list_models() should fetch from OpenRouter API."""
        chat.models_cache["data"] = None
        original_key = chat.OPENROUTER_API_KEY
        chat.OPENROUTER_API_KEY = "test-key"

        # Mock response
        mock_response = MagicMock()
        mock_response.raise_for_status = MagicMock()
        mock_response.json.return_value = {
            "data": [
                {"id": "model:free", "name": "Free Model", "pricing": {"prompt": "0", "completion": "0"}},
                {"id": "gpt-5-turbo", "name": "GPT-5 Turbo", "pricing": {"prompt": "0.01", "completion": "0.02"}},
                {"id": "anthropic/claude-4.5-sonnet", "name": "Claude 4.5", "pricing": {"prompt": "0.01", "completion": "0.02"}},
            ]
        }

        mock_client = AsyncMock()
        mock_client.get.return_value = mock_response
        mock_client.__aenter__.return_value = mock_client
        mock_client.__aexit__.return_value = None
        mock_client_class.return_value = mock_client

        try:
            result = await chat.list_models()

            assert "models" in result
            # Should include Ollama models + filtered OpenRouter models
            model_ids = [m["id"] for m in result["models"]]
            assert any("ollama" in mid for mid in model_ids)
        finally:
            chat.OPENROUTER_API_KEY = original_key

    @pytest.mark.asyncio
    @patch("httpx.AsyncClient")
    async def test_list_models_handles_api_error(self, mock_client_class):
        """list_models() should return fallback on API error."""
        chat.models_cache["data"] = None
        original_key = chat.OPENROUTER_API_KEY
        chat.OPENROUTER_API_KEY = "test-key"

        mock_client = AsyncMock()
        mock_client.get.side_effect = Exception("API Error")
        mock_client.__aenter__.return_value = mock_client
        mock_client.__aexit__.return_value = None
        mock_client_class.return_value = mock_client

        try:
            result = await chat.list_models()

            # Should return fallback
            assert "models" in result
            assert len(result["models"]) > 0
        finally:
            chat.OPENROUTER_API_KEY = original_key


# ============ Random Question Endpoint Tests ============


class TestRandomQuestionEndpoint:
    """Tests for /random-question endpoint."""

    @pytest.mark.asyncio
    async def test_random_question_returns_default_on_empty_collection(self):
        """get_random_question() should return default if collection is empty."""
        with patch.object(chat, "get_qdrant_client") as mock_get_client:
            mock_client = MagicMock()
            mock_collection = MagicMock()
            mock_collection.points_count = 0
            mock_client.get_collection.return_value = mock_collection
            mock_get_client.return_value = mock_client

            result = await chat.get_random_question()

            assert "question" in result
            assert result["question"] == "What are the best practices for building AI agents?"

    @pytest.mark.asyncio
    async def test_random_question_uses_tags(self):
        """get_random_question() should use tags from indexed content."""
        with patch.object(chat, "get_qdrant_client") as mock_get_client:
            mock_client = MagicMock()
            mock_collection = MagicMock()
            mock_collection.points_count = 100
            mock_client.get_collection.return_value = mock_collection

            # Mock scroll result with tags
            mock_point = MagicMock()
            mock_point.payload = {
                "tags": ["Python", "AI"],
                "metadata": {"title": "Test Video"}
            }
            mock_client.scroll.return_value = ([mock_point], None)
            mock_get_client.return_value = mock_client

            result = await chat.get_random_question()

            assert "question" in result
            # Should be one of the tag-based or title-based questions
            assert any(keyword in result["question"] for keyword in ["Python", "AI", "Test Video", "What", "Tell", "Summarize"])

    @pytest.mark.asyncio
    async def test_random_question_handles_error(self):
        """get_random_question() should return default on error."""
        with patch.object(chat, "get_qdrant_client") as mock_get_client:
            mock_get_client.side_effect = Exception("Connection failed")

            result = await chat.get_random_question()

            assert "question" in result
            assert result["question"] == "What are the best practices for building AI agents?"


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

        # Mock Qdrant search results
        mock_qdrant = MagicMock()
        mock_point = MagicMock()
        mock_point.payload = {
            "text": "Sample content",
            "video_id": "youtube:abc123",
            "video_title": "Test Video",
            "url": "https://youtube.com/watch?v=abc123",
            "tags": ["Python", "AI"],
        }
        mock_qdrant.query_points.return_value = MagicMock(points=[mock_point])

        async def mock_embedding(text):
            return [0.1] * 384

        with patch.object(chat, "get_openrouter_client", return_value=mock_openrouter):
            with patch.object(chat, "get_qdrant_client", return_value=mock_qdrant):
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


# ============ Embedding Tests ============


class TestEmbedding:
    """Tests for get_embedding function."""

    @pytest.mark.asyncio
    @patch("httpx.AsyncClient")
    async def test_get_embedding_returns_vector(self, mock_client_class):
        """get_embedding() should return embedding vector."""
        mock_response = MagicMock()
        mock_response.raise_for_status = MagicMock()
        mock_response.json.return_value = {
            "data": [{"embedding": [0.1, 0.2, 0.3]}]
        }

        mock_client = AsyncMock()
        mock_client.post.return_value = mock_response
        mock_client.__aenter__.return_value = mock_client
        mock_client.__aexit__.return_value = None
        mock_client_class.return_value = mock_client

        result = await chat.get_embedding("test text")

        assert result == [0.1, 0.2, 0.3]

    @pytest.mark.asyncio
    @patch("httpx.AsyncClient")
    async def test_get_embedding_raises_on_error(self, mock_client_class):
        """get_embedding() should raise on HTTP error."""
        mock_response = MagicMock()
        mock_response.raise_for_status.side_effect = Exception("HTTP Error")

        mock_client = AsyncMock()
        mock_client.post.return_value = mock_response
        mock_client.__aenter__.return_value = mock_client
        mock_client.__aexit__.return_value = None
        mock_client_class.return_value = mock_client

        with pytest.raises(Exception):
            await chat.get_embedding("test text")


# ============ Style Injection Tests ============


class TestStyleInjection:
    """Tests for writing style injection in chat."""

    def setup_method(self):
        """Reset clients before each test."""
        chat.reset_clients()

    def test_websocket_chat_applies_style(self, client):
        """WebSocket chat should apply style modifier to system message."""
        mock_openrouter = AsyncMock()
        captured_messages = []

        async def create_stream(*args, **kwargs):
            # Capture the messages passed to the LLM
            if "messages" in kwargs:
                captured_messages.extend(kwargs["messages"])

            class MockStream:
                def __aiter__(self):
                    return self

                async def __anext__(self):
                    raise StopAsyncIteration

            return MockStream()

        mock_openrouter.chat.completions.create = create_stream

        with patch.object(chat, "get_openrouter_client", return_value=mock_openrouter):
            with patch.object(chat, "get_conversation_service") as mock_conv_svc:
                with patch.object(chat, "get_project_service") as mock_proj_svc:
                    mock_conv_svc.return_value = MagicMock()
                    mock_proj_svc.return_value = MagicMock()
                    mock_proj_svc.return_value.get_project.return_value = None

                    with client.websocket_connect("/chat/ws/chat") as websocket:
                        websocket.send_text(json.dumps({
                            "message": "Hello",
                            "model": "test-model",
                            "style": "concise"  # Apply concise style
                        }))

                        # Get done response
                        response = websocket.receive_json()
                        assert response["type"] == "done"

        # Check that style modifier was applied
        assert len(captured_messages) >= 1
        system_msg = next((m for m in captured_messages if m.get("role") == "system"), None)
        assert system_msg is not None
        assert "STYLE INSTRUCTION" in system_msg["content"]
        assert "concise" in system_msg["content"].lower()

    def test_websocket_chat_no_style_modifier_for_default(self, client):
        """WebSocket chat should not add system message for default style."""
        mock_openrouter = AsyncMock()
        captured_messages = []

        async def create_stream(*args, **kwargs):
            if "messages" in kwargs:
                captured_messages.extend(kwargs["messages"])

            class MockStream:
                def __aiter__(self):
                    return self

                async def __anext__(self):
                    raise StopAsyncIteration

            return MockStream()

        mock_openrouter.chat.completions.create = create_stream

        with patch.object(chat, "get_openrouter_client", return_value=mock_openrouter):
            with patch.object(chat, "get_conversation_service") as mock_conv_svc:
                with patch.object(chat, "get_project_service") as mock_proj_svc:
                    mock_conv_svc.return_value = MagicMock()
                    mock_proj_svc.return_value = MagicMock()
                    mock_proj_svc.return_value.get_project.return_value = None

                    with client.websocket_connect("/chat/ws/chat") as websocket:
                        websocket.send_text(json.dumps({
                            "message": "Hello",
                            "model": "test-model",
                            "style": "default"
                        }))

                        response = websocket.receive_json()
                        assert response["type"] == "done"

        # Check no system message was added (default style has no modifier)
        system_msgs = [m for m in captured_messages if m.get("role") == "system"]
        assert len(system_msgs) == 0

    def test_websocket_rag_chat_applies_style(self, client):
        """WebSocket RAG chat should include style in augmented prompt."""
        mock_openrouter = AsyncMock()
        captured_messages = []

        async def create_stream(*args, **kwargs):
            if "messages" in kwargs:
                captured_messages.extend(kwargs["messages"])

            class MockStream:
                def __aiter__(self):
                    return self

                async def __anext__(self):
                    raise StopAsyncIteration

            return MockStream()

        mock_openrouter.chat.completions.create = create_stream

        with patch.object(chat, "get_openrouter_client", return_value=mock_openrouter):
            # Mock embedding to fail so we use fallback path (simpler to test)
            with patch.object(chat, "get_embedding", side_effect=Exception("Fail")):
                with patch.object(chat, "get_conversation_service") as mock_conv_svc:
                    with patch.object(chat, "get_project_service") as mock_proj_svc:
                        mock_conv_svc.return_value = MagicMock()
                        mock_proj_svc.return_value = MagicMock()
                        mock_proj_svc.return_value.get_project.return_value = None

                        with client.websocket_connect("/chat/ws/rag-chat") as websocket:
                            websocket.send_text(json.dumps({
                                "message": "Hello",
                                "model": "test-model",
                                "style": "technical"
                            }))

                            response = websocket.receive_json()
                            assert response["type"] == "done"

        # Check that style modifier appears in the prompt
        assert len(captured_messages) >= 1
        user_msg = captured_messages[0]  # RAG puts everything in user message
        assert "STYLE INSTRUCTION" in user_msg["content"]
        assert "technical" in user_msg["content"].lower()


# ============ Memory Injection Tests ============


class TestMemoryInjection:
    """Tests for memory context injection in chat."""

    def setup_method(self):
        """Reset clients before each test."""
        chat.reset_clients()

    def test_websocket_chat_applies_memory_context(self, client, tmp_path):
        """WebSocket chat should apply memory context to system message."""
        from compose.services.memory import MemoryService

        # Create a memory service with some memories
        memory_dir = tmp_path / "memory"
        memory_dir.mkdir()
        memory_service = MemoryService(str(memory_dir))
        memory_service.add_memory(content="User prefers Python programming")

        mock_openrouter = AsyncMock()
        captured_messages = []

        async def create_stream(*args, **kwargs):
            if "messages" in kwargs:
                captured_messages.extend(kwargs["messages"])

            class MockStream:
                def __aiter__(self):
                    return self

                async def __anext__(self):
                    raise StopAsyncIteration

            return MockStream()

        mock_openrouter.chat.completions.create = create_stream

        with patch.object(chat, "get_openrouter_client", return_value=mock_openrouter):
            with patch.object(chat, "get_conversation_service") as mock_conv_svc:
                with patch.object(chat, "get_project_service") as mock_proj_svc:
                    with patch("compose.api.routers.chat.get_memory_service", return_value=memory_service):
                        mock_conv_svc.return_value = MagicMock()
                        mock_proj_svc.return_value = MagicMock()
                        mock_proj_svc.return_value.get_project.return_value = None

                        with client.websocket_connect("/chat/ws/chat") as websocket:
                            websocket.send_text(json.dumps({
                                "message": "Help with Python",
                                "model": "test-model",
                                "use_memory": True
                            }))

                            response = websocket.receive_json()
                            assert response["type"] == "done"

        # Check that memory context was included
        system_msgs = [m for m in captured_messages if m.get("role") == "system"]
        assert len(system_msgs) >= 1
        assert "remember about the user" in system_msgs[0]["content"]
        assert "Python" in system_msgs[0]["content"]

    def test_websocket_chat_can_disable_memory(self, client, tmp_path):
        """WebSocket chat should skip memory when use_memory is False."""
        from compose.services.memory import MemoryService

        memory_dir = tmp_path / "memory"
        memory_dir.mkdir()
        memory_service = MemoryService(str(memory_dir))
        memory_service.add_memory(content="User prefers Python programming")

        mock_openrouter = AsyncMock()
        captured_messages = []

        async def create_stream(*args, **kwargs):
            if "messages" in kwargs:
                captured_messages.extend(kwargs["messages"])

            class MockStream:
                def __aiter__(self):
                    return self

                async def __anext__(self):
                    raise StopAsyncIteration

            return MockStream()

        mock_openrouter.chat.completions.create = create_stream

        with patch.object(chat, "get_openrouter_client", return_value=mock_openrouter):
            with patch.object(chat, "get_conversation_service") as mock_conv_svc:
                with patch.object(chat, "get_project_service") as mock_proj_svc:
                    with patch("compose.api.routers.chat.get_memory_service", return_value=memory_service):
                        mock_conv_svc.return_value = MagicMock()
                        mock_proj_svc.return_value = MagicMock()
                        mock_proj_svc.return_value.get_project.return_value = None

                        with client.websocket_connect("/chat/ws/chat") as websocket:
                            websocket.send_text(json.dumps({
                                "message": "Help with Python",
                                "model": "test-model",
                                "use_memory": False
                            }))

                            response = websocket.receive_json()
                            assert response["type"] == "done"

        # Check that no memory context was included
        system_msgs = [m for m in captured_messages if m.get("role") == "system"]
        # Should be empty or not contain memory context
        for msg in system_msgs:
            assert "remember about the user" not in msg.get("content", "")

    def test_websocket_rag_chat_applies_memory_context(self, client, tmp_path):
        """WebSocket RAG chat should include memory context in prompt."""
        from compose.services.memory import MemoryService

        memory_dir = tmp_path / "memory"
        memory_dir.mkdir()
        memory_service = MemoryService(str(memory_dir))
        memory_service.add_memory(content="User is expert in Python")

        mock_openrouter = AsyncMock()
        captured_messages = []

        async def create_stream(*args, **kwargs):
            if "messages" in kwargs:
                captured_messages.extend(kwargs["messages"])

            class MockStream:
                def __aiter__(self):
                    return self

                async def __anext__(self):
                    raise StopAsyncIteration

            return MockStream()

        mock_openrouter.chat.completions.create = create_stream

        with patch.object(chat, "get_openrouter_client", return_value=mock_openrouter):
            with patch.object(chat, "get_embedding", side_effect=Exception("Fail")):
                with patch.object(chat, "get_conversation_service") as mock_conv_svc:
                    with patch.object(chat, "get_project_service") as mock_proj_svc:
                        with patch("compose.api.routers.chat.get_memory_service", return_value=memory_service):
                            mock_conv_svc.return_value = MagicMock()
                            mock_proj_svc.return_value = MagicMock()
                            mock_proj_svc.return_value.get_project.return_value = None

                            with client.websocket_connect("/chat/ws/rag-chat") as websocket:
                                websocket.send_text(json.dumps({
                                    "message": "Help with Python code",
                                    "model": "test-model",
                                    "use_memory": True
                                }))

                                response = websocket.receive_json()
                                assert response["type"] == "done"

        # Check that memory context appears in the prompt
        assert len(captured_messages) >= 1
        user_msg = captured_messages[0]
        assert "remember about the user" in user_msg["content"]
        assert "Python" in user_msg["content"]
