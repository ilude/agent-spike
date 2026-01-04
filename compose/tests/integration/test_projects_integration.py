"""Integration tests for ProjectService against real SurrealDB.

Tests project CRUD, file metadata, and conversation linking.

Run with: pytest -m integration compose/tests/integration/
"""

import pytest
from surrealdb import AsyncSurreal


class TestProjectCRUDIntegration:
    """Integration tests for project CRUD operations."""

    @pytest.mark.asyncio
    async def test_create_project(self, clean_tables: AsyncSurreal):
        """Test creating a project."""
        db = clean_tables

        result = await db.query("""
            CREATE project CONTENT {
                id: $id,
                name: $name,
                description: $description,
                custom_instructions: "",
                created_at: $created_at,
                updated_at: $updated_at
            };
        """, {
            "id": "proj1",
            "name": "Test Project",
            "description": "A test project",
            "created_at": "2024-01-01T00:00:00Z",
            "updated_at": "2024-01-01T00:00:00Z",
        })

        assert len(result) > 0
        assert result[0]["name"] == "Test Project"

    @pytest.mark.asyncio
    async def test_get_project_by_id(self, clean_tables: AsyncSurreal):
        """Test retrieving project by ID."""
        db = clean_tables

        await db.query("""
            CREATE project CONTENT {
                id: "getproj",
                name: "Get Project",
                description: "For retrieval",
                custom_instructions: "Be helpful",
                created_at: time::now(),
                updated_at: time::now()
            };
        """)

        # Use record ID syntax for retrieval
        result = await db.query("SELECT * FROM project:`getproj`")

        assert len(result) > 0
        assert result[0]["name"] == "Get Project"
        assert result[0]["custom_instructions"] == "Be helpful"

    @pytest.mark.asyncio
    async def test_update_project(self, clean_tables: AsyncSurreal):
        """Test updating project settings."""
        db = clean_tables

        await db.query("""
            CREATE project CONTENT {
                id: "updproj",
                name: "Original Name",
                description: "",
                custom_instructions: "",
                created_at: time::now(),
                updated_at: time::now()
            };
        """)

        # Use record ID syntax for UPDATE
        result = await db.query("""
            UPDATE project:`updproj` SET
                name = $name,
                description = $description,
                updated_at = time::now();
        """, {
            "name": "Updated Name",
            "description": "Now with description",
        })

        assert len(result) > 0
        assert result[0]["name"] == "Updated Name"
        assert result[0]["description"] == "Now with description"

    @pytest.mark.asyncio
    async def test_list_projects_ordered(self, clean_tables: AsyncSurreal):
        """Test listing projects ordered by updated_at."""
        db = clean_tables

        await db.query("""
            CREATE project CONTENT {
                id: "oldproj",
                name: "Old Project",
                description: "",
                custom_instructions: "",
                created_at: "2024-01-01T00:00:00Z",
                updated_at: "2024-01-01T00:00:00Z"
            };
        """)
        await db.query("""
            CREATE project CONTENT {
                id: "newproj",
                name: "New Project",
                description: "",
                custom_instructions: "",
                created_at: "2024-06-01T00:00:00Z",
                updated_at: "2024-06-01T00:00:00Z"
            };
        """)

        result = await db.query("""
            SELECT * FROM project ORDER BY updated_at DESC;
        """)

        assert len(result) == 2
        assert result[0]["name"] == "New Project"

    @pytest.mark.asyncio
    async def test_delete_project(self, clean_tables: AsyncSurreal):
        """Test deleting a project."""
        db = clean_tables

        await db.query("""
            CREATE project CONTENT {
                id: "delproj",
                name: "Delete Me",
                description: "",
                custom_instructions: "",
                created_at: time::now(),
                updated_at: time::now()
            };
        """)

        # Verify exists using record ID syntax
        before = await db.query("SELECT * FROM project:`delproj`")
        assert len(before) > 0

        # Delete using record ID syntax
        await db.query("DELETE project:`delproj`")

        # Verify deleted
        after = await db.query("SELECT * FROM project:`delproj`")
        assert len(after) == 0


class TestProjectFileIntegration:
    """Integration tests for project file operations."""

    @pytest.mark.asyncio
    async def test_create_project_file(self, clean_tables: AsyncSurreal):
        """Test creating a project file record."""
        db = clean_tables

        result = await db.query("""
            CREATE project_file CONTENT {
                id: $id,
                project_id: $project_id,
                filename: $filename,
                original_filename: $original_filename,
                content_type: $content_type,
                size_bytes: $size_bytes,
                minio_key: $minio_key,
                processed: false,
                vector_indexed: false,
                processing_error: NONE,
                uploaded_at: time::now()
            };
        """, {
            "id": "file1",
            "project_id": "proj1",
            "filename": "doc.pdf",
            "original_filename": "Document.pdf",
            "content_type": "application/pdf",
            "size_bytes": 1024,
            "minio_key": "projects/proj1/file1_doc.pdf",
        })

        assert len(result) > 0
        assert result[0]["filename"] == "doc.pdf"

    @pytest.mark.asyncio
    async def test_list_project_files(self, clean_tables: AsyncSurreal):
        """Test listing files for a project."""
        db = clean_tables

        await db.query("""
            CREATE project_file CONTENT {
                id: "lf1", project_id: "listproj",
                filename: "first.txt", original_filename: "first.txt",
                content_type: "text/plain", size_bytes: 100,
                minio_key: "projects/listproj/lf1_first.txt",
                processed: false, vector_indexed: false,
                uploaded_at: "2024-01-01T00:00:00Z"
            };
        """)
        await db.query("""
            CREATE project_file CONTENT {
                id: "lf2", project_id: "listproj",
                filename: "second.txt", original_filename: "second.txt",
                content_type: "text/plain", size_bytes: 200,
                minio_key: "projects/listproj/lf2_second.txt",
                processed: false, vector_indexed: false,
                uploaded_at: "2024-01-02T00:00:00Z"
            };
        """)

        result = await db.query("""
            SELECT * FROM project_file
            WHERE project_id = $project_id
            ORDER BY uploaded_at DESC;
        """, {"project_id": "listproj"})

        assert len(result) == 2
        assert result[0]["filename"] == "second.txt"

    @pytest.mark.asyncio
    async def test_mark_file_processed(self, clean_tables: AsyncSurreal):
        """Test marking a file as processed."""
        db = clean_tables

        await db.query("""
            CREATE project_file CONTENT {
                id: "procfile", project_id: "procproj",
                filename: "data.csv", original_filename: "data.csv",
                content_type: "text/csv", size_bytes: 500,
                minio_key: "projects/procproj/procfile_data.csv",
                processed: false, vector_indexed: false,
                uploaded_at: time::now()
            };
        """)

        # Use record ID syntax for UPDATE
        result = await db.query("""
            UPDATE project_file:`procfile` SET
                processed = true,
                vector_indexed = $vector_indexed;
        """, {"vector_indexed": True})

        assert len(result) > 0
        assert result[0]["processed"] is True
        assert result[0]["vector_indexed"] is True

    @pytest.mark.asyncio
    async def test_mark_file_failed(self, clean_tables: AsyncSurreal):
        """Test recording a file processing error."""
        db = clean_tables

        await db.query("""
            CREATE project_file CONTENT {
                id: "failfile", project_id: "failproj",
                filename: "bad.pdf", original_filename: "bad.pdf",
                content_type: "application/pdf", size_bytes: 100,
                minio_key: "projects/failproj/failfile_bad.pdf",
                processed: false, vector_indexed: false,
                uploaded_at: time::now()
            };
        """)

        # Use record ID syntax for UPDATE
        result = await db.query("""
            UPDATE project_file:`failfile` SET
                processed = true,
                vector_indexed = false,
                processing_error = $error;
        """, {"error": "Invalid PDF format"})

        assert len(result) > 0
        assert result[0]["processing_error"] == "Invalid PDF format"

    @pytest.mark.asyncio
    async def test_delete_project_file(self, clean_tables: AsyncSurreal):
        """Test deleting a project file."""
        db = clean_tables

        await db.query("""
            CREATE project_file CONTENT {
                id: "delfile", project_id: "delfileproj",
                filename: "remove.txt", original_filename: "remove.txt",
                content_type: "text/plain", size_bytes: 50,
                minio_key: "projects/delfileproj/delfile_remove.txt",
                processed: false, vector_indexed: false,
                uploaded_at: time::now()
            };
        """)

        # Delete
        await db.query("DELETE FROM project_file WHERE id = $id", {"id": "delfile"})

        # Verify deleted
        result = await db.query("SELECT * FROM project_file WHERE id = 'delfile'")
        assert len(result) == 0


class TestProjectConversationIntegration:
    """Integration tests for project-conversation linking."""

    @pytest.mark.asyncio
    async def test_add_conversation_to_project(self, clean_tables: AsyncSurreal):
        """Test linking a conversation to a project."""
        db = clean_tables

        result = await db.query("""
            CREATE project_conversation CONTENT {
                project_id: $project_id,
                conversation_id: $conversation_id,
                created_at: time::now()
            };
        """, {"project_id": "proj1", "conversation_id": "conv1"})

        assert len(result) > 0
        assert result[0]["project_id"] == "proj1"
        assert result[0]["conversation_id"] == "conv1"

    @pytest.mark.asyncio
    async def test_list_project_conversations(self, clean_tables: AsyncSurreal):
        """Test listing conversations for a project."""
        db = clean_tables

        await db.query("""
            CREATE project_conversation CONTENT {
                project_id: "listpc", conversation_id: "c1", created_at: time::now()
            };
        """)
        await db.query("""
            CREATE project_conversation CONTENT {
                project_id: "listpc", conversation_id: "c2", created_at: time::now()
            };
        """)

        result = await db.query("""
            SELECT conversation_id FROM project_conversation
            WHERE project_id = $project_id;
        """, {"project_id": "listpc"})

        assert len(result) == 2
        conv_ids = {r["conversation_id"] for r in result}
        assert conv_ids == {"c1", "c2"}

    @pytest.mark.asyncio
    async def test_count_project_conversations(self, clean_tables: AsyncSurreal):
        """Test counting conversations for a project."""
        db = clean_tables

        await db.query("""
            CREATE project_conversation CONTENT {
                project_id: "countpc", conversation_id: "cx1", created_at: time::now()
            };
        """)
        await db.query("""
            CREATE project_conversation CONTENT {
                project_id: "countpc", conversation_id: "cx2", created_at: time::now()
            };
        """)
        await db.query("""
            CREATE project_conversation CONTENT {
                project_id: "countpc", conversation_id: "cx3", created_at: time::now()
            };
        """)

        result = await db.query("""
            SELECT count() FROM project_conversation
            WHERE project_id = $project_id
            GROUP ALL;
        """, {"project_id": "countpc"})

        assert len(result) > 0
        assert result[0]["count"] == 3

    @pytest.mark.asyncio
    async def test_remove_conversation_from_project(self, clean_tables: AsyncSurreal):
        """Test unlinking a conversation from a project."""
        db = clean_tables

        await db.query("""
            CREATE project_conversation CONTENT {
                project_id: "rmpc", conversation_id: "rmconv", created_at: time::now()
            };
        """)

        # Remove
        await db.query("""
            DELETE FROM project_conversation
            WHERE project_id = $project_id AND conversation_id = $conversation_id;
        """, {"project_id": "rmpc", "conversation_id": "rmconv"})

        # Verify removed
        result = await db.query("""
            SELECT * FROM project_conversation
            WHERE project_id = 'rmpc' AND conversation_id = 'rmconv';
        """)
        assert len(result) == 0
