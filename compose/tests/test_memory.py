"""Tests for the global memory service."""

import json
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from compose.services.memory import (
    MemoryIndex,
    MemoryItem,
    MemoryService,
    get_memory_service,
)


class TestMemoryItem:
    """Tests for MemoryItem model."""

    def test_memory_item_creation(self):
        """Test creating a MemoryItem instance."""
        memory = MemoryItem(
            content="User prefers Python",
            category="preference",
        )
        assert memory.content == "User prefers Python"
        assert memory.category == "preference"
        assert memory.id is not None
        assert memory.created_at is not None
        assert memory.relevance_score == 1.0

    def test_memory_item_with_all_fields(self):
        """Test creating a memory with all fields."""
        memory = MemoryItem(
            id="test-id",
            content="Test content",
            category="fact",
            source_conversation_id="conv-123",
            relevance_score=0.8,
        )
        assert memory.id == "test-id"
        assert memory.source_conversation_id == "conv-123"
        assert memory.relevance_score == 0.8


class TestMemoryService:
    """Tests for MemoryService class."""

    @pytest.fixture
    def temp_memory_dir(self, tmp_path):
        """Create a temporary memory directory."""
        memory_dir = tmp_path / "memory"
        memory_dir.mkdir()
        return memory_dir

    @pytest.fixture
    def service(self, temp_memory_dir):
        """Create a memory service with temp directory."""
        return MemoryService(str(temp_memory_dir))

    def test_init_creates_index(self, temp_memory_dir):
        """Test that service creates index on init."""
        service = MemoryService(str(temp_memory_dir))
        assert (temp_memory_dir / "index.json").exists()

    def test_list_memories_empty(self, service):
        """Test listing memories when empty."""
        memories = service.list_memories()
        assert memories == []

    def test_add_memory(self, service):
        """Test adding a memory."""
        memory = service.add_memory(
            content="User likes Python",
            category="preference",
        )
        assert memory.content == "User likes Python"
        assert memory.category == "preference"
        assert memory.id is not None

        # Verify it's persisted
        memories = service.list_memories()
        assert len(memories) == 1
        assert memories[0].id == memory.id

    def test_add_memory_with_source(self, service):
        """Test adding a memory with source conversation."""
        memory = service.add_memory(
            content="Works at Acme Corp",
            category="fact",
            source_conversation_id="conv-123",
        )
        assert memory.source_conversation_id == "conv-123"

    def test_get_memory(self, service):
        """Test getting a memory by ID."""
        created = service.add_memory(content="Test memory")
        retrieved = service.get_memory(created.id)
        assert retrieved is not None
        assert retrieved.content == "Test memory"

    def test_get_memory_not_found(self, service):
        """Test getting non-existent memory returns None."""
        result = service.get_memory("nonexistent")
        assert result is None

    def test_update_memory(self, service):
        """Test updating a memory."""
        memory = service.add_memory(content="Original")
        updated = service.update_memory(memory.id, content="Updated")
        assert updated is not None
        assert updated.content == "Updated"
        assert updated.updated_at != memory.created_at

    def test_update_memory_partial(self, service):
        """Test partial update preserves other fields."""
        memory = service.add_memory(
            content="Original",
            category="preference",
            relevance_score=0.9,
        )
        updated = service.update_memory(memory.id, relevance_score=0.5)
        assert updated.content == "Original"  # Unchanged
        assert updated.category == "preference"  # Unchanged
        assert updated.relevance_score == 0.5  # Changed

    def test_update_memory_not_found(self, service):
        """Test updating non-existent memory returns None."""
        result = service.update_memory("nonexistent", content="New")
        assert result is None

    def test_delete_memory(self, service):
        """Test deleting a memory."""
        memory = service.add_memory(content="To delete")
        assert service.delete_memory(memory.id) is True
        assert service.get_memory(memory.id) is None

    def test_delete_memory_not_found(self, service):
        """Test deleting non-existent memory returns False."""
        assert service.delete_memory("nonexistent") is False

    def test_clear_all(self, service):
        """Test clearing all memories."""
        service.add_memory(content="Memory 1")
        service.add_memory(content="Memory 2")
        service.add_memory(content="Memory 3")

        count = service.clear_all()
        assert count == 3
        assert service.list_memories() == []

    def test_clear_all_empty(self, service):
        """Test clearing empty memory store."""
        count = service.clear_all()
        assert count == 0

    def test_list_memories_by_category(self, service):
        """Test filtering memories by category."""
        service.add_memory(content="Preference 1", category="preference")
        service.add_memory(content="Fact 1", category="fact")
        service.add_memory(content="Preference 2", category="preference")

        preferences = service.list_memories(category="preference")
        assert len(preferences) == 2
        assert all(m.category == "preference" for m in preferences)

    def test_list_memories_sorted_by_relevance(self, service):
        """Test memories are sorted by relevance score."""
        service.add_memory(content="Low relevance", relevance_score=0.3)
        service.add_memory(content="High relevance", relevance_score=0.9)
        service.add_memory(content="Medium relevance", relevance_score=0.6)

        memories = service.list_memories()
        assert memories[0].content == "High relevance"
        assert memories[1].content == "Medium relevance"
        assert memories[2].content == "Low relevance"

    def test_search_memories(self, service):
        """Test searching memories by content."""
        service.add_memory(content="User prefers Python for backend")
        service.add_memory(content="User works on AI projects")
        service.add_memory(content="Prefers TypeScript for frontend")

        results = service.search_memories("python")
        assert len(results) == 1
        assert "Python" in results[0].content

    def test_search_memories_case_insensitive(self, service):
        """Test search is case insensitive."""
        service.add_memory(content="User likes PYTHON")

        results = service.search_memories("python")
        assert len(results) == 1

    def test_search_memories_no_results(self, service):
        """Test search with no matches."""
        service.add_memory(content="User likes Python")

        results = service.search_memories("javascript")
        assert results == []

    def test_get_relevant_memories(self, service):
        """Test getting memories relevant to context."""
        service.add_memory(content="User prefers Python programming")
        service.add_memory(content="User works in machine learning")
        service.add_memory(content="User uses VS Code editor")

        relevant = service.get_relevant_memories("Write a Python function")
        # Should find Python-related memories
        assert any("Python" in m.content for m in relevant)

    def test_get_relevant_memories_with_limit(self, service):
        """Test relevant memories respects limit."""
        for i in range(10):
            service.add_memory(content=f"Memory about code example {i}")

        relevant = service.get_relevant_memories("code example", limit=3)
        assert len(relevant) <= 3

    def test_build_memory_context_empty(self, service):
        """Test building context with no memories."""
        context = service.build_memory_context("Hello")
        assert context == ""

    def test_build_memory_context_with_memories(self, service):
        """Test building context includes relevant memories."""
        service.add_memory(content="User prefers concise code")
        service.add_memory(content="User works with Python")

        context = service.build_memory_context("Write Python code")
        assert "Python" in context
        assert "remember about the user" in context


class TestMemoryExtraction:
    """Tests for memory auto-extraction."""

    @pytest.fixture
    def temp_memory_dir(self, tmp_path):
        """Create a temporary memory directory."""
        memory_dir = tmp_path / "memory"
        memory_dir.mkdir()
        return memory_dir

    @pytest.fixture
    def service(self, temp_memory_dir):
        """Create a memory service with temp directory."""
        return MemoryService(str(temp_memory_dir))

    @pytest.mark.asyncio
    async def test_extract_memories_no_api_key(self, service):
        """Test extraction returns empty list without API key."""
        with patch("compose.services.memory.OPENROUTER_API_KEY", ""):
            result = await service.extract_memories_from_conversation(
                "I prefer Python", "Great choice!"
            )
            assert result == []

    @pytest.mark.asyncio
    @patch("httpx.AsyncClient")
    async def test_extract_memories_success(self, mock_client_class, service):
        """Test successful memory extraction."""
        mock_response = MagicMock()
        mock_response.raise_for_status = MagicMock()
        mock_response.json.return_value = {
            "choices": [
                {
                    "message": {
                        "content": '[{"content": "User prefers Python", "category": "preference"}]'
                    }
                }
            ]
        }

        mock_client = AsyncMock()
        mock_client.post.return_value = mock_response
        mock_client.__aenter__.return_value = mock_client
        mock_client.__aexit__.return_value = None
        mock_client_class.return_value = mock_client

        with patch("compose.services.memory.OPENROUTER_API_KEY", "test-key"):
            result = await service.extract_memories_from_conversation(
                "I prefer Python", "Great choice!"
            )

        assert len(result) == 1
        assert result[0].content == "User prefers Python"
        assert result[0].category == "preference"

    @pytest.mark.asyncio
    @patch("httpx.AsyncClient")
    async def test_extract_memories_handles_error(self, mock_client_class, service):
        """Test extraction handles errors gracefully."""
        mock_client = AsyncMock()
        mock_client.post.side_effect = Exception("Network error")
        mock_client.__aenter__.return_value = mock_client
        mock_client.__aexit__.return_value = None
        mock_client_class.return_value = mock_client

        with patch("compose.services.memory.OPENROUTER_API_KEY", "test-key"):
            result = await service.extract_memories_from_conversation(
                "Test message", "Test response"
            )

        assert result == []

    @pytest.mark.asyncio
    @patch("httpx.AsyncClient")
    async def test_extract_memories_handles_empty_response(
        self, mock_client_class, service
    ):
        """Test extraction handles empty JSON array."""
        mock_response = MagicMock()
        mock_response.raise_for_status = MagicMock()
        mock_response.json.return_value = {
            "choices": [{"message": {"content": "[]"}}]
        }

        mock_client = AsyncMock()
        mock_client.post.return_value = mock_response
        mock_client.__aenter__.return_value = mock_client
        mock_client.__aexit__.return_value = None
        mock_client_class.return_value = mock_client

        with patch("compose.services.memory.OPENROUTER_API_KEY", "test-key"):
            result = await service.extract_memories_from_conversation(
                "Hello", "Hi there!"
            )

        assert result == []


class TestMemorySingleton:
    """Tests for singleton pattern."""

    def test_get_memory_service_returns_service(self):
        """Test get_memory_service returns MemoryService instance."""
        # Reset singleton
        import compose.services.memory as memory_module

        memory_module._service = None

        service = get_memory_service()
        assert isinstance(service, MemoryService)

    def test_get_memory_service_returns_same_instance(self):
        """Test get_memory_service returns same instance."""
        # Reset singleton
        import compose.services.memory as memory_module

        memory_module._service = None

        service1 = get_memory_service()
        service2 = get_memory_service()
        assert service1 is service2
