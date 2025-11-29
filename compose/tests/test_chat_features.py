"""
Tests for chat feature injection functionality.

Tests cover:
- Embedding generation
- Writing style injection
- Memory context injection
"""

import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from compose.api.routers import chat


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
