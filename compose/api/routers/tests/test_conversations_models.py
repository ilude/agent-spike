"""Tests for conversations router request/response models.

Run with: uv run pytest compose/api/routers/tests/test_conversations_models.py
"""

import pytest
from pydantic import ValidationError

from compose.api.routers.conversations import (
    CreateConversationRequest,
    UpdateConversationRequest,
    SearchRequest,
    GenerateTitleRequest,
    GenerateTitleResponse,
    ConversationListResponse,
)
from compose.services.conversations import ConversationMeta


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
# Test: Pydantic Request/Response Models
# =============================================================================


@pytest.mark.unit
class TestCreateConversationRequest:
    """Tests for CreateConversationRequest model."""

    def test_default_values(self):
        """Verify default values are applied."""
        request = CreateConversationRequest()
        assert request.title == "New conversation"
        assert request.model == ""

    def test_custom_values(self):
        """Verify custom values are accepted."""
        request = CreateConversationRequest(title="Custom Title", model="gpt-4")
        assert request.title == "Custom Title"
        assert request.model == "gpt-4"

    def test_partial_values(self):
        """Verify partial values with defaults."""
        request = CreateConversationRequest(title="My Title")
        assert request.title == "My Title"
        assert request.model == ""


@pytest.mark.unit
class TestUpdateConversationRequest:
    """Tests for UpdateConversationRequest model."""

    def test_all_none_default(self):
        """Verify all fields default to None."""
        request = UpdateConversationRequest()
        assert request.title is None
        assert request.model is None

    def test_partial_update(self):
        """Verify partial update fields."""
        request = UpdateConversationRequest(title="Updated Title")
        assert request.title == "Updated Title"
        assert request.model is None

    def test_full_update(self):
        """Verify full update fields."""
        request = UpdateConversationRequest(title="New Title", model="claude-3")
        assert request.title == "New Title"
        assert request.model == "claude-3"


@pytest.mark.unit
class TestSearchRequest:
    """Tests for SearchRequest model."""

    def test_valid_query(self):
        """Verify valid query is accepted."""
        request = SearchRequest(query="test search")
        assert request.query == "test search"

    def test_query_required(self):
        """Verify query is required."""
        with pytest.raises(ValidationError):
            SearchRequest()


@pytest.mark.unit
class TestGenerateTitleRequest:
    """Tests for GenerateTitleRequest model."""

    def test_valid_message(self):
        """Verify valid message is accepted."""
        request = GenerateTitleRequest(message="How do I build an AI agent?")
        assert request.message == "How do I build an AI agent?"

    def test_message_required(self):
        """Verify message is required."""
        with pytest.raises(ValidationError):
            GenerateTitleRequest()


@pytest.mark.unit
class TestGenerateTitleResponse:
    """Tests for GenerateTitleResponse model."""

    def test_valid_title(self):
        """Verify valid title is accepted."""
        response = GenerateTitleResponse(title="Building AI Agents")
        assert response.title == "Building AI Agents"

    def test_title_required(self):
        """Verify title is required."""
        with pytest.raises(ValidationError):
            GenerateTitleResponse()

    def test_serialization(self):
        """Verify response serializes correctly."""
        response = GenerateTitleResponse(title="Test Title")
        serialized = response.model_dump()
        assert serialized == {"title": "Test Title"}


@pytest.mark.unit
class TestConversationListResponse:
    """Tests for ConversationListResponse model."""

    def test_empty_list(self):
        """Verify empty conversations list is accepted."""
        response = ConversationListResponse(conversations=[])
        assert response.conversations == []

    def test_with_conversations(self, sample_conversation_meta):
        """Verify conversations list is accepted."""
        response = ConversationListResponse(conversations=[sample_conversation_meta])
        assert len(response.conversations) == 1
        assert response.conversations[0].id == "test-conv-123"
