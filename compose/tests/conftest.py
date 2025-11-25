"""
Pytest configuration and fixtures for compose/ tests.

Provides:
- Async test client for FastAPI endpoints
- Mock LLM client fixtures
- Mock Qdrant/vector store fixtures
- Test data fixtures
- Environment setup
"""

import os
from collections.abc import AsyncGenerator, Generator
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi.testclient import TestClient


# ============ Environment Setup ============


@pytest.fixture(scope="session", autouse=True)
def setup_test_environment():
    """Set up test environment variables."""
    # Set test-specific environment variables
    os.environ.setdefault("OPENROUTER_API_KEY", "test-key")
    os.environ.setdefault("ANTHROPIC_API_KEY", "test-anthropic-key")
    os.environ.setdefault("QDRANT_URL", "http://localhost:6333")
    os.environ.setdefault("INFINITY_URL", "http://localhost:7997")
    os.environ.setdefault("OLLAMA_URL", "http://localhost:11434")
    yield


# ============ FastAPI Test Client ============


@pytest.fixture
def app():
    """Create FastAPI app instance for testing."""
    from compose.api.main import app

    return app


@pytest.fixture
def client(app) -> Generator[TestClient, None, None]:
    """Synchronous test client for FastAPI."""
    with TestClient(app) as c:
        yield c


@pytest.fixture
async def async_client(app) -> AsyncGenerator:
    """Async test client for FastAPI."""
    from httpx import ASGITransport, AsyncClient

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as ac:
        yield ac


# ============ Mock LLM Client ============


@pytest.fixture
def mock_openai_client():
    """Mock OpenAI client for testing."""
    mock = MagicMock()

    # Mock chat completion response
    mock_response = MagicMock()
    mock_response.choices = [
        MagicMock(
            message=MagicMock(content="Test response from LLM"),
            finish_reason="stop",
        )
    ]
    mock_response.usage = MagicMock(prompt_tokens=10, completion_tokens=20)

    mock.chat.completions.create.return_value = mock_response

    return mock


@pytest.fixture
def mock_openai_streaming():
    """Mock OpenAI streaming client for testing."""
    mock = MagicMock()

    # Create streaming chunks
    def create_stream():
        chunks = [
            MagicMock(choices=[MagicMock(delta=MagicMock(content="Hello "))]),
            MagicMock(choices=[MagicMock(delta=MagicMock(content="world"))]),
            MagicMock(choices=[MagicMock(delta=MagicMock(content="!"))]),
            MagicMock(choices=[MagicMock(delta=MagicMock(content=None))]),
        ]
        for chunk in chunks:
            yield chunk

    mock.chat.completions.create.return_value = create_stream()

    return mock


@pytest.fixture
def mock_anthropic_client():
    """Mock Anthropic client for testing."""
    mock = MagicMock()

    mock_response = MagicMock()
    mock_response.content = [MagicMock(text="Test response from Claude")]
    mock_response.stop_reason = "end_turn"
    mock_response.usage = MagicMock(input_tokens=10, output_tokens=20)

    mock.messages.create.return_value = mock_response

    return mock


# ============ Mock Vector Store ============


@pytest.fixture
def mock_qdrant_client():
    """Mock Qdrant client for testing."""
    mock = MagicMock()

    # Mock search results
    mock_search_result = [
        MagicMock(
            id="doc-1",
            score=0.95,
            payload={"text": "Test document content", "source": "test.md"},
        ),
        MagicMock(
            id="doc-2",
            score=0.85,
            payload={"text": "Another document", "source": "other.md"},
        ),
    ]

    mock.search.return_value = mock_search_result
    mock.query_points.return_value = MagicMock(points=mock_search_result)

    # Mock collection operations
    mock.get_collections.return_value = MagicMock(
        collections=[MagicMock(name="test_collection")]
    )
    mock.collection_exists.return_value = True

    return mock


@pytest.fixture
def mock_embedding_service():
    """Mock embedding service for testing."""
    mock = AsyncMock()

    # Return fake embeddings (384-dim like MiniLM)
    mock.embed.return_value = [[0.1] * 384]
    mock.embed_batch.return_value = [[0.1] * 384, [0.2] * 384]

    return mock


# ============ Mock External Services ============


@pytest.fixture
def mock_youtube_transcript():
    """Mock YouTube transcript API."""
    with patch("youtube_transcript_api.YouTubeTranscriptApi") as mock:
        mock.get_transcript.return_value = [
            {"text": "Hello ", "start": 0.0, "duration": 1.0},
            {"text": "world", "start": 1.0, "duration": 1.0},
        ]
        yield mock


@pytest.fixture
def mock_httpx_client():
    """Mock httpx client for external HTTP calls."""
    mock = AsyncMock()

    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {"status": "ok"}
    mock_response.text = "OK"

    mock.get.return_value = mock_response
    mock.post.return_value = mock_response

    return mock


# ============ Test Data Fixtures ============


@pytest.fixture
def sample_conversation():
    """Sample conversation data for testing."""
    return {
        "id": "test-conv-123",
        "title": "Test Conversation",
        "created_at": "2025-01-01T00:00:00Z",
        "updated_at": "2025-01-01T00:00:00Z",
        "model": "gpt-4",
        "messages": [
            {
                "id": "msg-1",
                "role": "user",
                "content": "Hello",
                "timestamp": "2025-01-01T00:00:00Z",
            },
            {
                "id": "msg-2",
                "role": "assistant",
                "content": "Hi there!",
                "timestamp": "2025-01-01T00:00:01Z",
            },
        ],
    }


@pytest.fixture
def sample_project():
    """Sample project data for testing."""
    return {
        "id": "test-proj-123",
        "name": "Test Project",
        "description": "A test project",
        "created_at": "2025-01-01T00:00:00Z",
        "updated_at": "2025-01-01T00:00:00Z",
        "custom_instructions": "Be helpful",
        "conversation_ids": [],
        "files": [],
    }


@pytest.fixture
def sample_chat_message():
    """Sample chat message for WebSocket testing."""
    return {
        "type": "message",
        "content": "What is Python?",
        "model": "gpt-4",
        "conversation_id": "test-conv-123",
    }


# ============ WebSocket Testing ============


@pytest.fixture
def websocket_client(client):
    """WebSocket test client context manager."""

    class WebSocketTestClient:
        def __init__(self, test_client, path):
            self.test_client = test_client
            self.path = path
            self._ws = None

        def __enter__(self):
            self._ws = self.test_client.websocket_connect(self.path)
            self._ws.__enter__()
            return self._ws

        def __exit__(self, *args):
            if self._ws:
                self._ws.__exit__(*args)

    def create_ws(path: str):
        return WebSocketTestClient(client, path)

    return create_ws


# ============ SSE Streaming Tests ============


@pytest.fixture
def mock_sse_client():
    """Mock SSE client for testing Server-Sent Events."""

    class MockSSEClient:
        """Mock client that simulates SSE event stream."""

        def __init__(self):
            self.events = []
            self.closed = False

        async def __aiter__(self):
            """Async iterator for events."""
            for event in self.events:
                if self.closed:
                    break
                yield event

        def add_event(self, event_type: str, data: dict):
            """Add an event to the stream."""
            self.events.append({"type": event_type, "data": data})

        def close(self):
            """Simulate client disconnect."""
            self.closed = True

    return MockSSEClient()


@pytest.fixture
def mock_video_metadata():
    """Standard test video metadata."""
    return {
        "video_id": "test_vid123",  # Must be 11 chars for YouTube ID format
        "title": "Test Video Title",
        "url": "https://youtube.com/watch?v=test_vid123",
        "channel_id": "test_channel",
        "channel_name": "Test Channel",
        "duration_seconds": 300,
        "view_count": 1000,
        "published_at": "2025-01-01T00:00:00Z",
        "fetched_at": "2025-01-24T00:00:00Z",
    }


@pytest.fixture
def mock_transcript():
    """Standard test transcript."""
    return """This is a test transcript for video ingestion testing.
It contains multiple sentences across several lines.
This simulates a real YouTube transcript with meaningful content.
The transcript should be long enough to test chunking and embedding."""


@pytest.fixture
def mock_youtube_service():
    """Mock YouTube service for ingestion testing."""
    with patch("compose.services.youtube.get_transcript") as mock_get_transcript:
        # Mock successful transcript fetch
        mock_get_transcript.return_value = """This is a test transcript for video ingestion testing.
It contains multiple sentences across several lines.
This simulates a real YouTube transcript with meaningful content."""
        yield mock_get_transcript


@pytest.fixture
def mock_surrealdb_repository():
    """Mock SurrealDB repository operations."""
    # Create async mock functions
    mock_get = AsyncMock(return_value=None)  # Video doesn't exist
    mock_upsert = AsyncMock(return_value={"video_id": "test_vid123"})

    with patch("compose.services.surrealdb.get_video", mock_get), \
         patch("compose.services.surrealdb.upsert_video", mock_upsert):
        yield {"get_video": mock_get, "upsert_video": mock_upsert}


@pytest.fixture
def mock_minio_archive():
    """Mock MinIO archive writer."""
    mock_instance = MagicMock()
    mock_instance.archive_youtube_video.return_value = "archive/test_vid123.json"

    with patch("compose.services.archive.create_local_archive_writer", return_value=mock_instance):
        yield mock_instance


# ============ Temporary Data Directory ============


@pytest.fixture
def temp_data_dir(tmp_path):
    """Create temporary data directory for tests."""
    data_dir = tmp_path / "data"
    data_dir.mkdir()

    # Create subdirectories
    (data_dir / "conversations").mkdir()
    (data_dir / "projects").mkdir()
    (data_dir / "memory").mkdir()
    (data_dir / "artifacts").mkdir()

    # Create empty index files
    (data_dir / "conversations" / "index.json").write_text('{"conversations": []}')
    (data_dir / "projects" / "index.json").write_text('{"projects": []}')

    return data_dir
