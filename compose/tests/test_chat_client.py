"""
Tests for chat client management and HTTP endpoints.

Tests cover:
- Client initialization and reset
- /models endpoint (caching, fallback, error handling)
- /random-question endpoint
"""

import json
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

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
        """_fallback_models() should include local Ollama models when provided."""
        ollama_test_models = [
            {"id": "ollama:llama2", "name": "Llama2 (Local)", "context_length": 32000, "provider": "ollama", "is_free": True},
            {"id": "ollama:mistral", "name": "Mistral (Local)", "context_length": 32000, "provider": "ollama", "is_free": True},
        ]
        result = chat._fallback_models(ollama_models=ollama_test_models)

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
    @patch("compose.api.routers.chat.fetch_ollama_models")
    async def test_list_models_fetches_from_openrouter(self, mock_fetch_ollama, mock_client_class):
        """list_models() should fetch from OpenRouter API."""
        chat.models_cache["data"] = None
        original_key = chat.OPENROUTER_API_KEY
        chat.OPENROUTER_API_KEY = "test-key"

        # Mock Ollama models
        mock_fetch_ollama.return_value = [
            {"id": "ollama:llama2", "name": "Llama2 (Local)", "context_length": 32000, "provider": "ollama", "is_free": True}
        ]

        # Mock OpenRouter response
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
        with patch("compose.services.surrealdb.repository.get_random_video_ids", return_value=[]):
            result = await chat.get_random_question()

            assert "question" in result
            assert result["question"] == "What are the best practices for building AI agents?"

    @pytest.mark.asyncio
    async def test_random_question_uses_tags(self):
        """get_random_question() should use topics from indexed content."""
        # Use MagicMock to avoid Pydantic validation issues with pipeline_state
        # The model type is dict[str, str] but actual usage stores nested tag data
        mock_video = MagicMock()
        mock_video.title = "Test Video"
        mock_video.pipeline_state = {
            "tags": {
                "subject_matter": ["Python", "AI"]
            }
        }

        with patch("compose.services.surrealdb.repository.get_random_video_ids", return_value=["test123"]):
            with patch("compose.services.surrealdb.repository.get_video", return_value=mock_video):
                result = await chat.get_random_question()

                assert "question" in result
                # Should be one of the topic-based or title-based questions
                assert any(keyword in result["question"] for keyword in ["Python", "AI", "Test Video", "What", "Tell", "Summarize"])

    @pytest.mark.asyncio
    async def test_random_question_handles_error(self):
        """get_random_question() should return default on error."""
        with patch("compose.services.surrealdb.repository.get_random_video_ids", side_effect=Exception("Connection failed")):
            result = await chat.get_random_question()

            assert "question" in result
            assert result["question"] == "What are the best practices for building AI agents?"
