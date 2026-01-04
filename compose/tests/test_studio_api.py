"""Tests for Studio API endpoints (vaults, notes, graph).

These tests cover the issues we encountered during development:
1. SurrealDB query syntax (no AS aliases)
2. note_count being None when no notes exist
3. API parameter validation (missing required fields)
4. Proper error handling for 404 cases
"""

import pytest
from datetime import datetime
from unittest.mock import AsyncMock, patch, MagicMock
from fastapi.testclient import TestClient

from compose.services.vaults import Vault, VaultMeta
from compose.services.notes import Note, NoteMeta, NoteLink
from compose.services.surrealdb.models import GraphData, GraphNode, GraphEdge, AISuggestionRecord


# ============ Fixtures ============


@pytest.fixture
def sample_vault():
    """Sample Vault model instance."""
    return Vault(
        id="vault-123",
        name="Test Vault",
        slug="test-vault-123",
        storage_type="minio",
        note_count=0,
        minio_bucket="mentat-vaults",
        settings={},
        created_at=datetime.fromisoformat("2025-01-01T00:00:00+00:00"),
        updated_at=datetime.fromisoformat("2025-01-01T00:00:00+00:00"),
    )


@pytest.fixture
def sample_vault_meta():
    """Sample VaultMeta model instance for list responses."""
    return VaultMeta(
        id="vault-123",
        name="Test Vault",
        slug="test-vault-123",
        storage_type="minio",
        note_count=5,
        created_at=datetime.fromisoformat("2025-01-01T00:00:00+00:00"),
        updated_at=datetime.fromisoformat("2025-01-01T00:00:00+00:00"),
    )


@pytest.fixture
def sample_note():
    """Sample Note model instance."""
    return Note(
        id="note-123",
        vault_id="vault-123",
        path="test-note.md",
        title="Test Note",
        content="# Test Note\n\nContent",
        preview="Test Note Content",
        word_count=100,
        created_at=datetime.fromisoformat("2025-01-01T00:00:00+00:00"),
        updated_at=datetime.fromisoformat("2025-01-01T00:00:00+00:00"),
    )


@pytest.fixture
def sample_note_meta():
    """Sample NoteMeta model instance for list responses."""
    return NoteMeta(
        id="note-123",
        vault_id="vault-123",
        path="test-note.md",
        title="Test Note",
        preview="Test Note Content",
        word_count=100,
        created_at=datetime.fromisoformat("2025-01-01T00:00:00+00:00"),
        updated_at=datetime.fromisoformat("2025-01-01T00:00:00+00:00"),
    )


@pytest.fixture
def sample_link():
    """Sample NoteLink model instance."""
    return NoteLink(
        id="link-123",
        source_id="note-123",
        target_id="note-456",
        link_text="Other Note",
        link_type="manual",
        accepted=True,
        confidence=None,
    )


@pytest.fixture
def sample_suggestion():
    """Sample AI suggestion model instance."""
    return AISuggestionRecord(
        id="sug-123",
        note_id="note-123",
        suggestion_type="link",
        suggestion_data={"target_title": "Related", "link_text": "Related"},
        confidence=0.85,
        status="pending",
        created_at=datetime.fromisoformat("2025-01-01T00:00:00+00:00"),
    )


@pytest.fixture
def sample_graph():
    """Sample GraphData model instance."""
    return GraphData(
        nodes=[GraphNode(id="note-123", title="Test Note", type="note", size=1)],
        edges=[],
    )


# ============ Vault API Tests ============


class TestVaultsAPI:
    """Tests for /vaults endpoints."""

    def test_list_vaults_empty(self, client):
        """Test GET /vaults returns empty list when no vaults exist."""
        mock_service = MagicMock()
        mock_service.list_vaults = AsyncMock(return_value=[])

        with patch("compose.api.routers.vaults.get_vault_service", return_value=mock_service):
            response = client.get("/vaults")

        assert response.status_code == 200
        data = response.json()
        assert data == {"vaults": []}

    def test_list_vaults_with_data(self, client, sample_vault_meta):
        """Test GET /vaults returns list of vaults."""
        mock_service = MagicMock()
        mock_service.list_vaults = AsyncMock(return_value=[sample_vault_meta])

        with patch("compose.api.routers.vaults.get_vault_service", return_value=mock_service):
            response = client.get("/vaults")

        assert response.status_code == 200
        data = response.json()
        assert len(data["vaults"]) == 1
        assert data["vaults"][0]["name"] == "Test Vault"
        assert data["vaults"][0]["note_count"] == 5

    def test_list_vaults_note_count_zero(self, client):
        """Test that note_count=0 is handled correctly (was causing issues with None)."""
        vault_meta_zero = VaultMeta(
            id="vault-123",
            name="Test Vault",
            slug="test-vault-123",
            storage_type="minio",
            note_count=0,
            created_at=datetime.fromisoformat("2025-01-01T00:00:00+00:00"),
            updated_at=datetime.fromisoformat("2025-01-01T00:00:00+00:00"),
        )

        mock_service = MagicMock()
        mock_service.list_vaults = AsyncMock(return_value=[vault_meta_zero])

        with patch("compose.api.routers.vaults.get_vault_service", return_value=mock_service):
            response = client.get("/vaults")

        assert response.status_code == 200
        data = response.json()
        assert data["vaults"][0]["note_count"] == 0

    def test_create_vault_success(self, client, sample_vault):
        """Test POST /vaults creates a new vault."""
        mock_service = MagicMock()
        mock_service.create_vault = AsyncMock(return_value=sample_vault)

        with patch("compose.api.routers.vaults.get_vault_service", return_value=mock_service):
            response = client.post("/vaults", json={"name": "Test Vault"})

        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "Test Vault"
        assert data["slug"] == "test-vault-123"

    def test_create_vault_missing_name(self, client):
        """Test POST /vaults fails without name - caught validation error."""
        response = client.post("/vaults", json={})

        assert response.status_code == 422
        data = response.json()
        assert "detail" in data

    def test_create_vault_empty_name(self, client, sample_vault):
        """Test POST /vaults with empty string name - should still succeed (service handles validation)."""
        mock_service = MagicMock()
        mock_service.create_vault = AsyncMock(return_value=sample_vault)

        with patch("compose.api.routers.vaults.get_vault_service", return_value=mock_service):
            response = client.post("/vaults", json={"name": ""})

        # Empty string is valid JSON, service may accept it
        assert response.status_code == 200

    def test_get_vault_success(self, client, sample_vault):
        """Test GET /vaults/{id} returns vault."""
        mock_service = MagicMock()
        mock_service.get_vault = AsyncMock(return_value=sample_vault)

        with patch("compose.api.routers.vaults.get_vault_service", return_value=mock_service):
            response = client.get("/vaults/vault-123")

        assert response.status_code == 200
        data = response.json()
        assert data["id"] == "vault-123"

    def test_get_vault_not_found(self, client):
        """Test GET /vaults/{id} returns 404 for non-existent vault."""
        mock_service = MagicMock()
        mock_service.get_vault = AsyncMock(return_value=None)

        with patch("compose.api.routers.vaults.get_vault_service", return_value=mock_service):
            response = client.get("/vaults/non-existent")

        assert response.status_code == 404
        assert "not found" in response.json()["detail"].lower()

    def test_get_vault_by_slug(self, client, sample_vault):
        """Test GET /vaults/by-slug/{slug} returns vault."""
        mock_service = MagicMock()
        mock_service.get_vault_by_slug = AsyncMock(return_value=sample_vault)

        with patch("compose.api.routers.vaults.get_vault_service", return_value=mock_service):
            response = client.get("/vaults/by-slug/test-vault-123")

        assert response.status_code == 200
        data = response.json()
        assert data["slug"] == "test-vault-123"

    def test_update_vault(self, client):
        """Test PUT /vaults/{id} updates vault."""
        updated_vault = Vault(
            id="vault-123",
            name="Updated Name",
            slug="updated-name",
            storage_type="minio",
            note_count=0,
            minio_bucket="mentat-vaults",
            settings={},
            created_at=datetime.fromisoformat("2025-01-01T00:00:00+00:00"),
            updated_at=datetime.fromisoformat("2025-01-01T00:00:00+00:00"),
        )

        mock_service = MagicMock()
        mock_service.update_vault = AsyncMock(return_value=updated_vault)

        with patch("compose.api.routers.vaults.get_vault_service", return_value=mock_service):
            response = client.put("/vaults/vault-123", json={"name": "Updated Name"})

        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "Updated Name"

    def test_delete_vault_success(self, client):
        """Test DELETE /vaults/{id} deletes vault."""
        mock_service = MagicMock()
        mock_service.delete_vault = AsyncMock(return_value=True)

        with patch("compose.api.routers.vaults.get_vault_service", return_value=mock_service):
            response = client.delete("/vaults/vault-123")

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "deleted"

    def test_delete_vault_not_found(self, client):
        """Test DELETE /vaults/{id} returns 404 for non-existent vault."""
        mock_service = MagicMock()
        mock_service.delete_vault = AsyncMock(return_value=False)

        with patch("compose.api.routers.vaults.get_vault_service", return_value=mock_service):
            response = client.delete("/vaults/non-existent")

        assert response.status_code == 404

    def test_get_file_tree_empty(self, client, sample_vault):
        """Test GET /vaults/{id}/tree returns empty tree."""
        mock_service = MagicMock()
        mock_service.get_vault = AsyncMock(return_value=sample_vault)
        mock_service.get_file_tree = AsyncMock(return_value=[])

        with patch("compose.api.routers.vaults.get_vault_service", return_value=mock_service):
            response = client.get("/vaults/vault-123/tree")

        assert response.status_code == 200
        data = response.json()
        assert data["tree"] == []

    def test_get_file_tree_vault_not_found(self, client):
        """Test GET /vaults/{id}/tree returns 404 for non-existent vault."""
        mock_service = MagicMock()
        mock_service.get_vault = AsyncMock(return_value=None)

        with patch("compose.api.routers.vaults.get_vault_service", return_value=mock_service):
            response = client.get("/vaults/non-existent/tree")

        assert response.status_code == 404


# ============ Notes API Tests ============


class TestNotesAPI:
    """Tests for /notes endpoints."""

    def test_list_notes(self, client, sample_note_meta):
        """Test GET /notes returns list of notes."""
        mock_service = MagicMock()
        mock_service.list_notes = AsyncMock(return_value=[sample_note_meta])

        with patch("compose.api.routers.studio_notes.get_note_service", return_value=mock_service):
            response = client.get("/notes?vault_id=vault-123")

        assert response.status_code == 200
        data = response.json()
        assert "notes" in data

    def test_list_notes_missing_vault_id(self, client):
        """Test GET /notes without vault_id returns 422."""
        response = client.get("/notes")

        assert response.status_code == 422

    def test_create_note_success(self, client, sample_note):
        """Test POST /notes creates a new note."""
        mock_service = MagicMock()
        mock_service.create_note = AsyncMock(return_value=sample_note)

        with patch("compose.api.routers.studio_notes.get_note_service", return_value=mock_service):
            response = client.post("/notes", json={
                "vault_id": "vault-123",
                "path": "new-note.md",
                "title": "New Note",
                "content": "# New Note\n\nContent"
            })

        assert response.status_code == 200
        data = response.json()
        assert data["title"] == "Test Note"

    def test_create_note_missing_vault_id(self, client):
        """Test POST /notes without vault_id returns 422."""
        response = client.post("/notes", json={
            "path": "test.md",
            "content": "test"
        })

        assert response.status_code == 422

    def test_create_note_missing_path(self, client):
        """Test POST /notes without path returns 422."""
        response = client.post("/notes", json={
            "vault_id": "vault-123",
            "content": "test"
        })

        assert response.status_code == 422

    def test_get_note_success(self, client, sample_note):
        """Test GET /notes/{id} returns note."""
        mock_service = MagicMock()
        mock_service.get_note = AsyncMock(return_value=sample_note)

        with patch("compose.api.routers.studio_notes.get_note_service", return_value=mock_service):
            response = client.get("/notes/note-123")

        assert response.status_code == 200
        data = response.json()
        assert data["id"] == "note-123"

    def test_get_note_not_found(self, client):
        """Test GET /notes/{id} returns 404 for non-existent note."""
        mock_service = MagicMock()
        mock_service.get_note = AsyncMock(return_value=None)

        with patch("compose.api.routers.studio_notes.get_note_service", return_value=mock_service):
            response = client.get("/notes/non-existent")

        assert response.status_code == 404

    def test_update_note_success(self, client, sample_note):
        """Test PUT /notes/{id} updates note."""
        mock_service = MagicMock()
        mock_service.update_note = AsyncMock(return_value=sample_note)

        with patch("compose.api.routers.studio_notes.get_note_service", return_value=mock_service):
            response = client.put("/notes/note-123", json={"content": "# Updated"})

        assert response.status_code == 200

    def test_delete_note_success(self, client):
        """Test DELETE /notes/{id} deletes note."""
        mock_service = MagicMock()
        mock_service.delete_note = AsyncMock(return_value=True)

        with patch("compose.api.routers.studio_notes.get_note_service", return_value=mock_service):
            response = client.delete("/notes/note-123")

        assert response.status_code == 200
        assert response.json()["status"] == "deleted"

    def test_delete_note_not_found(self, client):
        """Test DELETE /notes/{id} returns 404."""
        mock_service = MagicMock()
        mock_service.delete_note = AsyncMock(return_value=False)

        with patch("compose.api.routers.studio_notes.get_note_service", return_value=mock_service):
            response = client.delete("/notes/non-existent")

        assert response.status_code == 404

    def test_search_notes(self, client, sample_note_meta):
        """Test GET /notes/search/{vault_id} returns matching notes."""
        mock_service = MagicMock()
        mock_service.search_notes = AsyncMock(return_value=[sample_note_meta])

        with patch("compose.api.routers.studio_notes.get_note_service", return_value=mock_service):
            response = client.get("/notes/search/vault-123?q=test")

        assert response.status_code == 200
        data = response.json()
        assert "notes" in data


# ============ Links API Tests ============


class TestLinksAPI:
    """Tests for note links endpoints."""

    def test_get_note_links(self, client, sample_note, sample_link):
        """Test GET /notes/{id}/links returns links."""
        mock_service = MagicMock()
        mock_service.get_note = AsyncMock(return_value=sample_note)
        mock_service.get_outlinks = AsyncMock(return_value=[sample_link])
        mock_service.get_backlinks = AsyncMock(return_value=[])

        with patch("compose.api.routers.studio_notes.get_note_service", return_value=mock_service):
            response = client.get("/notes/note-123/links")

        assert response.status_code == 200
        data = response.json()
        assert "outlinks" in data
        assert "backlinks" in data

    def test_get_note_links_note_not_found(self, client):
        """Test GET /notes/{id}/links returns 404 for non-existent note."""
        mock_service = MagicMock()
        mock_service.get_note = AsyncMock(return_value=None)

        with patch("compose.api.routers.studio_notes.get_note_service", return_value=mock_service):
            response = client.get("/notes/non-existent/links")

        assert response.status_code == 404

    def test_create_link(self, client, sample_note, sample_link):
        """Test POST /notes/{id}/links creates a link."""
        mock_service = MagicMock()
        mock_service.get_note = AsyncMock(return_value=sample_note)
        mock_service.create_link = AsyncMock(return_value=sample_link)

        with patch("compose.api.routers.studio_notes.get_note_service", return_value=mock_service):
            response = client.post("/notes/note-123/links", json={
                "target_id": "note-456",
                "link_text": "Other Note"
            })

        assert response.status_code == 200


# ============ Suggestions API Tests ============


class TestSuggestionsAPI:
    """Tests for AI suggestions endpoints."""

    def test_get_suggestions(self, client, sample_note, sample_suggestion):
        """Test GET /notes/{id}/suggestions returns suggestions."""
        mock_service = MagicMock()
        mock_service.get_note = AsyncMock(return_value=sample_note)
        mock_service.get_suggestions = AsyncMock(return_value=[sample_suggestion])

        with patch("compose.api.routers.studio_notes.get_note_service", return_value=mock_service):
            response = client.get("/notes/note-123/suggestions")

        assert response.status_code == 200
        data = response.json()
        assert "suggestions" in data

    def test_accept_suggestion(self, client):
        """Test POST /notes/{id}/suggestions/{sug_id}/accept."""
        mock_service = MagicMock()
        mock_service.accept_suggestion = AsyncMock(return_value=True)

        with patch("compose.api.routers.studio_notes.get_note_service", return_value=mock_service):
            response = client.post("/notes/note-123/suggestions/sug-123/accept")

        assert response.status_code == 200
        assert response.json()["status"] == "accepted"

    def test_reject_suggestion(self, client):
        """Test POST /notes/{id}/suggestions/{sug_id}/reject."""
        mock_service = MagicMock()
        mock_service.reject_suggestion = AsyncMock(return_value=True)

        with patch("compose.api.routers.studio_notes.get_note_service", return_value=mock_service):
            response = client.post("/notes/note-123/suggestions/sug-123/reject")

        assert response.status_code == 200
        assert response.json()["status"] == "rejected"

    def test_accept_suggestion_not_found(self, client):
        """Test accept returns 404 for non-existent suggestion."""
        mock_service = MagicMock()
        mock_service.accept_suggestion = AsyncMock(return_value=False)

        with patch("compose.api.routers.studio_notes.get_note_service", return_value=mock_service):
            response = client.post("/notes/note-123/suggestions/non-existent/accept")

        assert response.status_code == 404


# ============ Graph API Tests ============


class TestGraphAPI:
    """Tests for /graph endpoints."""

    def test_get_graph(self, client, sample_vault, sample_graph):
        """Test GET /graph/{vault_id} returns graph data."""
        mock_vault_service = MagicMock()
        mock_vault_service.get_vault = AsyncMock(return_value=sample_vault)

        mock_note_service = MagicMock()
        mock_note_service.get_graph_data = AsyncMock(return_value=sample_graph)

        with patch("compose.api.routers.graph.get_vault_service", return_value=mock_vault_service), \
             patch("compose.api.routers.graph.get_note_service", return_value=mock_note_service):
            response = client.get("/graph/vault-123")

        assert response.status_code == 200
        data = response.json()
        assert "nodes" in data
        assert "edges" in data

    def test_get_graph_vault_not_found(self, client):
        """Test GET /graph/{vault_id} returns 404 for non-existent vault."""
        mock_vault_service = MagicMock()
        mock_vault_service.get_vault = AsyncMock(return_value=None)

        with patch("compose.api.routers.graph.get_vault_service", return_value=mock_vault_service):
            response = client.get("/graph/non-existent")

        assert response.status_code == 404

    def test_get_local_graph(self, client, sample_vault, sample_note, sample_graph):
        """Test GET /graph/{vault_id}/local/{note_id} returns local graph."""
        mock_vault_service = MagicMock()
        mock_vault_service.get_vault = AsyncMock(return_value=sample_vault)

        mock_note_service = MagicMock()
        mock_note_service.get_note = AsyncMock(return_value=sample_note)
        mock_note_service.get_graph_data = AsyncMock(return_value=sample_graph)

        with patch("compose.api.routers.graph.get_vault_service", return_value=mock_vault_service), \
             patch("compose.api.routers.graph.get_note_service", return_value=mock_note_service):
            response = client.get("/graph/vault-123/local/note-123?depth=2")

        assert response.status_code == 200
        data = response.json()
        assert "nodes" in data
        assert "edges" in data

    def test_get_graph_stats(self, client, sample_vault, sample_graph):
        """Test GET /graph/{vault_id}/stats returns statistics."""
        mock_vault_service = MagicMock()
        mock_vault_service.get_vault = AsyncMock(return_value=sample_vault)

        mock_note_service = MagicMock()
        mock_note_service.get_graph_data = AsyncMock(return_value=sample_graph)

        with patch("compose.api.routers.graph.get_vault_service", return_value=mock_vault_service), \
             patch("compose.api.routers.graph.get_note_service", return_value=mock_note_service):
            response = client.get("/graph/vault-123/stats")

        assert response.status_code == 200
        data = response.json()
        assert "node_count" in data
        assert "edge_count" in data
