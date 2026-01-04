"""Integration tests for BackupService against real SurrealDB.

Tests backup manifest creation, status updates, listing, and deletion.
Validates the backup table schema and query patterns.

Run with: pytest -m integration compose/tests/integration/
"""

import pytest
from datetime import datetime, timezone
from surrealdb import AsyncSurreal


class TestBackupCRUDIntegration:
    """Integration tests for backup CRUD operations."""

    @pytest.mark.asyncio
    async def test_create_backup_manifest(self, clean_tables: AsyncSurreal):
        """Test creating a backup record with INSERT syntax.

        Validates that backup records can be created with all required fields
        including status, timestamps, and minio_path.
        """
        db = clean_tables

        # Create backup manifest using INSERT (as the service does)
        result = await db.query("""
            INSERT INTO backup {
                id: $id,
                status: $status,
                started_at: $started_at,
                minio_path: $minio_path,
                tables_backed_up: $tables,
                size_bytes: $size
            };
        """, {
            "id": "backup1",
            "status": "pending",
            "started_at": datetime.now(timezone.utc).isoformat(),
            "minio_path": "backups/20250130_120000",
            "tables": [],
            "size": 0,
        })

        assert len(result) > 0
        assert result[0]["status"] == "pending"
        assert result[0]["minio_path"] == "backups/20250130_120000"
        assert result[0]["tables_backed_up"] == []
        assert result[0]["size_bytes"] == 0

    @pytest.mark.asyncio
    async def test_get_backup_by_id(self, clean_tables: AsyncSurreal):
        """Test retrieving backup using record ID syntax.

        Validates that backups can be retrieved by their ID using
        SurrealDB's record ID syntax (backup:`id`).
        """
        db = clean_tables

        # Create backup
        await db.query("""
            INSERT INTO backup {
                id: "gettest",
                status: "completed",
                started_at: time::now(),
                completed_at: time::now(),
                minio_path: "backups/test1",
                tables_backed_up: ["conversation", "message"],
                size_bytes: 1024
            };
        """)

        # Get using record ID syntax (as the service does)
        result = await db.query("SELECT * FROM backup:`gettest`")

        assert len(result) > 0
        assert result[0]["status"] == "completed"
        assert result[0]["minio_path"] == "backups/test1"
        assert len(result[0]["tables_backed_up"]) == 2
        assert result[0]["size_bytes"] == 1024

    @pytest.mark.asyncio
    async def test_update_backup_status(self, clean_tables: AsyncSurreal):
        """Test updating backup status from pending to in_progress to completed.

        Validates the status transition workflow and timestamp updates
        that occur during a backup job lifecycle.
        """
        db = clean_tables

        # Create pending backup
        await db.query("""
            INSERT INTO backup {
                id: "updatetest",
                status: "pending",
                started_at: time::now(),
                minio_path: "backups/update",
                tables_backed_up: [],
                size_bytes: 0
            };
        """)

        # Update to in_progress
        result = await db.query("""
            UPDATE backup:`updatetest` SET
                status = $status;
        """, {"status": "in_progress"})

        assert len(result) > 0
        assert result[0]["status"] == "in_progress"

        # Update to completed with final data
        result = await db.query("""
            UPDATE backup:`updatetest` SET
                status = $status,
                completed_at = $completed_at,
                tables_backed_up = $tables,
                size_bytes = $size;
        """, {
            "status": "completed",
            "completed_at": datetime.now(timezone.utc).isoformat(),
            "tables": ["conversation", "message", "project"],
            "size": 2048,
        })

        assert len(result) > 0
        assert result[0]["status"] == "completed"
        assert result[0]["completed_at"] is not None
        assert len(result[0]["tables_backed_up"]) == 3
        assert result[0]["size_bytes"] == 2048

    @pytest.mark.asyncio
    async def test_delete_backup(self, clean_tables: AsyncSurreal):
        """Test deleting backup record using record ID syntax.

        Validates that backup records can be properly deleted from
        the database.
        """
        db = clean_tables

        # Create backup
        await db.query("""
            INSERT INTO backup {
                id: "deltest",
                status: "completed",
                started_at: time::now(),
                minio_path: "backups/todelete",
                tables_backed_up: [],
                size_bytes: 512
            };
        """)

        # Verify exists
        exists = await db.query("SELECT * FROM backup:`deltest`")
        assert len(exists) > 0

        # Delete
        await db.query("DELETE backup:`deltest`")

        # Verify deleted
        after = await db.query("SELECT * FROM backup:`deltest`")
        assert len(after) == 0


class TestBackupListingIntegration:
    """Integration tests for listing and querying backups."""

    @pytest.mark.asyncio
    async def test_list_backups_ordered_by_timestamp(self, clean_tables: AsyncSurreal):
        """Test listing backups ordered by started_at DESC.

        Validates that backups are returned in reverse chronological order,
        showing the most recent backups first.
        """
        db = clean_tables

        # Create multiple backups with different timestamps
        await db.query("""
            INSERT INTO backup {
                id: "backup1",
                status: "completed",
                started_at: "2025-01-30T10:00:00Z",
                minio_path: "backups/old",
                tables_backed_up: [],
                size_bytes: 0
            };
        """)
        await db.query("""
            INSERT INTO backup {
                id: "backup2",
                status: "completed",
                started_at: "2025-01-30T12:00:00Z",
                minio_path: "backups/new",
                tables_backed_up: [],
                size_bytes: 0
            };
        """)
        await db.query("""
            INSERT INTO backup {
                id: "backup3",
                status: "pending",
                started_at: "2025-01-30T11:00:00Z",
                minio_path: "backups/middle",
                tables_backed_up: [],
                size_bytes: 0
            };
        """)

        # List ordered by started_at DESC (as the service does)
        result = await db.query("""
            SELECT * FROM backup ORDER BY started_at DESC;
        """)

        assert len(result) == 3
        # Most recent first
        assert result[0]["minio_path"] == "backups/new"
        assert result[1]["minio_path"] == "backups/middle"
        assert result[2]["minio_path"] == "backups/old"

    @pytest.mark.asyncio
    async def test_list_backups_by_status(self, clean_tables: AsyncSurreal):
        """Test filtering backups by status field.

        Validates that backups can be filtered by their status
        (pending, in_progress, completed, failed).
        """
        db = clean_tables

        # Create backups with different statuses
        await db.query("""
            INSERT INTO backup {
                id: "completed1",
                status: "completed",
                started_at: time::now(),
                minio_path: "backups/done1",
                tables_backed_up: [],
                size_bytes: 0
            };
        """)
        await db.query("""
            INSERT INTO backup {
                id: "pending1",
                status: "pending",
                started_at: time::now(),
                minio_path: "backups/waiting",
                tables_backed_up: [],
                size_bytes: 0
            };
        """)
        await db.query("""
            INSERT INTO backup {
                id: "failed1",
                status: "failed",
                started_at: time::now(),
                minio_path: "backups/error",
                tables_backed_up: [],
                size_bytes: 0,
                error: "Connection timeout"
            };
        """)

        # Filter by completed status
        result = await db.query("""
            SELECT * FROM backup WHERE status = $status;
        """, {"status": "completed"})

        assert len(result) == 1
        assert result[0]["minio_path"] == "backups/done1"

        # Filter by failed status
        result = await db.query("""
            SELECT * FROM backup WHERE status = $status;
        """, {"status": "failed"})

        assert len(result) == 1
        assert result[0]["error"] == "Connection timeout"


class TestBackupValidationIntegration:
    """Integration tests for backup data validation."""

    @pytest.mark.asyncio
    async def test_backup_manifest_structure(self, clean_tables: AsyncSurreal):
        """Test that backup manifest has all required fields.

        Validates the complete structure of a backup record including
        optional fields like completed_at and error.
        """
        db = clean_tables

        # Create backup with all fields
        await db.query("""
            INSERT INTO backup {
                id: "fullmanifest",
                status: "completed",
                started_at: time::now(),
                completed_at: time::now(),
                minio_path: "backups/20250130_150000",
                tables_backed_up: ["conversation", "message", "project", "artifact"],
                size_bytes: 4096,
                error: NONE
            };
        """)

        result = await db.query("SELECT * FROM backup:`fullmanifest`")

        assert len(result) > 0
        backup = result[0]

        # Validate all required fields exist
        assert "id" in backup
        assert "status" in backup
        assert "started_at" in backup
        assert "completed_at" in backup
        assert "minio_path" in backup
        assert "tables_backed_up" in backup
        assert "size_bytes" in backup

        # Validate field values
        assert backup["status"] == "completed"
        assert backup["minio_path"] == "backups/20250130_150000"
        assert len(backup["tables_backed_up"]) == 4
        assert backup["size_bytes"] == 4096

    @pytest.mark.asyncio
    async def test_backup_with_error_message(self, clean_tables: AsyncSurreal):
        """Test backup with failed status and error message.

        Validates that failed backups properly store error information
        for debugging and monitoring.
        """
        db = clean_tables

        # Create failed backup with error
        await db.query("""
            INSERT INTO backup {
                id: "failedbackup",
                status: "failed",
                started_at: time::now(),
                completed_at: time::now(),
                minio_path: "backups/failed",
                tables_backed_up: ["conversation"],
                size_bytes: 256,
                error: $error
            };
        """, {"error": "MinIO connection timeout after 30s"})

        result = await db.query("SELECT * FROM backup:`failedbackup`")

        assert len(result) > 0
        assert result[0]["status"] == "failed"
        assert result[0]["error"] == "MinIO connection timeout after 30s"
        # Partial backup still tracked
        assert len(result[0]["tables_backed_up"]) == 1


class TestBackupErrorHandlingIntegration:
    """Integration tests for error handling scenarios."""

    @pytest.mark.asyncio
    async def test_get_nonexistent_backup(self, clean_tables: AsyncSurreal):
        """Test querying for a backup that doesn't exist.

        Validates that queries for non-existent backups return empty results
        rather than errors.
        """
        db = clean_tables

        # Query for non-existent backup
        result = await db.query("SELECT * FROM backup:`nonexistent`")

        # Should return empty array, not error
        assert len(result) == 0

    @pytest.mark.asyncio
    async def test_update_nonexistent_backup(self, clean_tables: AsyncSurreal):
        """Test updating a backup that doesn't exist.

        Validates that UPDATE operations on non-existent records
        return empty results gracefully.
        """
        db = clean_tables

        # Try to update non-existent backup
        result = await db.query("""
            UPDATE backup:`doesnotexist` SET
                status = $status;
        """, {"status": "completed"})

        # Should return empty, not create a record
        assert len(result) == 0

        # Verify it wasn't created
        verify = await db.query("SELECT * FROM backup:`doesnotexist`")
        assert len(verify) == 0

    @pytest.mark.asyncio
    async def test_backup_with_empty_tables_list(self, clean_tables: AsyncSurreal):
        """Test backup with no tables backed up.

        Validates handling of edge case where a backup starts but
        no tables are successfully backed up.
        """
        db = clean_tables

        # Create backup with empty tables
        await db.query("""
            INSERT INTO backup {
                id: "emptytables",
                status: "completed",
                started_at: time::now(),
                completed_at: time::now(),
                minio_path: "backups/empty",
                tables_backed_up: [],
                size_bytes: 0
            };
        """)

        result = await db.query("SELECT * FROM backup:`emptytables`")

        assert len(result) > 0
        assert result[0]["tables_backed_up"] == []
        assert result[0]["size_bytes"] == 0
        assert result[0]["status"] == "completed"
