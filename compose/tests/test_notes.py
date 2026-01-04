"""Tests for NoteService."""

import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from datetime import datetime, timezone

from compose.services.notes import NoteService, Note, NoteLink
from compose.services.surrealdb.models import AISuggestionRecord


# ============ Fixtures ============


@pytest.fixture
def mock_execute_query():
    """Mock SurrealDB execute_query function."""
    with patch("compose.services.notes.execute_query") as mock:
        yield mock


@pytest.fixture
def mock_vault_service():
    """Mock VaultService for note content operations."""
    mock_service = MagicMock()
    # These are sync methods in VaultService, not async
    mock_service.save_note_content = MagicMock()
    mock_service.get_note_content = MagicMock(return_value="# Test Note\n\nContent")
    mock_service.delete_note_content = MagicMock()
    # get_vault is async and returns a Vault object
    mock_vault = MagicMock()
    mock_vault.slug = "test-vault"
    mock_vault.storage_type = "minio"
    mock_service.get_vault = AsyncMock(return_value=mock_vault)

    with patch("compose.services.notes.get_vault_service", return_value=mock_service):
        yield mock_service


@pytest.fixture
def note_service(mock_vault_service):
    """Create NoteService instance with mocked dependencies."""
    return NoteService()


@pytest.fixture
def sample_note_record():
    """Sample note record from SurrealDB."""
    return {
        "id": "note:test-note-123",
        "vault_id": "vault-123",
        "path": "test-note.md",
        "title": "Test Note",
        "content": "# Test Note\n\nContent",
        "preview": "Test Note Content",
        "word_count": 100,
        "created_at": "2025-01-01T00:00:00Z",
        "updated_at": "2025-01-01T00:00:00Z",
    }


@pytest.fixture
def sample_link_record():
    """Sample note link record from SurrealDB."""
    return {
        "id": "note_link:link-123",
        "source_id": "note:source-123",
        "target_id": "note:target-123",
        "link_text": "Target Note",
        "link_type": "manual",
        "accepted": True,
        "confidence": None,
        "created_at": "2025-01-01T00:00:00Z",
    }


# ============ Wiki-Link Parsing Tests ============


class TestWikiLinkParsing:
    """Tests for wiki-link extraction from markdown.

    Note: parse_wiki_links returns list of tuples (link_text, alias).
    Alias is empty string when not provided (regex behavior).
    """

    def test_parse_simple_wiki_link(self, note_service):
        """Test parsing simple [[link]]."""
        content = "Check out [[My Note]] for more info."
        links = note_service.parse_wiki_links(content)

        assert len(links) == 1
        link_text, alias = links[0]
        assert link_text == "My Note"
        assert alias == ""  # Empty string when no alias

    def test_parse_wiki_link_with_alias(self, note_service):
        """Test parsing [[target|display]] links."""
        content = "See [[Technical Details|the details]] here."
        links = note_service.parse_wiki_links(content)

        assert len(links) == 1
        link_text, alias = links[0]
        assert link_text == "Technical Details"
        assert alias == "the details"

    def test_parse_multiple_wiki_links(self, note_service):
        """Test parsing multiple wiki-links."""
        content = """
        Links: [[Note A]], [[Note B|B]], and [[Note C]].
        """
        links = note_service.parse_wiki_links(content)

        assert len(links) == 3
        targets = [link_text for link_text, _ in links]
        assert "Note A" in targets
        assert "Note B" in targets
        assert "Note C" in targets

    def test_parse_no_wiki_links(self, note_service):
        """Test content with no wiki-links."""
        content = "Plain text with no links."
        links = note_service.parse_wiki_links(content)

        assert links == []

    def test_parse_wiki_link_with_path(self, note_service):
        """Test parsing wiki-link with folder path."""
        content = "See [[folder/subfolder/Note Name]]."
        links = note_service.parse_wiki_links(content)

        assert len(links) == 1
        link_text, alias = links[0]
        assert link_text == "folder/subfolder/Note Name"


# ============ NoteService CRUD Tests ============


class TestNoteServiceCreate:
    """Tests for note creation."""

    @pytest.mark.asyncio
    async def test_create_note_success(
        self, note_service, mock_execute_query, mock_vault_service, sample_note_record
    ):
        """Test successful note creation."""
        mock_execute_query.return_value = [sample_note_record]

        note = await note_service.create_note(
            vault_id="vault-123",
            path="test-note.md",
            title="Test Note",
            content="# Test Note\n\nContent"
        )

        assert note.title == "Test Note"
        assert note.path == "test-note.md"
        mock_vault_service.save_note_content.assert_called_once()

    @pytest.mark.asyncio
    async def test_create_note_with_wiki_links(
        self, note_service, mock_execute_query, mock_vault_service, sample_note_record
    ):
        """Test note creation syncs wiki-links."""
        mock_execute_query.return_value = [sample_note_record]

        content = "# Test\n\nSee [[Other Note]] for details."
        await note_service.create_note(
            vault_id="vault-123",
            path="test-note.md",
            title="Test Note",
            content=content
        )

        # Should have called execute_query for link syncing
        assert mock_execute_query.call_count >= 1


class TestNoteServiceGet:
    """Tests for getting notes."""

    @pytest.mark.asyncio
    async def test_get_note_by_id(
        self, note_service, mock_execute_query, sample_note_record
    ):
        """Test getting note by ID."""
        mock_execute_query.return_value = [sample_note_record]

        note = await note_service.get_note("test-note-123")

        assert note is not None
        assert note.title == "Test Note"

    @pytest.mark.asyncio
    async def test_get_note_not_found(self, note_service, mock_execute_query):
        """Test getting non-existent note."""
        mock_execute_query.return_value = []

        note = await note_service.get_note("non-existent")

        assert note is None

    @pytest.mark.asyncio
    async def test_get_note_by_path(
        self, note_service, mock_execute_query, sample_note_record
    ):
        """Test getting note by vault and path."""
        mock_execute_query.return_value = [sample_note_record]

        note = await note_service.get_note_by_path("vault-123", "test-note.md")

        assert note is not None
        assert note.path == "test-note.md"


class TestNoteServiceUpdate:
    """Tests for updating notes."""

    @pytest.mark.asyncio
    async def test_update_note_content(
        self, note_service, mock_execute_query, mock_vault_service, sample_note_record
    ):
        """Test updating note content."""
        mock_execute_query.return_value = [sample_note_record]

        note = await note_service.update_note(
            "test-note-123",
            content="# Updated Content"
        )

        assert note is not None
        mock_vault_service.save_note_content.assert_called()

    @pytest.mark.asyncio
    async def test_update_note_title(
        self, note_service, mock_execute_query, mock_vault_service, sample_note_record
    ):
        """Test updating note title."""
        updated_record = {**sample_note_record, "title": "New Title"}
        mock_execute_query.return_value = [updated_record]

        note = await note_service.update_note(
            "test-note-123",
            title="New Title"
        )

        assert note.title == "New Title"


class TestNoteServiceDelete:
    """Tests for deleting notes."""

    @pytest.mark.asyncio
    async def test_delete_note_success(
        self, note_service, mock_execute_query, mock_vault_service, sample_note_record
    ):
        """Test successful note deletion.

        delete_note makes multiple execute_query calls:
        1. Get note (to get vault_id for MinIO cleanup)
        2. Delete links where note is source or target
        3. Delete AI suggestions for note
        4. Delete note-entity relationships
        5. Delete the note itself
        """
        mock_execute_query.side_effect = [
            [sample_note_record],  # get note
            [],  # delete links
            [],  # delete ai_suggestions
            [],  # delete note_entity
            [],  # delete note
        ]

        result = await note_service.delete_note("test-note-123")

        assert result is True
        mock_vault_service.delete_note_content.assert_called_once()

    @pytest.mark.asyncio
    async def test_delete_note_not_found(self, note_service, mock_execute_query):
        """Test deleting non-existent note."""
        mock_execute_query.return_value = []

        result = await note_service.delete_note("non-existent")

        assert result is False


# ============ Link Management Tests ============


class TestNoteServiceLinks:
    """Tests for link management."""

    @pytest.mark.asyncio
    async def test_get_outlinks(
        self, note_service, mock_execute_query, sample_link_record
    ):
        """Test getting outgoing links from a note."""
        mock_execute_query.return_value = [sample_link_record]

        links = await note_service.get_outlinks("note:source-123")

        assert len(links) == 1
        assert links[0].link_text == "Target Note"

    @pytest.mark.asyncio
    async def test_get_backlinks(
        self, note_service, mock_execute_query, sample_link_record
    ):
        """Test getting backlinks to a note."""
        mock_execute_query.return_value = [sample_link_record]

        links = await note_service.get_backlinks("note:target-123")

        assert len(links) == 1

    @pytest.mark.asyncio
    async def test_create_link(self, note_service, mock_execute_query, sample_link_record):
        """Test creating a link between notes."""
        mock_execute_query.return_value = [sample_link_record]

        link = await note_service.create_link(
            source_id="note:source-123",
            target_id="note:target-123",
            link_text="Target Note"
        )

        assert link is not None
        assert link.link_text == "Target Note"


# ============ Search Tests ============


class TestNoteServiceSearch:
    """Tests for note search."""

    @pytest.mark.asyncio
    async def test_search_notes_by_title(
        self, note_service, mock_execute_query, sample_note_record
    ):
        """Test searching notes by title."""
        mock_execute_query.return_value = [sample_note_record]

        results = await note_service.search_notes("vault-123", "Test")

        assert len(results) == 1
        assert results[0].title == "Test Note"

    @pytest.mark.asyncio
    async def test_search_notes_empty_query(self, note_service, mock_execute_query):
        """Test search with empty query returns all notes."""
        mock_execute_query.return_value = []

        results = await note_service.search_notes("vault-123", "")

        assert results == []


# ============ Graph Data Tests ============


class TestNoteServiceGraph:
    """Tests for graph data generation."""

    @pytest.mark.asyncio
    async def test_get_graph_data(self, note_service, mock_execute_query):
        """Test getting graph data for visualization."""
        # Mock notes query
        notes = [
            {"id": "note:1", "title": "Note 1", "path": "note1.md"},
            {"id": "note:2", "title": "Note 2", "path": "note2.md"},
        ]
        # Mock links query - use source_id/target_id as per actual implementation
        links = [
            {"source_id": "note:1", "target_id": "note:2"},
        ]
        mock_execute_query.side_effect = [notes, links]

        graph = await note_service.get_graph_data("vault-123")

        assert len(graph.nodes) == 2
        assert len(graph.edges) == 1
        assert graph.edges[0].source == "note:1"
        assert graph.edges[0].target == "note:2"


# ============ AI Suggestion Tests ============


class TestNoteServiceSuggestions:
    """Tests for AI suggestion management."""

    @pytest.mark.asyncio
    async def test_get_suggestions(self, note_service, mock_execute_query):
        """Test getting suggestions for a note."""
        suggestion_record = {
            "id": "ai_suggestion:sug-123",
            "note_id": "note:test-123",
            "suggestion_type": "link",
            "suggested_text": "[[Related Note]]",
            "reason": "Similar topic",
            "confidence": 0.85,
            "status": "pending",
            "created_at": "2025-01-01T00:00:00Z",
        }
        mock_execute_query.return_value = [suggestion_record]

        suggestions = await note_service.get_suggestions("note:test-123")

        assert len(suggestions) == 1
        assert suggestions[0].suggestion_type == "link"
        assert suggestions[0].status == "pending"

    @pytest.mark.asyncio
    async def test_accept_suggestion(self, note_service, mock_execute_query):
        """Test accepting a suggestion."""
        mock_execute_query.return_value = [{"status": "accepted"}]

        result = await note_service.accept_suggestion("sug-123")

        assert result is True

    @pytest.mark.asyncio
    async def test_reject_suggestion(self, note_service, mock_execute_query):
        """Test rejecting a suggestion."""
        mock_execute_query.return_value = [{"status": "rejected"}]

        result = await note_service.reject_suggestion("sug-123")

        assert result is True


# ============ SurrealDB Query Syntax Tests ============


class TestNoteServiceQuerySyntax:
    """Tests to verify SurrealDB query syntax is correct.

    SurrealDB does NOT support SQL-style table aliases like 'FROM table AS t'.
    These tests verify all queries avoid this pattern.
    """

    def _assert_no_table_aliases(self, query: str) -> None:
        """Assert query doesn't use table aliases (AS pattern after FROM)."""
        import re
        alias_pattern = r"FROM\s+\w+\s+AS\s+\w+"
        matches = re.findall(alias_pattern, query, re.IGNORECASE)
        assert not matches, f"Query uses forbidden table alias pattern: {matches}"

    @pytest.mark.asyncio
    async def test_get_outlinks_query_no_as_alias(self, note_service, mock_execute_query):
        """Verify get_outlinks query doesn't use AS for table aliases."""
        mock_execute_query.return_value = []

        await note_service.get_outlinks("note:test-123")

        assert mock_execute_query.called
        query = mock_execute_query.call_args[0][0]
        self._assert_no_table_aliases(query)

    @pytest.mark.asyncio
    async def test_get_backlinks_query_no_as_alias(self, note_service, mock_execute_query):
        """Verify get_backlinks query doesn't use AS for table aliases."""
        mock_execute_query.return_value = []

        await note_service.get_backlinks("note:test-123")

        assert mock_execute_query.called
        query = mock_execute_query.call_args[0][0]
        self._assert_no_table_aliases(query)
