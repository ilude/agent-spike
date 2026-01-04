"""Integration tests for NoteService against real SurrealDB.

Tests note CRUD, wiki-link parsing, backlinks, and graph data generation.

Run with: pytest -m integration compose/tests/integration/
"""

import pytest
from surrealdb import AsyncSurreal


class TestNoteCRUDIntegration:
    """Integration tests for note CRUD operations."""

    @pytest.mark.asyncio
    async def test_create_note(self, clean_tables: AsyncSurreal):
        """Test creating a note with all fields."""
        db = clean_tables

        # Create vault first
        await db.query("""
            CREATE vault:v1 SET
                name = "Test Vault",
                slug = "test-vault",
                storage_type = "minio",
                created_at = time::now(),
                updated_at = time::now();
        """)

        # Create note
        result = await db.query("""
            CREATE note:n1 SET
                vault_id = vault:v1,
                path = "inbox/test-note.md",
                title = "Test Note",
                content = "# Test Note\n\nSome content here.",
                preview = "Some content here.",
                word_count = 4,
                created_at = time::now(),
                updated_at = time::now();
        """)

        assert len(result) > 0
        note = result[0]
        assert note["title"] == "Test Note"
        assert note["path"] == "inbox/test-note.md"

    @pytest.mark.asyncio
    async def test_get_note_by_id(self, clean_tables: AsyncSurreal):
        """Test retrieving note by ID using type::thing."""
        db = clean_tables

        # Create vault and note
        await db.query("""
            CREATE vault:v1 SET
                name = "Test", slug = "test", storage_type = "minio",
                created_at = time::now(), updated_at = time::now();
        """)
        await db.query("""
            CREATE note:gettest SET
                vault_id = vault:v1, path = "test.md", title = "Get Test",
                content = "Content", preview = "Content", word_count = 1,
                created_at = time::now(), updated_at = time::now();
        """)

        # Retrieve using type::thing (the pattern we use in code)
        result = await db.query("""
            SELECT * FROM type::thing("note", "gettest");
        """)

        assert len(result) > 0
        assert result[0]["title"] == "Get Test"

    @pytest.mark.asyncio
    async def test_get_note_by_path(self, clean_tables: AsyncSurreal):
        """Test retrieving note by vault_id and path."""
        db = clean_tables

        await db.query("""
            CREATE vault:pathv SET
                name = "Path Vault", slug = "path", storage_type = "minio",
                created_at = time::now(), updated_at = time::now();
        """)
        await db.query("""
            CREATE note:pathtest SET
                vault_id = vault:pathv, path = "folder/specific.md",
                title = "Specific Note", content = "Content", preview = "Content",
                word_count = 1, created_at = time::now(), updated_at = time::now();
        """)

        # vault_id is stored as record reference, must use type::thing
        result = await db.query("""
            SELECT * FROM note
            WHERE vault_id = type::thing($vault_id) AND path = $path
            LIMIT 1;
        """, {"vault_id": "vault:pathv", "path": "folder/specific.md"})

        assert len(result) > 0
        assert result[0]["title"] == "Specific Note"

    @pytest.mark.asyncio
    async def test_update_note(self, clean_tables: AsyncSurreal):
        """Test updating note content and metadata."""
        db = clean_tables

        await db.query("""
            CREATE vault:upd SET
                name = "Update Vault", slug = "upd", storage_type = "minio",
                created_at = time::now(), updated_at = time::now();
        """)
        await db.query("""
            CREATE note:updnote SET
                vault_id = vault:upd, path = "update.md",
                title = "Original Title", content = "Original",
                preview = "Original", word_count = 1,
                created_at = time::now(), updated_at = time::now();
        """)

        # Update note
        result = await db.query("""
            UPDATE type::thing("note", "updnote") SET
                title = $title,
                content = $content,
                preview = $preview,
                word_count = $word_count,
                updated_at = time::now();
        """, {
            "title": "Updated Title",
            "content": "New content here",
            "preview": "New content here",
            "word_count": 3,
        })

        assert len(result) > 0
        assert result[0]["title"] == "Updated Title"
        assert result[0]["content"] == "New content here"

    @pytest.mark.asyncio
    async def test_delete_note(self, clean_tables: AsyncSurreal):
        """Test deleting a note."""
        db = clean_tables

        await db.query("""
            CREATE vault:del SET
                name = "Del", slug = "del", storage_type = "minio",
                created_at = time::now(), updated_at = time::now();
        """)
        await db.query("""
            CREATE note:delnote SET
                vault_id = vault:del, path = "delete.md", title = "To Delete",
                content = "Delete me", preview = "Delete me", word_count = 2,
                created_at = time::now(), updated_at = time::now();
        """)

        # Verify exists
        exists = await db.query("SELECT * FROM note:delnote;")
        assert len(exists) > 0

        # Delete using type::thing
        await db.query('DELETE type::thing("note", "delnote");')

        # Verify deleted
        after = await db.query("SELECT * FROM note:delnote;")
        assert len(after) == 0

    @pytest.mark.asyncio
    async def test_list_notes_by_vault(self, clean_tables: AsyncSurreal):
        """Test listing notes filtered by vault."""
        db = clean_tables

        # Create two vaults with notes
        await db.query("""
            CREATE vault:list1 SET name = "List 1", slug = "list1",
                storage_type = "minio", created_at = time::now(), updated_at = time::now();
        """)
        await db.query("""
            CREATE vault:list2 SET name = "List 2", slug = "list2",
                storage_type = "minio", created_at = time::now(), updated_at = time::now();
        """)

        await db.query("""
            CREATE note:l1n1 SET vault_id = vault:list1, path = "note1.md",
                title = "Note 1", content = "", preview = "", word_count = 0,
                created_at = time::now(), updated_at = time::now();
        """)
        await db.query("""
            CREATE note:l1n2 SET vault_id = vault:list1, path = "note2.md",
                title = "Note 2", content = "", preview = "", word_count = 0,
                created_at = time::now(), updated_at = time::now();
        """)
        await db.query("""
            CREATE note:l2n1 SET vault_id = vault:list2, path = "other.md",
                title = "Other", content = "", preview = "", word_count = 0,
                created_at = time::now(), updated_at = time::now();
        """)

        # List notes for vault:list1 (vault_id stored as record reference)
        result = await db.query("""
            SELECT * FROM note WHERE vault_id = type::thing($vault_id) ORDER BY path ASC;
        """, {"vault_id": "vault:list1"})

        assert len(result) == 2
        assert result[0]["title"] == "Note 1"
        assert result[1]["title"] == "Note 2"


class TestWikiLinksIntegration:
    """Integration tests for wiki-link storage and retrieval."""

    @pytest.mark.asyncio
    async def test_create_note_link(self, clean_tables: AsyncSurreal):
        """Test creating a link between notes."""
        db = clean_tables

        # Create vault and notes
        await db.query("""
            CREATE vault:wl SET name = "Wiki Links", slug = "wl",
                storage_type = "minio", created_at = time::now(), updated_at = time::now();
        """)
        await db.query("""
            CREATE note:source SET vault_id = vault:wl, path = "source.md",
                title = "Source Note", content = "Links to [[Target]]",
                preview = "Links to Target", word_count = 3,
                created_at = time::now(), updated_at = time::now();
        """)
        await db.query("""
            CREATE note:target SET vault_id = vault:wl, path = "target.md",
                title = "Target Note", content = "Linked from source",
                preview = "Linked from source", word_count = 3,
                created_at = time::now(), updated_at = time::now();
        """)

        # Create link (as our service does)
        await db.query("""
            CREATE note_link:link1 SET
                source_id = note:source,
                target_id = note:target,
                link_text = "Target",
                link_type = "manual",
                accepted = true,
                created_at = time::now();
        """)

        # Verify link exists
        links = await db.query("SELECT * FROM note_link;")
        assert len(links) == 1
        assert links[0]["link_text"] == "Target"

    @pytest.mark.asyncio
    async def test_get_outlinks_with_type_thing(self, clean_tables: AsyncSurreal):
        """Test outlinks query uses type::thing for record comparison."""
        db = clean_tables

        await db.query("""
            CREATE note:outsrc SET vault_id = vault:v1, path = "out.md",
                title = "Out Source", content = "", preview = "", word_count = 0,
                created_at = time::now(), updated_at = time::now();
        """)
        await db.query("""
            CREATE note:outtgt SET vault_id = vault:v1, path = "target.md",
                title = "Out Target", content = "", preview = "", word_count = 0,
                created_at = time::now(), updated_at = time::now();
        """)
        await db.query("""
            CREATE note_link:outlink SET
                source_id = note:outsrc,
                target_id = note:outtgt,
                link_text = "Out Target",
                link_type = "manual",
                accepted = true,
                created_at = time::now();
        """)

        # Query using the pattern from notes.py (with type::thing)
        result = await db.query("""
            SELECT
                *,
                (SELECT title FROM note WHERE id = $parent.target_id)[0].title AS target_title,
                (SELECT path FROM note WHERE id = $parent.target_id)[0].path AS target_path
            FROM note_link
            WHERE source_id = type::thing($note_id) AND accepted = true
            ORDER BY created_at ASC;
        """, {"note_id": "note:outsrc"})

        assert len(result) == 1
        assert result[0]["link_text"] == "Out Target"
        assert result[0]["target_title"] == "Out Target"
        assert result[0]["target_path"] == "target.md"

    @pytest.mark.asyncio
    async def test_get_backlinks_with_type_thing(self, clean_tables: AsyncSurreal):
        """Test backlinks query uses type::thing for record comparison."""
        db = clean_tables

        await db.query("""
            CREATE note:backsrc SET vault_id = vault:v1, path = "linker.md",
                title = "Linker Note", content = "", preview = "", word_count = 0,
                created_at = time::now(), updated_at = time::now();
        """)
        await db.query("""
            CREATE note:backtgt SET vault_id = vault:v1, path = "linked.md",
                title = "Linked Note", content = "", preview = "", word_count = 0,
                created_at = time::now(), updated_at = time::now();
        """)
        await db.query("""
            CREATE note_link:backlink SET
                source_id = note:backsrc,
                target_id = note:backtgt,
                link_text = "Linked Note",
                link_type = "manual",
                accepted = true,
                created_at = time::now();
        """)

        # Query using the pattern from notes.py (with type::thing)
        result = await db.query("""
            SELECT
                *,
                (SELECT title FROM note WHERE id = $parent.source_id)[0].title AS source_title
            FROM note_link
            WHERE target_id = type::thing($note_id) AND accepted = true
            ORDER BY created_at DESC;
        """, {"note_id": "note:backtgt"})

        assert len(result) == 1
        assert result[0]["source_title"] == "Linker Note"

    @pytest.mark.asyncio
    async def test_delete_links_with_type_thing(self, clean_tables: AsyncSurreal):
        """Test deleting links uses type::thing for record comparison."""
        db = clean_tables

        await db.query("""
            CREATE note:delsrc SET vault_id = vault:v1, path = "src.md",
                title = "Src", content = "", preview = "", word_count = 0,
                created_at = time::now(), updated_at = time::now();
        """)
        await db.query("""
            CREATE note:deltgt SET vault_id = vault:v1, path = "tgt.md",
                title = "Tgt", content = "", preview = "", word_count = 0,
                created_at = time::now(), updated_at = time::now();
        """)
        await db.query("""
            CREATE note_link:dellink SET
                source_id = note:delsrc,
                target_id = note:deltgt,
                link_text = "Tgt",
                link_type = "manual",
                accepted = true,
                created_at = time::now();
        """)

        # Delete using the pattern from notes.py
        await db.query("""
            DELETE note_link
            WHERE source_id = type::thing($id) OR target_id = type::thing($id);
        """, {"id": "note:delsrc"})

        # Verify deleted
        links = await db.query("SELECT * FROM note_link;")
        assert len(links) == 0


class TestGraphDataIntegration:
    """Integration tests for graph data generation."""

    @pytest.mark.asyncio
    async def test_get_graph_nodes(self, clean_tables: AsyncSurreal):
        """Test retrieving notes as graph nodes."""
        db = clean_tables

        await db.query("""
            CREATE vault:graph SET name = "Graph", slug = "graph",
                storage_type = "minio", created_at = time::now(), updated_at = time::now();
        """)
        await db.query("""
            CREATE note:gn1 SET vault_id = vault:graph, path = "node1.md",
                title = "Node 1", content = "", preview = "", word_count = 0,
                created_at = time::now(), updated_at = time::now();
        """)
        await db.query("""
            CREATE note:gn2 SET vault_id = vault:graph, path = "node2.md",
                title = "Node 2", content = "", preview = "", word_count = 0,
                created_at = time::now(), updated_at = time::now();
        """)

        # Query using the pattern from notes.py (vault_id is record reference)
        result = await db.query("""
            SELECT id, title FROM note WHERE vault_id = type::thing($vault_id);
        """, {"vault_id": "vault:graph"})

        assert len(result) == 2
        titles = {r["title"] for r in result}
        assert titles == {"Node 1", "Node 2"}

    @pytest.mark.asyncio
    async def test_get_graph_edges(self, clean_tables: AsyncSurreal):
        """Test retrieving links as graph edges."""
        db = clean_tables

        await db.query("""
            CREATE vault:edges SET name = "Edges", slug = "edges",
                storage_type = "minio", created_at = time::now(), updated_at = time::now();
        """)
        await db.query("""
            CREATE note:en1 SET vault_id = vault:edges, path = "n1.md",
                title = "N1", content = "", preview = "", word_count = 0,
                created_at = time::now(), updated_at = time::now();
        """)
        await db.query("""
            CREATE note:en2 SET vault_id = vault:edges, path = "n2.md",
                title = "N2", content = "", preview = "", word_count = 0,
                created_at = time::now(), updated_at = time::now();
        """)
        await db.query("""
            CREATE note_link:edge1 SET
                source_id = note:en1,
                target_id = note:en2,
                link_text = "N2",
                link_type = "manual",
                accepted = true,
                created_at = time::now();
        """)

        # Get note IDs first, then filter links
        note_ids = await db.query("""
            SELECT id FROM note WHERE vault_id = type::thing($vault_id);
        """, {"vault_id": "vault:edges"})
        assert len(note_ids) == 2

        # Get all accepted links with resolved targets
        result = await db.query("""
            SELECT source_id, target_id FROM note_link
            WHERE target_id IS NOT NULL AND accepted = true;
        """)

        assert len(result) == 1
        # source_id and target_id are record references
        assert "note:en1" in str(result[0]["source_id"])
        assert "note:en2" in str(result[0]["target_id"])


class TestNoteSearchIntegration:
    """Integration tests for note search queries."""

    @pytest.mark.asyncio
    async def test_search_by_title(self, clean_tables: AsyncSurreal):
        """Test searching notes by title."""
        db = clean_tables

        await db.query("""
            CREATE vault:search SET name = "Search", slug = "search",
                storage_type = "minio", created_at = time::now(), updated_at = time::now();
        """)
        await db.query("""
            CREATE note:s1 SET vault_id = vault:search, path = "apple.md",
                title = "Apple Recipes", content = "Various apple recipes",
                preview = "Various apple recipes", word_count = 3,
                created_at = time::now(), updated_at = time::now();
        """)
        await db.query("""
            CREATE note:s2 SET vault_id = vault:search, path = "banana.md",
                title = "Banana Bread", content = "How to make banana bread",
                preview = "How to make banana bread", word_count = 5,
                created_at = time::now(), updated_at = time::now();
        """)

        # Search for "apple" (vault_id is record reference)
        result = await db.query("""
            SELECT * FROM note
            WHERE vault_id = type::thing($vault_id)
            AND (
                string::lowercase(title) CONTAINS string::lowercase($query)
                OR string::lowercase(content) CONTAINS string::lowercase($query)
            )
            ORDER BY updated_at DESC;
        """, {"vault_id": "vault:search", "query": "apple"})

        assert len(result) == 1
        assert result[0]["title"] == "Apple Recipes"

    @pytest.mark.asyncio
    async def test_search_by_content(self, clean_tables: AsyncSurreal):
        """Test searching notes by content."""
        db = clean_tables

        await db.query("""
            CREATE vault:srchc SET name = "Search C", slug = "searchc",
                storage_type = "minio", created_at = time::now(), updated_at = time::now();
        """)
        await db.query("""
            CREATE note:sc1 SET vault_id = vault:srchc, path = "recipe.md",
                title = "Fruit Recipe", content = "Use fresh oranges",
                preview = "Use fresh oranges", word_count = 3,
                created_at = time::now(), updated_at = time::now();
        """)

        # Search for content word (vault_id is record reference)
        result = await db.query("""
            SELECT * FROM note
            WHERE vault_id = type::thing($vault_id)
            AND (
                string::lowercase(title) CONTAINS string::lowercase($query)
                OR string::lowercase(content) CONTAINS string::lowercase($query)
            );
        """, {"vault_id": "vault:srchc", "query": "oranges"})

        assert len(result) == 1
        assert result[0]["title"] == "Fruit Recipe"

    @pytest.mark.asyncio
    async def test_search_case_insensitive(self, clean_tables: AsyncSurreal):
        """Test search is case-insensitive."""
        db = clean_tables

        await db.query("""
            CREATE vault:case SET name = "Case", slug = "case",
                storage_type = "minio", created_at = time::now(), updated_at = time::now();
        """)
        await db.query("""
            CREATE note:case1 SET vault_id = vault:case, path = "test.md",
                title = "UPPERCASE TITLE", content = "lowercase content",
                preview = "lowercase content", word_count = 2,
                created_at = time::now(), updated_at = time::now();
        """)

        # Search with different case (vault_id is record reference)
        result = await db.query("""
            SELECT * FROM note
            WHERE vault_id = type::thing($vault_id)
            AND (
                string::lowercase(title) CONTAINS string::lowercase($query)
                OR string::lowercase(content) CONTAINS string::lowercase($query)
            );
        """, {"vault_id": "vault:case", "query": "uppercase"})

        assert len(result) == 1
        assert result[0]["title"] == "UPPERCASE TITLE"
