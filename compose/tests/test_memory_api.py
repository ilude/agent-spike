"""Tests for memory API router."""

import pytest
from unittest.mock import patch, MagicMock

from fastapi.testclient import TestClient

from compose.api.main import app


@pytest.fixture
def client():
    """Create test client."""
    return TestClient(app)


@pytest.fixture
def temp_memory_dir(tmp_path):
    """Create temp memory directory."""
    memory_dir = tmp_path / "memory"
    memory_dir.mkdir()
    return memory_dir


@pytest.fixture
def mock_memory_service(temp_memory_dir):
    """Mock the memory service."""
    from compose.services.memory import MemoryService

    service = MemoryService(str(temp_memory_dir))
    with patch("compose.api.routers.memory.get_memory_service", return_value=service):
        yield service


class TestMemoryListEndpoint:
    """Tests for GET /memory."""

    def test_list_memories_empty(self, client, mock_memory_service):
        """Test listing memories when empty."""
        response = client.get("/memory")
        assert response.status_code == 200
        data = response.json()
        assert data["memories"] == []
        assert data["count"] == 0

    def test_list_memories_with_data(self, client, mock_memory_service):
        """Test listing memories with data."""
        mock_memory_service.add_memory(content="Test memory 1")
        mock_memory_service.add_memory(content="Test memory 2")

        response = client.get("/memory")
        assert response.status_code == 200
        data = response.json()
        assert data["count"] == 2
        assert len(data["memories"]) == 2

    def test_list_memories_filter_category(self, client, mock_memory_service):
        """Test filtering by category."""
        mock_memory_service.add_memory(content="Preference", category="preference")
        mock_memory_service.add_memory(content="Fact", category="fact")

        response = client.get("/memory?category=preference")
        assert response.status_code == 200
        data = response.json()
        assert data["count"] == 1
        assert data["memories"][0]["category"] == "preference"


class TestMemoryAddEndpoint:
    """Tests for POST /memory."""

    def test_add_memory(self, client, mock_memory_service):
        """Test adding a memory."""
        response = client.post(
            "/memory",
            json={"content": "User likes Python", "category": "preference"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["content"] == "User likes Python"
        assert data["category"] == "preference"
        assert "id" in data

    def test_add_memory_minimal(self, client, mock_memory_service):
        """Test adding memory with minimal data."""
        response = client.post("/memory", json={"content": "Simple memory"})
        assert response.status_code == 200
        data = response.json()
        assert data["content"] == "Simple memory"
        assert data["category"] == "general"


class TestMemoryGetEndpoint:
    """Tests for GET /memory/{id}."""

    def test_get_memory(self, client, mock_memory_service):
        """Test getting a memory by ID."""
        memory = mock_memory_service.add_memory(content="Test memory")

        response = client.get(f"/memory/{memory.id}")
        assert response.status_code == 200
        data = response.json()
        assert data["content"] == "Test memory"

    def test_get_memory_not_found(self, client, mock_memory_service):
        """Test getting non-existent memory."""
        response = client.get("/memory/nonexistent-id")
        assert response.status_code == 404


class TestMemoryUpdateEndpoint:
    """Tests for PUT /memory/{id}."""

    def test_update_memory(self, client, mock_memory_service):
        """Test updating a memory."""
        memory = mock_memory_service.add_memory(content="Original")

        response = client.put(
            f"/memory/{memory.id}", json={"content": "Updated"}
        )
        assert response.status_code == 200
        data = response.json()
        assert data["content"] == "Updated"

    def test_update_memory_partial(self, client, mock_memory_service):
        """Test partial update."""
        memory = mock_memory_service.add_memory(
            content="Original", category="fact", relevance_score=1.0
        )

        response = client.put(
            f"/memory/{memory.id}", json={"relevance_score": 0.5}
        )
        assert response.status_code == 200
        data = response.json()
        assert data["content"] == "Original"  # Unchanged
        assert data["relevance_score"] == 0.5  # Changed

    def test_update_memory_not_found(self, client, mock_memory_service):
        """Test updating non-existent memory."""
        response = client.put("/memory/nonexistent", json={"content": "New"})
        assert response.status_code == 404


class TestMemoryDeleteEndpoint:
    """Tests for DELETE /memory/{id}."""

    def test_delete_memory(self, client, mock_memory_service):
        """Test deleting a memory."""
        memory = mock_memory_service.add_memory(content="To delete")

        response = client.delete(f"/memory/{memory.id}")
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True

        # Verify deleted
        assert mock_memory_service.get_memory(memory.id) is None

    def test_delete_memory_not_found(self, client, mock_memory_service):
        """Test deleting non-existent memory."""
        response = client.delete("/memory/nonexistent")
        assert response.status_code == 404


class TestMemoryClearEndpoint:
    """Tests for DELETE /memory (clear all)."""

    def test_clear_all_memories(self, client, mock_memory_service):
        """Test clearing all memories."""
        mock_memory_service.add_memory(content="Memory 1")
        mock_memory_service.add_memory(content="Memory 2")
        mock_memory_service.add_memory(content="Memory 3")

        response = client.delete("/memory")
        assert response.status_code == 200
        data = response.json()
        assert data["deleted_count"] == 3

        # Verify cleared
        assert mock_memory_service.list_memories() == []

    def test_clear_empty(self, client, mock_memory_service):
        """Test clearing when already empty."""
        response = client.delete("/memory")
        assert response.status_code == 200
        data = response.json()
        assert data["deleted_count"] == 0


class TestMemorySearchEndpoint:
    """Tests for GET /memory/search."""

    def test_search_memories(self, client, mock_memory_service):
        """Test searching memories."""
        mock_memory_service.add_memory(content="User likes Python programming")
        mock_memory_service.add_memory(content="Works on AI projects")

        response = client.get("/memory/search?q=python")
        assert response.status_code == 200
        data = response.json()
        assert data["count"] == 1
        assert "Python" in data["memories"][0]["content"]

    def test_search_no_results(self, client, mock_memory_service):
        """Test search with no matches."""
        mock_memory_service.add_memory(content="User likes Python")

        response = client.get("/memory/search?q=javascript")
        assert response.status_code == 200
        data = response.json()
        assert data["count"] == 0
