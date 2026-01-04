"""Integration tests for VaultService against real SurrealDB.

These tests verify that our SurrealDB queries actually work,
catching syntax issues that mocked tests miss.

Run with: pytest -m integration compose/tests/integration/
"""

import pytest
from surrealdb import AsyncSurreal

from compose.services.surrealdb.models import FileTreeNode


class TestVaultServiceIntegration:
    """Integration tests for vault CRUD operations."""

    @pytest.mark.asyncio
    async def test_create_and_get_vault(self, clean_tables: AsyncSurreal):
        """Test creating a vault and retrieving it by ID."""
        db = clean_tables

        # Create a vault directly with SurrealDB
        result = await db.query("""
            CREATE vault SET
                id = "test-vault-1",
                name = "Test Vault",
                slug = "test-vault",
                storage_type = "minio",
                minio_bucket = "test-bucket",
                settings = {},
                created_at = time::now(),
                updated_at = time::now();
        """)

        # Verify we can retrieve it using type::thing (the pattern we use in code)
        get_result = await db.query("""
            SELECT * FROM type::thing("vault", "test-vault-1");
        """)

        assert len(get_result) > 0
        vault = get_result[0]
        assert vault["name"] == "Test Vault"
        assert vault["slug"] == "test-vault"

    @pytest.mark.asyncio
    async def test_list_vaults_with_note_count(self, clean_tables: AsyncSurreal):
        """Test listing vaults with note count subquery."""
        db = clean_tables

        # Create a vault using record ID syntax
        await db.query("""
            CREATE vault:vaultwn SET
                name = "Vault With Notes",
                slug = "vault-with-notes",
                storage_type = "minio",
                created_at = time::now(),
                updated_at = time::now();
        """)

        # Create notes with vault_id as record reference (not string)
        await db.query("""
            CREATE note:n1 SET
                vault_id = vault:vaultwn,
                path = "note1.md",
                title = "Note 1",
                created_at = time::now(),
                updated_at = time::now();
        """)
        await db.query("""
            CREATE note:n2 SET
                vault_id = vault:vaultwn,
                path = "note2.md",
                title = "Note 2",
                created_at = time::now(),
                updated_at = time::now();
        """)

        # Query using our actual pattern (no AS alias, uses $parent)
        result = await db.query("""
            SELECT
                *,
                (SELECT count() FROM note WHERE vault_id = $parent.id GROUP ALL)[0].count AS note_count
            FROM vault
            ORDER BY updated_at DESC;
        """)

        assert len(result) > 0
        vault = result[0]
        assert vault["name"] == "Vault With Notes"
        # Note count should be 2
        assert vault["note_count"] == 2

    @pytest.mark.asyncio
    async def test_get_vault_by_slug(self, clean_tables: AsyncSurreal):
        """Test getting vault by slug."""
        db = clean_tables

        # Create a vault
        await db.query("""
            CREATE vault SET
                id = "slug-test-vault",
                name = "Slug Test",
                slug = "my-unique-slug",
                storage_type = "minio",
                created_at = time::now(),
                updated_at = time::now();
        """)

        # Query by slug using our pattern
        result = await db.query("""
            SELECT
                *,
                (SELECT count() FROM note WHERE vault_id = $parent.id GROUP ALL)[0].count AS note_count
            FROM vault
            WHERE slug = $slug
            LIMIT 1;
        """, {"slug": "my-unique-slug"})

        assert len(result) > 0
        assert result[0]["name"] == "Slug Test"

    @pytest.mark.asyncio
    async def test_update_vault(self, clean_tables: AsyncSurreal):
        """Test updating vault metadata."""
        db = clean_tables

        # Create a vault
        await db.query("""
            CREATE vault SET
                id = "update-test",
                name = "Original Name",
                slug = "original-slug",
                storage_type = "minio",
                settings = {},
                created_at = time::now(),
                updated_at = time::now();
        """)

        # Update using our pattern
        result = await db.query("""
            UPDATE type::thing("vault", "update-test") SET
                name = $name,
                slug = $slug,
                updated_at = time::now();
        """, {"name": "Updated Name", "slug": "updated-slug"})

        assert len(result) > 0
        assert result[0]["name"] == "Updated Name"
        assert result[0]["slug"] == "updated-slug"

    @pytest.mark.asyncio
    async def test_delete_vault_cascade(self, clean_tables: AsyncSurreal):
        """Test deleting a vault and its associated data."""
        db = clean_tables

        # Create vault with notes
        await db.query("""
            CREATE vault SET
                id = "delete-test",
                name = "To Delete",
                slug = "delete-me",
                storage_type = "minio",
                created_at = time::now(),
                updated_at = time::now();
        """)
        await db.query("""
            CREATE note SET
                id = "orphan-note",
                vault_id = "delete-test",
                path = "orphan.md",
                title = "Orphan",
                created_at = time::now(),
                updated_at = time::now();
        """)

        # Delete notes first, then vault (as our service does)
        await db.query("DELETE note WHERE vault_id = $id;", {"id": "delete-test"})
        await db.query("DELETE type::thing('vault', $id);", {"id": "delete-test"})

        # Verify both are gone
        vaults = await db.query("SELECT * FROM vault WHERE id = 'delete-test';")
        notes = await db.query("SELECT * FROM note WHERE vault_id = 'delete-test';")

        assert len(vaults) == 0
        assert len(notes) == 0


class TestNoteLinksIntegration:
    """Integration tests for note link queries."""

    @pytest.mark.asyncio
    async def test_get_outlinks_query(self, clean_tables: AsyncSurreal):
        """Test outlinks query syntax works."""
        db = clean_tables

        # Create notes using record ID syntax
        await db.query("""
            CREATE note:source SET vault_id = vault:v1, path = "source.md",
                title = "Source", created_at = time::now(), updated_at = time::now();
        """)
        await db.query("""
            CREATE note:target SET vault_id = vault:v1, path = "target.md",
                title = "Target Note", created_at = time::now(), updated_at = time::now();
        """)

        # Create link with record references
        await db.query("""
            CREATE note_link:link1 SET
                source_id = note:source,
                target_id = note:target,
                link_text = "Target Note",
                link_type = "manual",
                accepted = true,
                created_at = time::now();
        """)

        # Query using our actual pattern (no AS alias)
        # Note: must use type::thing() to compare string param to record reference
        result = await db.query("""
            SELECT
                *,
                (SELECT title FROM note WHERE id = $parent.target_id)[0].title AS target_title,
                (SELECT path FROM note WHERE id = $parent.target_id)[0].path AS target_path
            FROM note_link
            WHERE source_id = type::thing($note_id) AND accepted = true
            ORDER BY created_at ASC;
        """, {"note_id": "note:source"})

        assert len(result) > 0
        link = result[0]
        assert link["link_text"] == "Target Note"
        assert link["target_title"] == "Target Note"

    @pytest.mark.asyncio
    async def test_get_backlinks_query(self, clean_tables: AsyncSurreal):
        """Test backlinks query syntax works."""
        db = clean_tables

        # Create notes using record ID syntax
        await db.query("""
            CREATE note:linker SET vault_id = vault:v1, path = "linker.md",
                title = "Linker Note", created_at = time::now(), updated_at = time::now();
        """)
        await db.query("""
            CREATE note:linked SET vault_id = vault:v1, path = "linked.md",
                title = "Linked Note", created_at = time::now(), updated_at = time::now();
        """)

        # Create link with record references
        await db.query("""
            CREATE note_link:backlink1 SET
                source_id = note:linker,
                target_id = note:linked,
                link_text = "Linked Note",
                link_type = "manual",
                accepted = true,
                created_at = time::now();
        """)

        # Query using our actual pattern
        # Note: must use type::thing() to compare string param to record reference
        result = await db.query("""
            SELECT
                *,
                (SELECT title FROM note WHERE id = $parent.source_id)[0].title AS source_title
            FROM note_link
            WHERE target_id = type::thing($note_id) AND accepted = true
            ORDER BY created_at DESC;
        """, {"note_id": "note:linked"})

        assert len(result) > 0
        assert result[0]["source_title"] == "Linker Note"


class TestFileTreeIntegration:
    """Integration tests for file tree queries."""

    @pytest.mark.asyncio
    async def test_file_tree_query(self, clean_tables: AsyncSurreal):
        """Test file tree query returns notes in correct order."""
        db = clean_tables

        # Create vault
        await db.query("""
            CREATE vault SET id = "tree-vault", name = "Tree Test",
                slug = "tree-test", storage_type = "minio",
                created_at = time::now(), updated_at = time::now();
        """)

        # Create notes with paths
        await db.query("""
            CREATE note SET id = "n1", vault_id = "tree-vault",
                path = "folder/note1.md", title = "Note 1",
                created_at = time::now(), updated_at = time::now();
        """)
        await db.query("""
            CREATE note SET id = "n2", vault_id = "tree-vault",
                path = "folder/subfolder/note2.md", title = "Note 2",
                created_at = time::now(), updated_at = time::now();
        """)
        await db.query("""
            CREATE note SET id = "n3", vault_id = "tree-vault",
                path = "root-note.md", title = "Root Note",
                created_at = time::now(), updated_at = time::now();
        """)

        # Query using our actual pattern
        result = await db.query("""
            SELECT id, path, title FROM note
            WHERE vault_id = $vault_id
            ORDER BY path ASC;
        """, {"vault_id": "tree-vault"})

        assert len(result) == 3
        # Should be sorted by path
        paths = [r["path"] for r in result]
        assert paths == ["folder/note1.md", "folder/subfolder/note2.md", "root-note.md"]
