"""Tests for conversations router endpoints.

Run with: uv run pytest compose/api/routers/tests/test_conversations_endpoints.py
"""

import pytest
from unittest.mock import patch, MagicMock, AsyncMock
from fastapi import FastAPI
from fastapi.testclient import TestClient

from compose.api.routers.conversations import router
from compose.services.conversations import (
    Conversation,
    ConversationMeta,
)


# Create a test app with the router
app = FastAPI()
app.include_router(router)


@pytest.fixture
def client():
    """Create test client for the router."""
    return TestClient(app)


@pytest.fixture
def mock_service():
    """Create a mock conversation service."""
    service = MagicMock()
    return service


@pytest.fixture
def sample_conversation():
    """Create a sample conversation for testing."""
    return Conversation(
        id="test-conv-123",
        title="Test Conversation",
        model="test-model",
        messages=[],
    )


@pytest.fixture
def sample_conversation_meta():
    """Create sample conversation metadata for testing."""
    return ConversationMeta(
        id="test-conv-123",
        title="Test Conversation",
        created_at="2024-01-01T00:00:00Z",
        updated_at="2024-01-01T00:00:00Z",
        message_count=0,
        model="test-model",
    )


# =============================================================================
# Test: GET /conversations - list_conversations
# =============================================================================


@pytest.mark.unit
class TestListConversations:
    """Tests for list_conversations endpoint."""

    def test_returns_empty_list(self, client, mock_service):
        """Verify empty list when no conversations exist."""
        mock_service.list_conversations.return_value = []

        with patch(
            "compose.api.routers.conversations.get_conversation_service",
            return_value=mock_service,
        ):
            response = client.get("/conversations")

        assert response.status_code == 200
        data = response.json()
        assert data == {"conversations": []}

    def test_returns_conversations_list(
        self, client, mock_service, sample_conversation_meta
    ):
        """Verify conversations are returned."""
        mock_service.list_conversations.return_value = [sample_conversation_meta]

        with patch(
            "compose.api.routers.conversations.get_conversation_service",
            return_value=mock_service,
        ):
            response = client.get("/conversations")

        assert response.status_code == 200
        data = response.json()
        assert len(data["conversations"]) == 1
        assert data["conversations"][0]["id"] == "test-conv-123"
        assert data["conversations"][0]["title"] == "Test Conversation"


# =============================================================================
# Test: POST /conversations - create_conversation
# =============================================================================


@pytest.mark.unit
class TestCreateConversation:
    """Tests for create_conversation endpoint."""

    def test_create_with_defaults(self, client, mock_service, sample_conversation):
        """Verify conversation created with default values."""
        mock_service.create_conversation.return_value = sample_conversation

        with patch(
            "compose.api.routers.conversations.get_conversation_service",
            return_value=mock_service,
        ):
            response = client.post("/conversations", json={})

        assert response.status_code == 200
        mock_service.create_conversation.assert_called_once_with(
            title="New conversation",
            model="",
        )

    def test_create_with_custom_values(self, client, mock_service, sample_conversation):
        """Verify conversation created with custom values."""
        mock_service.create_conversation.return_value = sample_conversation

        with patch(
            "compose.api.routers.conversations.get_conversation_service",
            return_value=mock_service,
        ):
            response = client.post(
                "/conversations",
                json={"title": "My Chat", "model": "gpt-4"},
            )

        assert response.status_code == 200
        mock_service.create_conversation.assert_called_once_with(
            title="My Chat",
            model="gpt-4",
        )

    def test_create_returns_conversation(
        self, client, mock_service, sample_conversation
    ):
        """Verify created conversation is returned."""
        mock_service.create_conversation.return_value = sample_conversation

        with patch(
            "compose.api.routers.conversations.get_conversation_service",
            return_value=mock_service,
        ):
            response = client.post("/conversations", json={})

        assert response.status_code == 200
        data = response.json()
        assert data["id"] == "test-conv-123"
        assert data["title"] == "Test Conversation"


# =============================================================================
# Test: GET /conversations/search - search_conversations
# =============================================================================


@pytest.mark.unit
class TestSearchConversations:
    """Tests for search_conversations endpoint."""

    def test_search_returns_results(
        self, client, mock_service, sample_conversation_meta
    ):
        """Verify search returns matching conversations."""
        mock_service.search_conversations.return_value = [sample_conversation_meta]

        with patch(
            "compose.api.routers.conversations.get_conversation_service",
            return_value=mock_service,
        ):
            response = client.get("/conversations/search", params={"q": "test"})

        assert response.status_code == 200
        data = response.json()
        assert len(data["conversations"]) == 1
        mock_service.search_conversations.assert_called_once_with("test")

    def test_search_returns_empty_list(self, client, mock_service):
        """Verify search returns empty list when no matches."""
        mock_service.search_conversations.return_value = []

        with patch(
            "compose.api.routers.conversations.get_conversation_service",
            return_value=mock_service,
        ):
            response = client.get("/conversations/search", params={"q": "nonexistent"})

        assert response.status_code == 200
        data = response.json()
        assert data == {"conversations": []}

    def test_search_query_too_short_empty(self, client, mock_service):
        """Verify 400 error for empty query."""
        with patch(
            "compose.api.routers.conversations.get_conversation_service",
            return_value=mock_service,
        ):
            response = client.get("/conversations/search", params={"q": ""})

        assert response.status_code == 400
        assert "at least 2 characters" in response.json()["detail"]

    def test_search_query_too_short_one_char(self, client, mock_service):
        """Verify 400 error for single character query."""
        with patch(
            "compose.api.routers.conversations.get_conversation_service",
            return_value=mock_service,
        ):
            response = client.get("/conversations/search", params={"q": "a"})

        assert response.status_code == 400
        assert "at least 2 characters" in response.json()["detail"]

    def test_search_query_minimum_length(self, client, mock_service):
        """Verify 2-character query is accepted."""
        mock_service.search_conversations.return_value = []

        with patch(
            "compose.api.routers.conversations.get_conversation_service",
            return_value=mock_service,
        ):
            response = client.get("/conversations/search", params={"q": "ab"})

        assert response.status_code == 200


# =============================================================================
# Test: GET /conversations/{conversation_id} - get_conversation
# =============================================================================


@pytest.mark.unit
class TestGetConversation:
    """Tests for get_conversation endpoint."""

    def test_get_existing_conversation(
        self, client, mock_service, sample_conversation
    ):
        """Verify existing conversation is returned."""
        mock_service.get_conversation.return_value = sample_conversation

        with patch(
            "compose.api.routers.conversations.get_conversation_service",
            return_value=mock_service,
        ):
            response = client.get("/conversations/test-conv-123")

        assert response.status_code == 200
        data = response.json()
        assert data["id"] == "test-conv-123"
        assert data["title"] == "Test Conversation"
        mock_service.get_conversation.assert_called_once_with("test-conv-123")

    def test_get_nonexistent_conversation(self, client, mock_service):
        """Verify 404 for nonexistent conversation."""
        mock_service.get_conversation.return_value = None

        with patch(
            "compose.api.routers.conversations.get_conversation_service",
            return_value=mock_service,
        ):
            response = client.get("/conversations/nonexistent-id")

        assert response.status_code == 404
        assert response.json()["detail"] == "Conversation not found"


# =============================================================================
# Test: PUT /conversations/{conversation_id} - update_conversation
# =============================================================================


@pytest.mark.unit
class TestUpdateConversation:
    """Tests for update_conversation endpoint."""

    def test_update_title(self, client, mock_service, sample_conversation):
        """Verify title update works."""
        updated_conversation = Conversation(
            id="test-conv-123",
            title="Updated Title",
            model="test-model",
        )
        mock_service.update_conversation.return_value = updated_conversation

        with patch(
            "compose.api.routers.conversations.get_conversation_service",
            return_value=mock_service,
        ):
            response = client.put(
                "/conversations/test-conv-123",
                json={"title": "Updated Title"},
            )

        assert response.status_code == 200
        data = response.json()
        assert data["title"] == "Updated Title"
        mock_service.update_conversation.assert_called_once_with(
            "test-conv-123",
            title="Updated Title",
            model=None,
        )

    def test_update_model(self, client, mock_service, sample_conversation):
        """Verify model update works."""
        updated_conversation = Conversation(
            id="test-conv-123",
            title="Test Conversation",
            model="claude-3",
        )
        mock_service.update_conversation.return_value = updated_conversation

        with patch(
            "compose.api.routers.conversations.get_conversation_service",
            return_value=mock_service,
        ):
            response = client.put(
                "/conversations/test-conv-123",
                json={"model": "claude-3"},
            )

        assert response.status_code == 200
        data = response.json()
        assert data["model"] == "claude-3"

    def test_update_both_fields(self, client, mock_service):
        """Verify both title and model can be updated."""
        updated_conversation = Conversation(
            id="test-conv-123",
            title="New Title",
            model="new-model",
        )
        mock_service.update_conversation.return_value = updated_conversation

        with patch(
            "compose.api.routers.conversations.get_conversation_service",
            return_value=mock_service,
        ):
            response = client.put(
                "/conversations/test-conv-123",
                json={"title": "New Title", "model": "new-model"},
            )

        assert response.status_code == 200
        mock_service.update_conversation.assert_called_once_with(
            "test-conv-123",
            title="New Title",
            model="new-model",
        )

    def test_update_nonexistent_conversation(self, client, mock_service):
        """Verify 404 for nonexistent conversation."""
        mock_service.update_conversation.return_value = None

        with patch(
            "compose.api.routers.conversations.get_conversation_service",
            return_value=mock_service,
        ):
            response = client.put(
                "/conversations/nonexistent-id",
                json={"title": "New Title"},
            )

        assert response.status_code == 404
        assert response.json()["detail"] == "Conversation not found"


# =============================================================================
# Test: DELETE /conversations/{conversation_id} - delete_conversation
# =============================================================================


@pytest.mark.unit
class TestDeleteConversation:
    """Tests for delete_conversation endpoint."""

    def test_delete_existing_conversation(self, client, mock_service):
        """Verify successful deletion returns status."""
        mock_service.delete_conversation.return_value = True

        with patch(
            "compose.api.routers.conversations.get_conversation_service",
            return_value=mock_service,
        ):
            response = client.delete("/conversations/test-conv-123")

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "deleted"
        assert data["id"] == "test-conv-123"
        mock_service.delete_conversation.assert_called_once_with("test-conv-123")

    def test_delete_nonexistent_conversation(self, client, mock_service):
        """Verify 404 for nonexistent conversation."""
        mock_service.delete_conversation.return_value = False

        with patch(
            "compose.api.routers.conversations.get_conversation_service",
            return_value=mock_service,
        ):
            response = client.delete("/conversations/nonexistent-id")

        assert response.status_code == 404
        assert response.json()["detail"] == "Conversation not found"


# =============================================================================
# Test: POST /conversations/generate-title - generate_title
# =============================================================================


@pytest.mark.unit
class TestGenerateTitle:
    """Tests for generate_title endpoint."""

    def test_generate_title_success(self, client, mock_service):
        """Verify successful title generation."""
        mock_service.generate_title = AsyncMock(return_value="AI Agent Development")

        with patch(
            "compose.api.routers.conversations.get_conversation_service",
            return_value=mock_service,
        ):
            response = client.post(
                "/conversations/generate-title",
                json={"message": "How do I build an AI agent with Python?"},
            )

        assert response.status_code == 200
        data = response.json()
        assert data["title"] == "AI Agent Development"

    def test_generate_title_message_too_short_empty(self, client, mock_service):
        """Verify 400 error for empty message."""
        with patch(
            "compose.api.routers.conversations.get_conversation_service",
            return_value=mock_service,
        ):
            response = client.post(
                "/conversations/generate-title",
                json={"message": ""},
            )

        assert response.status_code == 400
        assert "at least 3 characters" in response.json()["detail"]

    def test_generate_title_message_too_short_two_chars(self, client, mock_service):
        """Verify 400 error for 2-character message."""
        with patch(
            "compose.api.routers.conversations.get_conversation_service",
            return_value=mock_service,
        ):
            response = client.post(
                "/conversations/generate-title",
                json={"message": "Hi"},
            )

        assert response.status_code == 400
        assert "at least 3 characters" in response.json()["detail"]

    def test_generate_title_minimum_length(self, client, mock_service):
        """Verify 3-character message is accepted."""
        mock_service.generate_title = AsyncMock(return_value="Hey")

        with patch(
            "compose.api.routers.conversations.get_conversation_service",
            return_value=mock_service,
        ):
            response = client.post(
                "/conversations/generate-title",
                json={"message": "Hey"},
            )

        assert response.status_code == 200

    def test_generate_title_long_message(self, client, mock_service):
        """Verify long message is accepted."""
        long_message = "This is a very long message " * 100
        mock_service.generate_title = AsyncMock(return_value="Long Message Title")

        with patch(
            "compose.api.routers.conversations.get_conversation_service",
            return_value=mock_service,
        ):
            response = client.post(
                "/conversations/generate-title",
                json={"message": long_message},
            )

        assert response.status_code == 200
        mock_service.generate_title.assert_called_once_with(long_message)
