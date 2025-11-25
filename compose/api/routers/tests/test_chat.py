"""Characterization tests for chat router.

These tests capture CURRENT behavior - not intended to refactor the code,
just to document how it works and ensure we don't break it unintentionally.
"""

from datetime import datetime, timezone

import pytest
from unittest.mock import patch, MagicMock, AsyncMock
from fastapi import FastAPI
from fastapi.testclient import TestClient

from compose.api.routers.chat import (
    router,
    list_models,
    get_random_question,
    _fallback_models,
    models_cache,
    reset_clients,
    get_openrouter_client,
    get_ollama_client,
    get_qdrant_client,
    ModelsResponse,
)
from compose.services.tests.conftest import (
    create_mock_qdrant_client,
    create_mock_openai_client,
    create_mock_httpx_client,
)


# Create a test app with the router
app = FastAPI()
app.include_router(router)


@pytest.fixture
def client():
    """Create test client for the router."""
    return TestClient(app)


@pytest.fixture(autouse=True)
def reset_cache_and_clients():
    """Reset cache and clients before each test."""
    models_cache["data"] = None
    models_cache["timestamp"] = None
    reset_clients()
    yield
    # Cleanup after test
    models_cache["data"] = None
    models_cache["timestamp"] = None
    reset_clients()


# =============================================================================
# Test: list_models returns expected structure
# =============================================================================


@pytest.mark.unit
@pytest.mark.asyncio
async def test_list_models_returns_model_structure():
    """Verify /models endpoint returns expected model structure."""
    mock_httpx = create_mock_httpx_client(
        responses={
            "openrouter.ai/api/v1/models": {
                "data": [
                    {
                        "id": "test-model:free",
                        "name": "Test Model (free)",
                        "context_length": 8192,
                        "pricing": {"prompt": "0", "completion": "0"},
                    },
                    {
                        "id": "openai/gpt-5",
                        "name": "GPT-5",
                        "context_length": 128000,
                        "pricing": {"prompt": "0.01", "completion": "0.03"},
                    },
                    {
                        "id": "anthropic/claude-4.5-sonnet",
                        "name": "Claude 4.5 Sonnet",
                        "context_length": 200000,
                        "pricing": {"prompt": "0.003", "completion": "0.015"},
                    },
                    {
                        "id": "some-paid-model",
                        "name": "Paid Model",
                        "context_length": 4096,
                        "pricing": {"prompt": "0.01", "completion": "0.02"},
                    },
                ]
            }
        }
    )

    with (
        patch("compose.api.routers.chat.OPENROUTER_API_KEY", "test-key"),
        patch("compose.api.routers.chat.httpx.AsyncClient") as mock_client_class,
    ):
        mock_client_class.return_value = mock_httpx

        result = await list_models()

        # Should return a dict with 'models' key
        assert "models" in result
        assert isinstance(result["models"], list)

        # Should have at least the ollama models prepended
        ollama_models = [m for m in result["models"] if m.get("is_local")]
        assert len(ollama_models) >= 2

        # All models should have expected keys
        for model in result["models"]:
            assert "id" in model
            assert "name" in model
            assert "is_free" in model


@pytest.mark.unit
@pytest.mark.asyncio
async def test_list_models_filters_correctly():
    """Verify models are filtered correctly (free, gpt-5, claude 4.5)."""
    mock_httpx = create_mock_httpx_client(
        responses={
            "openrouter.ai/api/v1/models": {
                "data": [
                    # Free model - should be included
                    {
                        "id": "free-model:free",
                        "name": "Free Model (free)",
                        "context_length": 8192,
                        "pricing": {"prompt": "0", "completion": "0"},
                    },
                    # GPT-5 model - should be included
                    {
                        "id": "openai/gpt-5-turbo",
                        "name": "GPT-5 Turbo",
                        "context_length": 128000,
                        "pricing": {"prompt": "0.01", "completion": "0.03"},
                    },
                    # Claude 4.5 - should be included
                    {
                        "id": "anthropic/claude-4.5-opus",
                        "name": "Claude 4.5 Opus",
                        "context_length": 200000,
                        "pricing": {"prompt": "0.015", "completion": "0.075"},
                    },
                    # Paid non-special model - should be EXCLUDED
                    {
                        "id": "random/paid-model",
                        "name": "Random Paid Model",
                        "context_length": 4096,
                        "pricing": {"prompt": "0.01", "completion": "0.02"},
                    },
                    # GPT-5.1 - should be EXCLUDED (5.1 filter)
                    {
                        "id": "openai/gpt-5.1-turbo",
                        "name": "GPT-5.1 Turbo",
                        "context_length": 128000,
                        "pricing": {"prompt": "0.01", "completion": "0.03"},
                    },
                    # GPT-5 image - should be EXCLUDED (image filter)
                    {
                        "id": "openai/gpt-5-image",
                        "name": "GPT-5 Image",
                        "context_length": 128000,
                        "pricing": {"prompt": "0.01", "completion": "0.03"},
                    },
                ]
            }
        }
    )

    with (
        patch("compose.api.routers.chat.OPENROUTER_API_KEY", "test-key"),
        patch("compose.api.routers.chat.httpx.AsyncClient") as mock_client_class,
    ):
        mock_client_class.return_value = mock_httpx

        result = await list_models()

        model_ids = [m["id"] for m in result["models"]]

        # Should include: ollama models + free + gpt-5 + claude 4.5
        assert "ollama:qwen3:8b" in model_ids
        assert "ollama:qwen2.5:7b" in model_ids
        assert "free-model:free" in model_ids
        assert "openai/gpt-5-turbo" in model_ids
        assert "anthropic/claude-4.5-opus" in model_ids

        # Should exclude: paid non-special + gpt-5.1 + gpt-5-image
        assert "random/paid-model" not in model_ids
        assert "openai/gpt-5.1-turbo" not in model_ids
        assert "openai/gpt-5-image" not in model_ids


# =============================================================================
# Test: list_models uses cache
# =============================================================================


@pytest.mark.unit
@pytest.mark.asyncio
async def test_list_models_uses_cache():
    """Verify caching behavior - second call should use cached data."""
    mock_httpx = create_mock_httpx_client(
        responses={
            "openrouter.ai/api/v1/models": {
                "data": [
                    {
                        "id": "test:free",
                        "name": "Test (free)",
                        "context_length": 8192,
                        "pricing": {"prompt": "0", "completion": "0"},
                    },
                ]
            }
        }
    )

    with (
        patch("compose.api.routers.chat.OPENROUTER_API_KEY", "test-key"),
        patch("compose.api.routers.chat.httpx.AsyncClient") as mock_client_class,
    ):
        mock_client_class.return_value = mock_httpx

        # First call - should make HTTP request
        result1 = await list_models()
        assert mock_client_class.call_count == 1

        # Second call - should use cache
        result2 = await list_models()
        assert mock_client_class.call_count == 1  # No additional HTTP call

        # Results should be the same
        assert result1 == result2


@pytest.mark.unit
@pytest.mark.asyncio
async def test_list_models_cache_expires():
    """Verify cache expires after TTL."""
    from datetime import datetime

    mock_httpx = create_mock_httpx_client(
        responses={
            "openrouter.ai/api/v1/models": {
                "data": [
                    {
                        "id": "test:free",
                        "name": "Test (free)",
                        "context_length": 8192,
                        "pricing": {"prompt": "0", "completion": "0"},
                    },
                ]
            }
        }
    )

    call_count = 0

    async def counting_aenter(self):
        nonlocal call_count
        call_count += 1
        return mock_httpx

    mock_httpx.__aenter__ = counting_aenter

    with (
        patch("compose.api.routers.chat.OPENROUTER_API_KEY", "test-key"),
        patch("compose.api.routers.chat.httpx.AsyncClient") as mock_client_class,
    ):
        mock_client_class.return_value = mock_httpx

        # First call
        await list_models()
        assert call_count == 1

        # Simulate cache expiry by manipulating timestamp
        models_cache["timestamp"] = datetime.now(timezone.utc).timestamp() - 400  # > 300 TTL

        # Third call - should make new request (cache expired)
        await list_models()
        assert call_count == 2


# =============================================================================
# Test: random_question returns expected structure
# =============================================================================


@pytest.mark.unit
@pytest.mark.asyncio
async def test_random_question_returns_question():
    """Verify /random-question endpoint returns question structure."""
    mock_qdrant = create_mock_qdrant_client(
        points_count=50,
        scroll_results=[
            {
                "payload": {
                    "tags": ["ai", "agents", "tutorial"],
                    "metadata": {"title": "Test Video About AI"},
                    "meta_youtube_title": "YouTube Title",
                }
            },
            {
                "payload": {
                    "metadata": {"subject": ["machine learning"]},
                    "value": {"title": "Another Video"},
                }
            },
        ],
    )

    with patch(
        "compose.api.routers.chat.get_qdrant_client", return_value=mock_qdrant
    ):
        result = await get_random_question()

        # Should return a dict with 'question' key
        assert "question" in result
        assert isinstance(result["question"], str)
        assert len(result["question"]) > 0


@pytest.mark.unit
@pytest.mark.asyncio
async def test_random_question_empty_collection():
    """Verify fallback question when collection is empty."""
    mock_qdrant = create_mock_qdrant_client(points_count=0)

    with patch(
        "compose.api.routers.chat.get_qdrant_client", return_value=mock_qdrant
    ):
        result = await get_random_question()

        # Should return fallback question
        assert result["question"] == "What are the best practices for building AI agents?"


@pytest.mark.unit
@pytest.mark.asyncio
async def test_random_question_error_handling():
    """Verify error handling returns fallback question."""
    mock_qdrant = MagicMock()
    mock_qdrant.get_collection.side_effect = Exception("Connection failed")

    with patch(
        "compose.api.routers.chat.get_qdrant_client", return_value=mock_qdrant
    ):
        result = await get_random_question()

        # Should return fallback question on error
        assert result["question"] == "What are the best practices for building AI agents?"


@pytest.mark.unit
@pytest.mark.asyncio
async def test_random_question_generates_from_tags():
    """Verify questions are generated from video tags."""
    mock_qdrant = create_mock_qdrant_client(
        points_count=100,
        scroll_results=[
            {"payload": {"tags": ["python", "fastapi"]}},
        ],
    )

    with patch(
        "compose.api.routers.chat.get_qdrant_client", return_value=mock_qdrant
    ):
        # Run multiple times to check question variety
        questions = set()
        for _ in range(20):
            result = await get_random_question()
            questions.add(result["question"])

        # Should generate questions containing tags
        all_questions_text = " ".join(questions)
        assert "python" in all_questions_text.lower() or "fastapi" in all_questions_text.lower()


# =============================================================================
# Test: fallback_models structure
# =============================================================================


@pytest.mark.unit
def test_fallback_models_structure():
    """Verify _fallback_models returns expected structure."""
    result = _fallback_models()

    # Should return dict with 'models' key
    assert "models" in result
    assert isinstance(result["models"], list)
    assert len(result["models"]) > 0

    # All models should have expected keys
    for model in result["models"]:
        assert "id" in model
        assert "name" in model
        assert "context_length" in model
        assert "is_free" in model


@pytest.mark.unit
def test_fallback_models_includes_ollama():
    """Verify fallback includes local Ollama models."""
    result = _fallback_models()

    ollama_models = [m for m in result["models"] if m.get("is_local")]
    assert len(ollama_models) >= 2

    model_ids = [m["id"] for m in result["models"]]
    assert "ollama:qwen3:8b" in model_ids
    assert "ollama:qwen2.5:7b" in model_ids


@pytest.mark.unit
def test_fallback_models_includes_free_openrouter():
    """Verify fallback includes free OpenRouter models."""
    result = _fallback_models()

    # Check for known free models
    model_ids = [m["id"] for m in result["models"]]
    free_models = [m for m in result["models"] if m.get("is_free") and not m.get("is_local")]
    assert len(free_models) > 0


# =============================================================================
# Test: ModelsResponse Pydantic model
# =============================================================================


@pytest.mark.unit
def test_models_response_model_structure():
    """Verify ModelsResponse Pydantic model accepts expected structure."""
    response = ModelsResponse(models=[
        {"id": "test-model", "name": "Test Model", "is_free": True}
    ])
    assert response.models == [{"id": "test-model", "name": "Test Model", "is_free": True}]


@pytest.mark.unit
def test_models_response_model_empty_list():
    """Verify ModelsResponse accepts empty models list."""
    response = ModelsResponse(models=[])
    assert response.models == []


@pytest.mark.unit
def test_models_response_model_fields():
    """Verify ModelsResponse has expected fields."""
    expected_fields = {"models"}
    actual_fields = set(ModelsResponse.model_fields.keys())
    assert actual_fields == expected_fields


@pytest.mark.unit
def test_models_response_serialization():
    """Verify ModelsResponse serializes correctly."""
    response = ModelsResponse(models=[
        {"id": "ollama:test", "name": "Test", "context_length": 32000, "is_free": True}
    ])
    serialized = response.model_dump()
    assert serialized["models"][0]["id"] == "ollama:test"
    assert serialized["models"][0]["context_length"] == 32000


# =============================================================================
# Test: Client lazy initialization pattern
# =============================================================================


@pytest.mark.unit
def test_client_getters_return_none_initially():
    """Verify lazy init pattern - clients are None before first use."""
    # Ensure clients are reset
    reset_clients()

    # Access module-level variables directly to check they're None
    import compose.api.routers.chat as chat_module
    assert chat_module._openrouter_client is None
    assert chat_module._ollama_client is None
    assert chat_module._qdrant_client is None


@pytest.mark.unit
def test_get_openrouter_client_returns_none_without_api_key():
    """Verify get_openrouter_client returns None when API key not set."""
    reset_clients()

    with patch("compose.api.routers.chat.OPENROUTER_API_KEY", None):
        client = get_openrouter_client()
        assert client is None


@pytest.mark.unit
def test_get_ollama_client_creates_client():
    """Verify get_ollama_client creates client on first call."""
    reset_clients()

    client = get_ollama_client()
    assert client is not None
    # Second call returns same instance
    client2 = get_ollama_client()
    assert client is client2


@pytest.mark.unit
def test_get_qdrant_client_creates_client():
    """Verify get_qdrant_client creates client on first call."""
    reset_clients()

    # Mock QdrantClient to avoid actual connection
    with patch("compose.api.routers.chat.QdrantClient") as mock_qdrant_class:
        mock_instance = MagicMock()
        mock_qdrant_class.return_value = mock_instance

        client = get_qdrant_client()
        assert client is mock_instance
        mock_qdrant_class.assert_called_once()

        # Second call returns same instance (no new constructor call)
        client2 = get_qdrant_client()
        assert client2 is mock_instance
        assert mock_qdrant_class.call_count == 1


@pytest.mark.unit
def test_reset_clients_clears_all():
    """Verify reset_clients clears all client instances."""
    import compose.api.routers.chat as chat_module

    # Set some non-None values
    chat_module._openrouter_client = MagicMock()
    chat_module._ollama_client = MagicMock()
    chat_module._qdrant_client = MagicMock()

    reset_clients()

    assert chat_module._openrouter_client is None
    assert chat_module._ollama_client is None
    assert chat_module._qdrant_client is None


# =============================================================================
# Test: list_models with no API key
# =============================================================================


@pytest.mark.unit
@pytest.mark.asyncio
async def test_list_models_no_api_key_returns_fallback():
    """Verify fallback is returned when no API key configured."""
    with patch("compose.api.routers.chat.OPENROUTER_API_KEY", None):
        result = await list_models()

        # Should return fallback models
        assert "models" in result
        fallback = _fallback_models()
        assert result == fallback


@pytest.mark.unit
@pytest.mark.asyncio
async def test_list_models_api_error_returns_fallback():
    """Verify fallback is returned when API call fails."""
    mock_httpx = MagicMock()
    mock_httpx.__aenter__ = AsyncMock(side_effect=Exception("API Error"))
    mock_httpx.__aexit__ = AsyncMock(return_value=None)

    with (
        patch("compose.api.routers.chat.OPENROUTER_API_KEY", "test-key"),
        patch("compose.api.routers.chat.httpx.AsyncClient") as mock_client_class,
    ):
        mock_client_class.return_value = mock_httpx

        result = await list_models()

        # Should return fallback models on error
        assert "models" in result
        fallback = _fallback_models()
        assert result == fallback


# =============================================================================
# Test: HTTP endpoint integration
# =============================================================================


@pytest.mark.unit
def test_models_endpoint_http(client):
    """Test /models endpoint via HTTP client."""
    with patch("compose.api.routers.chat.OPENROUTER_API_KEY", None):
        response = client.get("/models")

        assert response.status_code == 200
        data = response.json()
        assert "models" in data
        assert isinstance(data["models"], list)


@pytest.mark.unit
def test_random_question_endpoint_http(client):
    """Test /random-question endpoint via HTTP client."""
    mock_qdrant = create_mock_qdrant_client(
        points_count=50,
        scroll_results=[
            {"payload": {"tags": ["test-tag"], "meta_youtube_title": "Test Video"}},
        ],
    )

    with patch(
        "compose.api.routers.chat.get_qdrant_client", return_value=mock_qdrant
    ):
        response = client.get("/random-question")

        assert response.status_code == 200
        data = response.json()
        assert "question" in data
        assert isinstance(data["question"], str)
