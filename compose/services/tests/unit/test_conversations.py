"""Tests for conversation storage service.

Run with: uv run pytest compose/services/tests/unit/test_conversations.py
"""

import json
import time
from pathlib import Path

import pytest

from compose.services.conversations import (
    Conversation,
    ConversationMeta,
    ConversationService,
    Message,
)


# =============================================================================
# Fixtures
# =============================================================================


@pytest.fixture
def service(tmp_path):
    """Create service with temp directory."""
    return ConversationService(data_dir=str(tmp_path))


@pytest.fixture
def populated_service(service):
    """Create service with some existing conversations."""
    # Create three conversations with different timestamps
    conv1 = service.create_conversation(title="First Chat", model="gpt-4")
    time.sleep(0.01)  # Ensure different timestamps
    conv2 = service.create_conversation(title="Second Chat", model="claude-3")
    time.sleep(0.01)
    conv3 = service.create_conversation(title="Third Chat", model="gpt-4")

    # Add messages to conv2
    service.add_message(conv2.id, "user", "Hello there!")
    service.add_message(conv2.id, "assistant", "Hi! How can I help?")

    return service, conv1, conv2, conv3


# =============================================================================
# Model Tests
# =============================================================================


class TestMessage:
    """Tests for Message model."""

    def test_message_default_values(self):
        """Test Message creates with default id and timestamp."""
        msg = Message(role="user", content="Hello")

        assert msg.role == "user"
        assert msg.content == "Hello"
        assert msg.id  # Should have auto-generated UUID
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


class TestConversation:
    """Tests for Conversation model."""

    def test_conversation_default_values(self):
        """Test Conversation creates with default values."""
        conv = Conversation()

        assert conv.id  # Should have auto-generated UUID
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
# Service Initialization Tests
# =============================================================================


class TestConversationServiceInit:
    """Tests for ConversationService.__init__()."""

    def test_creates_data_directory(self, tmp_path):
        """Test __init__ creates data directory if not exists."""
        data_dir = tmp_path / "conversations"
        assert not data_dir.exists()

        service = ConversationService(data_dir=str(data_dir))

        assert data_dir.exists()
        assert data_dir.is_dir()

    def test_creates_index_file(self, tmp_path):
        """Test __init__ creates index.json if not exists."""
        service = ConversationService(data_dir=str(tmp_path))

        index_path = tmp_path / "index.json"
        assert index_path.exists()

        with open(index_path) as f:
            data = json.load(f)
        assert data == {"conversations": []}

    def test_preserves_existing_index(self, tmp_path):
        """Test __init__ preserves existing index.json."""
        # Create existing index
        index_path = tmp_path / "index.json"
        existing_data = {
            "conversations": [
                {
                    "id": "existing-id",
                    "title": "Existing",
                    "created_at": "2024-01-01T00:00:00Z",
                    "updated_at": "2024-01-01T00:00:00Z",
                    "message_count": 0,
                    "model": "",
                }
            ]
        }
        with open(index_path, "w") as f:
            json.dump(existing_data, f)

        service = ConversationService(data_dir=str(tmp_path))

        with open(index_path) as f:
            data = json.load(f)
        assert len(data["conversations"]) == 1
        assert data["conversations"][0]["id"] == "existing-id"

    def test_nested_directory_creation(self, tmp_path):
        """Test __init__ creates nested directory structure."""
        nested_path = tmp_path / "deep" / "nested" / "conversations"
        assert not nested_path.exists()

        service = ConversationService(data_dir=str(nested_path))

        assert nested_path.exists()
        assert (nested_path / "index.json").exists()


# =============================================================================
# list_conversations Tests
# =============================================================================


class TestListConversations:
    """Tests for ConversationService.list_conversations()."""

    def test_list_empty(self, service):
        """Test listing conversations when none exist."""
        result = service.list_conversations()

        assert result == []

    def test_list_single_conversation(self, service):
        """Test listing single conversation."""
        created = service.create_conversation(title="Test", model="gpt-4")

        result = service.list_conversations()

        assert len(result) == 1
        assert result[0].id == created.id
        assert result[0].title == "Test"
        assert result[0].model == "gpt-4"

    def test_list_sorted_by_updated_at_desc(self, populated_service):
        """Test conversations are sorted by updated_at descending."""
        service, conv1, conv2, conv3 = populated_service

        result = service.list_conversations()

        # conv2 was updated most recently (messages added)
        # Then conv3 was created after conv2
        # conv1 was created first
        assert len(result) == 3
        # Most recently updated first
        ids = [r.id for r in result]
        assert ids[0] == conv2.id  # Had messages added, so most recent

    def test_list_returns_metadata_only(self, service):
        """Test list returns ConversationMeta instances."""
        service.create_conversation(title="Test")

        result = service.list_conversations()

        assert all(isinstance(r, ConversationMeta) for r in result)


# =============================================================================
# create_conversation Tests
# =============================================================================


class TestCreateConversation:
    """Tests for ConversationService.create_conversation()."""

    def test_create_with_defaults(self, service, tmp_path):
        """Test creating conversation with default values."""
        conv = service.create_conversation()

        assert conv.id
        assert conv.title == "New conversation"
        assert conv.model == ""
        assert conv.messages == []

        # Verify file created
        conv_file = tmp_path / f"{conv.id}.json"
        assert conv_file.exists()

    def test_create_with_custom_values(self, service):
        """Test creating conversation with custom title and model."""
        conv = service.create_conversation(title="My Chat", model="claude-3")

        assert conv.title == "My Chat"
        assert conv.model == "claude-3"

    def test_create_updates_index(self, service, tmp_path):
        """Test creating conversation updates index.json."""
        conv = service.create_conversation(title="Test")

        with open(tmp_path / "index.json") as f:
            data = json.load(f)

        assert len(data["conversations"]) == 1
        assert data["conversations"][0]["id"] == conv.id
        assert data["conversations"][0]["title"] == "Test"

    def test_create_multiple_conversations(self, service):
        """Test creating multiple conversations."""
        conv1 = service.create_conversation(title="First")
        conv2 = service.create_conversation(title="Second")
        conv3 = service.create_conversation(title="Third")

        result = service.list_conversations()

        assert len(result) == 3
        ids = {r.id for r in result}
        assert conv1.id in ids
        assert conv2.id in ids
        assert conv3.id in ids

    def test_create_generates_unique_ids(self, service):
        """Test each conversation gets unique ID."""
        ids = set()
        for _ in range(10):
            conv = service.create_conversation()
            ids.add(conv.id)

        assert len(ids) == 10


# =============================================================================
# get_conversation Tests
# =============================================================================


class TestGetConversation:
    """Tests for ConversationService.get_conversation()."""

    def test_get_existing_conversation(self, service):
        """Test getting existing conversation by ID."""
        created = service.create_conversation(title="Test", model="gpt-4")

        result = service.get_conversation(created.id)

        assert result is not None
        assert result.id == created.id
        assert result.title == "Test"
        assert result.model == "gpt-4"

    def test_get_nonexistent_conversation(self, service):
        """Test getting non-existent conversation returns None."""
        result = service.get_conversation("nonexistent-id")

        assert result is None

    def test_get_conversation_with_messages(self, service):
        """Test getting conversation preserves messages."""
        conv = service.create_conversation()
        service.add_message(conv.id, "user", "Hello")
        service.add_message(conv.id, "assistant", "Hi there!")

        result = service.get_conversation(conv.id)

        assert len(result.messages) == 2
        assert result.messages[0].role == "user"
        assert result.messages[0].content == "Hello"
        assert result.messages[1].role == "assistant"
        assert result.messages[1].content == "Hi there!"

    def test_get_returns_full_conversation(self, service):
        """Test get returns Conversation instance, not ConversationMeta."""
        created = service.create_conversation()

        result = service.get_conversation(created.id)

        assert isinstance(result, Conversation)
        assert hasattr(result, "messages")


# =============================================================================
# update_conversation Tests
# =============================================================================


class TestUpdateConversation:
    """Tests for ConversationService.update_conversation()."""

    def test_update_title(self, service):
        """Test updating conversation title."""
        conv = service.create_conversation(title="Original")

        result = service.update_conversation(conv.id, title="Updated")

        assert result is not None
        assert result.title == "Updated"

        # Verify persisted
        fetched = service.get_conversation(conv.id)
        assert fetched.title == "Updated"

    def test_update_model(self, service):
        """Test updating conversation model."""
        conv = service.create_conversation(model="gpt-3.5")

        result = service.update_conversation(conv.id, model="gpt-4")

        assert result.model == "gpt-4"

        # Verify persisted
        fetched = service.get_conversation(conv.id)
        assert fetched.model == "gpt-4"

    def test_update_both_title_and_model(self, service):
        """Test updating both title and model."""
        conv = service.create_conversation(title="Old", model="gpt-3.5")

        result = service.update_conversation(conv.id, title="New", model="gpt-4")

        assert result.title == "New"
        assert result.model == "gpt-4"

    def test_update_updates_timestamp(self, service):
        """Test update changes updated_at timestamp."""
        conv = service.create_conversation()
        original_updated = conv.updated_at

        time.sleep(0.01)  # Ensure different timestamp
        result = service.update_conversation(conv.id, title="New Title")

        assert result.updated_at > original_updated

    def test_update_nonexistent_returns_none(self, service):
        """Test updating non-existent conversation returns None."""
        result = service.update_conversation("nonexistent-id", title="Test")

        assert result is None

    def test_update_preserves_messages(self, service):
        """Test update preserves existing messages."""
        conv = service.create_conversation()
        service.add_message(conv.id, "user", "Hello")

        service.update_conversation(conv.id, title="Updated")

        fetched = service.get_conversation(conv.id)
        assert len(fetched.messages) == 1
        assert fetched.messages[0].content == "Hello"

    def test_update_updates_index(self, service, tmp_path):
        """Test update modifies index.json."""
        conv = service.create_conversation(title="Original")

        service.update_conversation(conv.id, title="Updated")

        with open(tmp_path / "index.json") as f:
            data = json.load(f)

        assert data["conversations"][0]["title"] == "Updated"


# =============================================================================
# delete_conversation Tests
# =============================================================================


class TestDeleteConversation:
    """Tests for ConversationService.delete_conversation()."""

    def test_delete_existing_conversation(self, service, tmp_path):
        """Test deleting existing conversation."""
        conv = service.create_conversation()
        conv_path = tmp_path / f"{conv.id}.json"
        assert conv_path.exists()

        result = service.delete_conversation(conv.id)

        assert result is True
        assert not conv_path.exists()

    def test_delete_removes_from_index(self, service, tmp_path):
        """Test delete removes entry from index.json."""
        conv = service.create_conversation()

        service.delete_conversation(conv.id)

        with open(tmp_path / "index.json") as f:
            data = json.load(f)
        assert len(data["conversations"]) == 0

    def test_delete_nonexistent_returns_false(self, service):
        """Test deleting non-existent conversation returns False."""
        result = service.delete_conversation("nonexistent-id")

        assert result is False

    def test_delete_one_of_many(self, service):
        """Test deleting one conversation leaves others intact."""
        conv1 = service.create_conversation(title="Keep 1")
        conv2 = service.create_conversation(title="Delete Me")
        conv3 = service.create_conversation(title="Keep 2")

        service.delete_conversation(conv2.id)

        result = service.list_conversations()
        ids = {r.id for r in result}

        assert len(result) == 2
        assert conv1.id in ids
        assert conv2.id not in ids
        assert conv3.id in ids

    def test_get_after_delete_returns_none(self, service):
        """Test getting deleted conversation returns None."""
        conv = service.create_conversation()
        service.delete_conversation(conv.id)

        result = service.get_conversation(conv.id)

        assert result is None


# =============================================================================
# add_message Tests
# =============================================================================


class TestAddMessage:
    """Tests for ConversationService.add_message()."""

    def test_add_user_message(self, service):
        """Test adding user message."""
        conv = service.create_conversation()

        msg = service.add_message(conv.id, "user", "Hello!")

        assert msg is not None
        assert msg.role == "user"
        assert msg.content == "Hello!"
        assert msg.id
        assert msg.timestamp

    def test_add_assistant_message(self, service):
        """Test adding assistant message."""
        conv = service.create_conversation()

        msg = service.add_message(conv.id, "assistant", "Hi there!")

        assert msg.role == "assistant"
        assert msg.content == "Hi there!"

    def test_add_message_with_sources(self, service):
        """Test adding message with sources."""
        conv = service.create_conversation()
        sources = [
            {"url": "https://example.com", "title": "Example"},
            {"url": "https://test.com", "title": "Test"},
        ]

        msg = service.add_message(conv.id, "assistant", "Response", sources=sources)

        assert msg.sources == sources

    def test_add_message_persists(self, service):
        """Test added message is persisted."""
        conv = service.create_conversation()
        service.add_message(conv.id, "user", "Hello!")

        fetched = service.get_conversation(conv.id)

        assert len(fetched.messages) == 1
        assert fetched.messages[0].content == "Hello!"

    def test_add_multiple_messages(self, service):
        """Test adding multiple messages."""
        conv = service.create_conversation()
        service.add_message(conv.id, "user", "Hello!")
        service.add_message(conv.id, "assistant", "Hi!")
        service.add_message(conv.id, "user", "How are you?")

        fetched = service.get_conversation(conv.id)

        assert len(fetched.messages) == 3
        assert fetched.messages[0].content == "Hello!"
        assert fetched.messages[1].content == "Hi!"
        assert fetched.messages[2].content == "How are you?"

    def test_add_message_updates_timestamp(self, service):
        """Test adding message updates conversation updated_at."""
        conv = service.create_conversation()
        original_updated = conv.updated_at

        time.sleep(0.01)
        service.add_message(conv.id, "user", "Hello!")

        fetched = service.get_conversation(conv.id)
        assert fetched.updated_at > original_updated

    def test_add_message_updates_index(self, service, tmp_path):
        """Test adding message updates message_count in index."""
        conv = service.create_conversation()
        service.add_message(conv.id, "user", "Hello!")
        service.add_message(conv.id, "assistant", "Hi!")

        with open(tmp_path / "index.json") as f:
            data = json.load(f)

        assert data["conversations"][0]["message_count"] == 2

    def test_add_message_to_nonexistent_returns_none(self, service):
        """Test adding message to non-existent conversation returns None."""
        result = service.add_message("nonexistent-id", "user", "Hello!")

        assert result is None


# =============================================================================
# search_conversations Tests
# =============================================================================


class TestSearchConversations:
    """Tests for ConversationService.search_conversations()."""

    def test_search_by_title(self, service):
        """Test searching by conversation title."""
        service.create_conversation(title="Python Programming")
        service.create_conversation(title="JavaScript Basics")
        service.create_conversation(title="Python Advanced")

        results = service.search_conversations("Python")

        assert len(results) == 2
        titles = {r.title for r in results}
        assert "Python Programming" in titles
        assert "Python Advanced" in titles

    def test_search_by_message_content(self, service):
        """Test searching by message content."""
        conv1 = service.create_conversation(title="Chat 1")
        conv2 = service.create_conversation(title="Chat 2")
        service.add_message(conv1.id, "user", "Tell me about machine learning")
        service.add_message(conv2.id, "user", "What is the weather?")

        results = service.search_conversations("machine learning")

        assert len(results) == 1
        assert results[0].id == conv1.id

    def test_search_case_insensitive(self, service):
        """Test search is case-insensitive."""
        service.create_conversation(title="UPPERCASE Title")
        service.create_conversation(title="lowercase title")

        results = service.search_conversations("title")

        assert len(results) == 2

    def test_search_no_matches(self, service):
        """Test search with no matches returns empty list."""
        service.create_conversation(title="Hello")

        results = service.search_conversations("xyz123")

        assert results == []

    def test_search_empty_conversations(self, service):
        """Test search on empty service returns empty list."""
        results = service.search_conversations("anything")

        assert results == []

    def test_search_returns_sorted_results(self, service):
        """Test search results are sorted by updated_at descending."""
        conv1 = service.create_conversation(title="Python First")
        time.sleep(0.01)
        conv2 = service.create_conversation(title="Python Second")
        time.sleep(0.01)
        conv3 = service.create_conversation(title="Python Third")

        results = service.search_conversations("Python")

        # Most recently created/updated first
        assert len(results) == 3
        assert results[0].id == conv3.id
        assert results[1].id == conv2.id
        assert results[2].id == conv1.id

    def test_search_matches_title_before_checking_content(self, service):
        """Test title match doesn't cause duplicate results."""
        conv = service.create_conversation(title="Python Chat")
        service.add_message(conv.id, "user", "Tell me about Python")

        results = service.search_conversations("Python")

        # Should only appear once even though matches both title and content
        assert len(results) == 1
        assert results[0].id == conv.id

    def test_search_partial_match(self, service):
        """Test partial string matching."""
        service.create_conversation(title="Programming Tutorial")

        results = service.search_conversations("gram")

        assert len(results) == 1
        assert results[0].title == "Programming Tutorial"


# =============================================================================
# Integration/Edge Case Tests
# =============================================================================


class TestEdgeCases:
    """Tests for edge cases and error handling."""

    def test_corrupted_index_recovery(self, tmp_path):
        """Test service handles corrupted index.json."""
        # Create corrupted index
        index_path = tmp_path / "index.json"
        with open(index_path, "w") as f:
            f.write("not valid json{{{")

        service = ConversationService(data_dir=str(tmp_path))

        # Should recover with empty index
        result = service.list_conversations()
        assert result == []

    def test_corrupted_conversation_file(self, tmp_path):
        """Test service handles corrupted conversation file."""
        service = ConversationService(data_dir=str(tmp_path))
        conv = service.create_conversation()

        # Corrupt the conversation file
        conv_path = tmp_path / f"{conv.id}.json"
        with open(conv_path, "w") as f:
            f.write("not valid json")

        result = service.get_conversation(conv.id)
        assert result is None

    def test_special_characters_in_title(self, service):
        """Test conversation with special characters in title."""
        title = "Test: <>&\"'!@#$%^*()"
        conv = service.create_conversation(title=title)

        fetched = service.get_conversation(conv.id)

        assert fetched.title == title

    def test_unicode_content(self, service):
        """Test handling unicode content in messages."""
        conv = service.create_conversation(title="Unicode Test")
        content = "Hello! Emoji test: 🎉🚀 Chinese: 你好 Japanese: こんにちは"
        service.add_message(conv.id, "user", content)

        fetched = service.get_conversation(conv.id)

        assert fetched.messages[0].content == content

    def test_empty_message_content(self, service):
        """Test adding message with empty content."""
        conv = service.create_conversation()
        msg = service.add_message(conv.id, "user", "")

        assert msg is not None
        assert msg.content == ""

    def test_very_long_content(self, service):
        """Test handling very long message content."""
        conv = service.create_conversation()
        long_content = "x" * 100000  # 100K characters

        msg = service.add_message(conv.id, "user", long_content)

        fetched = service.get_conversation(conv.id)
        assert len(fetched.messages[0].content) == 100000

    def test_concurrent_operations(self, service):
        """Test multiple operations don't corrupt data."""
        # Create several conversations
        convs = [service.create_conversation(title=f"Conv {i}") for i in range(5)]

        # Add messages to each
        for conv in convs:
            service.add_message(conv.id, "user", f"Hello from {conv.id}")

        # Update some
        for conv in convs[:3]:
            service.update_conversation(conv.id, title=f"Updated {conv.id}")

        # Delete some
        service.delete_conversation(convs[4].id)

        # Verify state
        result = service.list_conversations()
        assert len(result) == 4

        # Verify all have messages
        for meta in result:
            conv = service.get_conversation(meta.id)
            assert len(conv.messages) == 1
