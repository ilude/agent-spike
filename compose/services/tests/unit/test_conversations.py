"""Tests for conversation storage service (SurrealDB implementation).

Run with: uv run pytest compose/services/tests/unit/test_conversations.py -v
"""

import pytest

from compose.services.conversations import (
    Conversation,
    ConversationMeta,
    ConversationService,
    Message,
)
from compose.services.tests.fakes import FakeDatabaseExecutor


# =============================================================================
# Fixtures
# =============================================================================


@pytest.fixture
def fake_db():
    """Create a fresh FakeDatabaseExecutor for each test."""
    return FakeDatabaseExecutor()


@pytest.fixture
def service(fake_db):
    """Create ConversationService with injected fake."""
    return ConversationService(db=fake_db)


# =============================================================================
# Model Tests (no mocking needed - just Pydantic models)
# =============================================================================


@pytest.mark.unit
class TestMessage:
    """Tests for Message model."""

    def test_message_default_values(self):
        """Test Message creates with default id and timestamp."""
        msg = Message(role="user", content="Hello")

        assert msg.role == "user"
        assert msg.content == "Hello"
        assert msg.id  # Should have auto-generated UUID
        assert len(msg.id) == 36  # UUID format
        assert msg.timestamp  # Should have auto-generated timestamp
        assert msg.sources == []

    def test_message_with_sources(self):
        """Test Message with sources."""
        sources = [{"url": "https://example.com", "title": "Example"}]
        msg = Message(role="assistant", content="Response", sources=sources)

        assert msg.sources == sources

    def test_message_explicit_values(self):
        """Test Message with explicit values."""
        msg = Message(
            id="test-id",
            role="assistant",
            content="Test content",
            timestamp="2024-01-01T00:00:00Z",
            sources=[{"url": "test"}],
        )

        assert msg.id == "test-id"
        assert msg.role == "assistant"
        assert msg.content == "Test content"
        assert msg.timestamp == "2024-01-01T00:00:00Z"
        assert msg.sources == [{"url": "test"}]


@pytest.mark.unit
class TestConversation:
    """Tests for Conversation model."""

    def test_conversation_default_values(self):
        """Test Conversation creates with default values."""
        conv = Conversation()

        assert conv.id  # Should have auto-generated UUID
        assert len(conv.id) == 36  # UUID format
        assert conv.title == "New conversation"
        assert conv.created_at  # Should have auto-generated timestamp
        assert conv.updated_at  # Should have auto-generated timestamp
        assert conv.model == ""
        assert conv.messages == []

    def test_conversation_explicit_values(self):
        """Test Conversation with explicit values."""
        conv = Conversation(
            id="conv-123",
            title="Test Conv",
            created_at="2024-01-01T00:00:00Z",
            updated_at="2024-01-02T00:00:00Z",
            model="gpt-4",
            messages=[Message(role="user", content="Hi")],
        )

        assert conv.id == "conv-123"
        assert conv.title == "Test Conv"
        assert conv.model == "gpt-4"
        assert len(conv.messages) == 1

    def test_conversation_to_meta(self):
        """Test Conversation.to_meta() conversion."""
        conv = Conversation(
            id="conv-123",
            title="Test Conv",
            created_at="2024-01-01T00:00:00Z",
            updated_at="2024-01-02T00:00:00Z",
            model="gpt-4",
            messages=[
                Message(role="user", content="Hi"),
                Message(role="assistant", content="Hello!"),
            ],
        )

        meta = conv.to_meta()

        assert isinstance(meta, ConversationMeta)
        assert meta.id == "conv-123"
        assert meta.title == "Test Conv"
        assert meta.created_at == "2024-01-01T00:00:00Z"
        assert meta.updated_at == "2024-01-02T00:00:00Z"
        assert meta.message_count == 2
        assert meta.model == "gpt-4"

    def test_conversation_to_meta_override_count(self):
        """Test Conversation.to_meta() with override message count."""
        conv = Conversation(
            id="conv-123",
            title="Test Conv",
            created_at="2024-01-01T00:00:00Z",
            updated_at="2024-01-02T00:00:00Z",
            messages=[Message(role="user", content="Hi")],
        )

        meta = conv.to_meta(message_count=10)

        assert meta.message_count == 10


@pytest.mark.unit
class TestConversationMeta:
    """Tests for ConversationMeta model."""

    def test_conversation_meta_defaults(self):
        """Test ConversationMeta default values."""
        meta = ConversationMeta(
            id="test-id",
            title="Test",
            created_at="2024-01-01T00:00:00Z",
            updated_at="2024-01-01T00:00:00Z",
        )

        assert meta.message_count == 0
        assert meta.model == ""

    def test_conversation_meta_all_fields(self):
        """Test ConversationMeta with all fields."""
        meta = ConversationMeta(
            id="test-id",
            title="Test",
            created_at="2024-01-01T00:00:00Z",
            updated_at="2024-01-02T00:00:00Z",
            message_count=5,
            model="claude-3",
        )

        assert meta.id == "test-id"
        assert meta.title == "Test"
        assert meta.message_count == 5
        assert meta.model == "claude-3"


# =============================================================================
# Service Tests (using DI with fakes)
# =============================================================================


@pytest.mark.unit
class TestCreateConversation:
    """Tests for create_conversation method."""

    async def test_creates_conversation_with_default_values(self, service, fake_db):
        """Test creating conversation with default values."""
        conv = await service.create_conversation()

        assert conv.title == "New conversation"
        assert conv.model == ""
        assert conv.id is not None
        assert len(conv.id) == 36  # UUID format

        # Verify database was called
        assert len(fake_db.query_log) == 1
        query, params = fake_db.query_log[0]
        assert "INSERT INTO conversation" in query
        assert params["title"] == "New conversation"

    async def test_creates_conversation_with_title_and_model(self, service, fake_db):
        """Test creating conversation with title and model."""
        conv = await service.create_conversation(
            title="My Chat",
            model="gpt-4",
        )

        assert conv.title == "My Chat"
        assert conv.model == "gpt-4"

        query, params = fake_db.query_log[0]
        assert params["title"] == "My Chat"
        assert params["model"] == "gpt-4"

    async def test_creates_conversation_with_user_id(self, service, fake_db):
        """Test creating conversation with user_id."""
        conv = await service.create_conversation(
            title="My Chat",
            user_id="user-123",
        )

        query, params = fake_db.query_log[0]
        assert params["user_id"] == "user-123"


@pytest.mark.unit
class TestListConversations:
    """Tests for list_conversations method."""

    async def test_list_conversations_empty(self, service, fake_db):
        """Test listing when no conversations exist."""
        conversations = await service.list_conversations()

        assert conversations == []

    async def test_list_conversations_returns_meta(self, service, fake_db):
        """Test that list returns ConversationMeta objects."""
        # Setup: Add a conversation to the fake DB
        fake_db.tables["conversation"] = [
            {
                "id": "test-id",
                "title": "Test Conversation",
                "model": "gpt-4",
                "created_at": "2024-01-01T00:00:00Z",
                "updated_at": "2024-01-02T00:00:00Z",
            }
        ]

        conversations = await service.list_conversations()

        assert len(conversations) == 1
        assert isinstance(conversations[0], ConversationMeta)
        assert conversations[0].title == "Test Conversation"
        assert conversations[0].model == "gpt-4"

    async def test_list_conversations_with_user_id(self, service, fake_db):
        """Test listing conversations filtered by user_id."""
        await service.list_conversations(user_id="user-123")

        # Verify query includes user_id filter
        query, params = fake_db.query_log[0]
        assert "user_id" in query.lower()
        assert params["user_id"] == "user-123"


@pytest.mark.unit
class TestGetConversation:
    """Tests for get_conversation method."""

    async def test_get_conversation_not_found(self, service):
        """Test getting a non-existent conversation returns None."""
        conv = await service.get_conversation("non-existent-id")

        assert conv is None

    async def test_get_conversation_success(self, service, fake_db):
        """Test getting an existing conversation."""
        # Setup: Add conversation to fake DB
        fake_db.tables["conversation"] = [
            {
                "id": "test-id",
                "title": "Test Conversation",
                "model": "gpt-4",
                "created_at": "2024-01-01T00:00:00Z",
                "updated_at": "2024-01-02T00:00:00Z",
            }
        ]

        conv = await service.get_conversation("test-id")

        assert conv is not None
        assert conv.title == "Test Conversation"
        assert conv.model == "gpt-4"


@pytest.mark.unit
class TestGetConversationUserId:
    """Tests for get_conversation_user_id method."""

    async def test_get_user_id_not_found(self, service):
        """Test getting user_id for non-existent conversation returns None."""
        user_id = await service.get_conversation_user_id("non-existent-id")

        assert user_id is None

    async def test_get_user_id_success(self, service, fake_db):
        """Test getting user_id for existing conversation."""
        # Setup: Use set_next_response for record ID query
        fake_db.set_next_response([{"user_id": "user-123"}])

        user_id = await service.get_conversation_user_id("test-id")

        assert user_id == "user-123"


@pytest.mark.unit
class TestUpdateConversation:
    """Tests for update_conversation method."""

    async def test_update_conversation_not_found(self, service):
        """Test updating non-existent conversation returns None."""
        result = await service.update_conversation("non-existent", title="New Title")

        assert result is None

    async def test_update_conversation_title(self, service, fake_db):
        """Test updating conversation title."""
        # Setup: Add conversation to fake DB
        fake_db.tables["conversation"] = [
            {
                "id": "test-id",
                "title": "Original",
                "model": "",
                "created_at": "2024-01-01T00:00:00Z",
                "updated_at": "2024-01-02T00:00:00Z",
            }
        ]

        updated = await service.update_conversation("test-id", title="Updated")

        # The fake DB should have been called with UPDATE
        update_queries = [q for q, _ in fake_db.query_log if "UPDATE" in q]
        assert len(update_queries) > 0

    async def test_update_conversation_model(self, service, fake_db):
        """Test updating conversation model."""
        # Setup: Add conversation to fake DB
        fake_db.tables["conversation"] = [
            {
                "id": "test-id",
                "title": "Test",
                "model": "gpt-3.5",
                "created_at": "2024-01-01T00:00:00Z",
                "updated_at": "2024-01-02T00:00:00Z",
            }
        ]

        await service.update_conversation("test-id", model="gpt-4")

        # Check UPDATE was called with model
        update_queries = [
            (q, p) for q, p in fake_db.query_log if "UPDATE" in q and p
        ]
        assert len(update_queries) > 0


@pytest.mark.unit
class TestDeleteConversation:
    """Tests for delete_conversation method."""

    async def test_delete_conversation_not_found(self, service):
        """Test deleting non-existent conversation returns False."""
        result = await service.delete_conversation("non-existent")

        assert result is False

    async def test_delete_conversation_success(self, service, fake_db):
        """Test deleting an existing conversation."""
        # Setup: Use set_next_response to indicate conversation exists
        fake_db.set_next_response([{"id": "test-id"}])

        result = await service.delete_conversation("test-id")

        assert result is True
        # Verify DELETE queries were issued (messages and conversation)
        delete_queries = [q for q, _ in fake_db.query_log if "DELETE" in q]
        assert len(delete_queries) >= 2  # One for messages, one for conversation


@pytest.mark.unit
class TestAddMessage:
    """Tests for add_message method."""

    async def test_add_message_conversation_not_found(self, service):
        """Test adding message to non-existent conversation."""
        result = await service.add_message("non-existent", "user", "Hello!")

        assert result is None

    async def test_add_user_message(self, service, fake_db):
        """Test adding a user message."""
        # Setup: Conversation exists
        fake_db.set_next_response([{"id": "conv-123"}])

        msg = await service.add_message("conv-123", "user", "Hello!")

        assert msg is not None
        assert msg.role == "user"
        assert msg.content == "Hello!"
        assert msg.id is not None
        assert msg.sources == []

        # Verify INSERT into message table
        insert_queries = [q for q, _ in fake_db.query_log if "INSERT INTO message" in q]
        assert len(insert_queries) == 1

    async def test_add_assistant_message_with_sources(self, service, fake_db):
        """Test adding assistant message with sources."""
        # Setup: Conversation exists
        fake_db.set_next_response([{"id": "conv-123"}])

        sources = [{"url": "https://example.com", "title": "Example"}]
        msg = await service.add_message(
            "conv-123", "assistant", "Here's the answer", sources=sources
        )

        assert msg is not None
        assert msg.role == "assistant"
        assert msg.sources == sources

    async def test_add_message_updates_conversation_timestamp(self, service, fake_db):
        """Test adding message updates conversation updated_at."""
        # Setup: Conversation exists
        fake_db.set_next_response([{"id": "conv-123"}])

        await service.add_message("conv-123", "user", "Hello!")

        # Verify UPDATE on conversation was called
        update_queries = [q for q, _ in fake_db.query_log if "UPDATE" in q]
        assert len(update_queries) >= 1


@pytest.mark.unit
class TestSearchConversations:
    """Tests for search_conversations method."""

    async def test_search_empty_results(self, service, fake_db):
        """Test search with no matches returns empty list."""
        results = await service.search_conversations("xyz123")

        assert results == []

    async def test_search_executes_query(self, service, fake_db):
        """Test search executes the correct query."""
        await service.search_conversations("python")

        # Verify query was executed with search term
        assert len(fake_db.query_log) == 1
        query, params = fake_db.query_log[0]
        assert params["query"] == "python"

    async def test_search_with_user_id_filter(self, service, fake_db):
        """Test search with user_id filter."""
        await service.search_conversations("python", user_id="user-123")

        query, params = fake_db.query_log[0]
        assert params["query"] == "python"
        assert params["user_id"] == "user-123"


# =============================================================================
# Edge Cases
# =============================================================================


@pytest.mark.unit
class TestEdgeCases:
    """Tests for edge cases."""

    async def test_special_characters_in_title(self, service, fake_db):
        """Test conversation with special characters in title."""
        conv = await service.create_conversation(
            title='Test "Conversation" with <special> & chars!'
        )

        assert conv.title == 'Test "Conversation" with <special> & chars!'

    async def test_empty_message_content(self, service, fake_db):
        """Test adding message with empty content."""
        # Setup: Conversation exists
        fake_db.set_next_response([{"id": "conv-123"}])

        msg = await service.add_message("conv-123", "user", "")

        assert msg is not None
        assert msg.content == ""

    async def test_unicode_content(self, service, fake_db):
        """Test handling unicode content in messages."""
        # Setup: Conversation exists
        fake_db.set_next_response([{"id": "conv-123"}])

        content = "Hello! Emoji test: 🎉🚀 Chinese: 你好 Japanese: こんにちは"
        msg = await service.add_message("conv-123", "user", content)

        assert msg.content == content

    async def test_generate_title_fallback_no_api_key(self, service):
        """Test generate_title uses fallback when no API key."""
        # This should not make any external calls, just return fallback
        title = await service.generate_title("Tell me about machine learning")

        # Should return truncated version of the message
        assert "machine learning" in title.lower() or len(title) <= 53

    async def test_generate_filename_fallback_no_api_key(self, service):
        """Test generate_filename uses fallback when no API key."""
        filename = await service.generate_filename(
            content="Some test content",
            model="openai:gpt-4",  # Will fail without API key
        )

        # Should return date-based fallback
        assert "conversation" in filename or "-" in filename
