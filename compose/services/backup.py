"""Backup service for SurrealDB data to MinIO.

Exports all SurrealDB tables to JSON and stores them in MinIO with
metadata tracking in SurrealDB.
"""

import asyncio
import json
import logging
from datetime import datetime, timezone
from enum import Enum
from typing import Optional
from uuid import uuid4

from pydantic import BaseModel

from compose.services.minio.factory import create_minio_client
from compose.services.surrealdb.driver import execute_query

logger = logging.getLogger(__name__)

# Tables to backup
BACKUP_TABLES = [
    "conversation",
    "message",
    "project",
    "project_file",
    "project_conversation",
    "artifact",
    "video",
    "channel",
    "topic",
]


class BackupStatus(str, Enum):
    """Status of a backup job."""

    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"


class BackupMeta(BaseModel):
    """Metadata for a backup job."""

    id: str
    status: BackupStatus
    started_at: datetime
    completed_at: Optional[datetime] = None
    tables_backed_up: list[str] = []
    minio_path: str
    size_bytes: int = 0
    error: Optional[str] = None


class BackupService:
    """Service for managing SurrealDB backups to MinIO."""

    def __init__(self):
        """Initialize backup service."""
        self._minio = None

    @property
    def minio(self):
        """Lazy-load MinIO client."""
        if self._minio is None:
            self._minio = create_minio_client()
        return self._minio

    async def list_backups(self) -> list[BackupMeta]:
        """List all backup records.

        Returns:
            List of backup metadata records.
        """
        result = await execute_query("SELECT * FROM backup ORDER BY started_at DESC")
        backups = []
        for record in result:
            try:
                # Handle SurrealDB record ID format
                backup_id = str(record.get("id", ""))
                if ":" in backup_id:
                    backup_id = backup_id.split(":")[1]

                backups.append(
                    BackupMeta(
                        id=backup_id,
                        status=BackupStatus(record.get("status", "pending")),
                        started_at=record.get("started_at", datetime.now(timezone.utc)),
                        completed_at=record.get("completed_at"),
                        tables_backed_up=record.get("tables_backed_up", []),
                        minio_path=record.get("minio_path", ""),
                        size_bytes=record.get("size_bytes", 0),
                        error=record.get("error"),
                    )
                )
            except Exception as e:
                logger.warning(f"Failed to parse backup record: {e}")
                continue
        return backups

    async def start_backup(self) -> BackupMeta:
        """Start a new backup job.

        Creates backup record and starts background task.

        Returns:
            Backup metadata with pending status.
        """
        backup_id = str(uuid4())
        timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
        minio_path = f"backups/{timestamp}"

        # Create backup record
        backup_meta = BackupMeta(
            id=backup_id,
            status=BackupStatus.PENDING,
            started_at=datetime.now(timezone.utc),
            minio_path=minio_path,
        )

        # Store in SurrealDB with record ID
        await execute_query(
            f"CREATE backup:`{backup_id}` SET status = $status, started_at = $started_at, minio_path = $minio_path, tables_backed_up = [], size_bytes = 0",
            {
                "status": backup_meta.status.value,
                "started_at": backup_meta.started_at.isoformat(),
                "minio_path": minio_path,
            },
        )

        # Start background task with exception logging
        task = asyncio.create_task(self._run_backup(backup_id, minio_path))
        task.add_done_callback(self._task_done_callback)

        return backup_meta

    def _task_done_callback(self, task: asyncio.Task) -> None:
        """Log any exceptions from background tasks."""
        try:
            exc = task.exception()
            if exc:
                logger.error(f"Backup task failed with exception: {exc}")
        except asyncio.CancelledError:
            logger.warning("Backup task was cancelled")

    async def _run_backup(self, backup_id: str, minio_path: str) -> None:
        """Execute the backup process.

        Args:
            backup_id: ID of the backup job.
            minio_path: Path in MinIO to store backup files.
        """
        logger.info(f"Starting backup task for {backup_id}")
        tables_backed_up = []
        total_size = 0

        try:
            # Update status to in_progress
            await execute_query(
                f"UPDATE backup:`{backup_id}` SET status = $status",
                {"status": BackupStatus.IN_PROGRESS.value},
            )

            # Backup each table
            for table in BACKUP_TABLES:
                try:
                    result = await execute_query(f"SELECT * FROM {table}")
                    if result:
                        # Serialize and upload to MinIO
                        json_data = json.dumps(result, default=str)
                        json_bytes = json_data.encode("utf-8")
                        total_size += len(json_bytes)

                        object_path = f"{minio_path}/{table}.json"
                        self.minio.put_json(object_path, result)
                        tables_backed_up.append(table)
                        logger.info(f"Backed up {table}: {len(result)} records")
                except Exception as e:
                    logger.warning(f"Failed to backup table {table}: {e}")

            # Create manifest
            manifest = {
                "backup_id": backup_id,
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "tables": tables_backed_up,
                "total_size_bytes": total_size,
            }
            self.minio.put_json(f"{minio_path}/manifest.json", manifest)

            # Update backup record as completed
            await execute_query(
                f"UPDATE backup:`{backup_id}` SET status = $status, completed_at = $completed_at, tables_backed_up = $tables, size_bytes = $size",
                {
                    "status": BackupStatus.COMPLETED.value,
                    "completed_at": datetime.now(timezone.utc).isoformat(),
                    "tables": tables_backed_up,
                    "size": total_size,
                },
            )
            logger.info(f"Backup {backup_id} completed: {len(tables_backed_up)} tables")

        except Exception as e:
            logger.error(f"Backup {backup_id} failed: {e}")
            await execute_query(
                f"UPDATE backup:`{backup_id}` SET status = $status, completed_at = $completed_at, error = $error",
                {
                    "status": BackupStatus.FAILED.value,
                    "completed_at": datetime.now(timezone.utc).isoformat(),
                    "error": str(e),
                },
            )

    async def get_backup(self, backup_id: str) -> Optional[BackupMeta]:
        """Get backup metadata by ID.

        Args:
            backup_id: ID of the backup.

        Returns:
            Backup metadata if found, None otherwise.
        """
        result = await execute_query(f"SELECT * FROM backup:`{backup_id}`")
        if not result:
            return None

        record = result[0]
        record_id = str(record.get("id", ""))
        if ":" in record_id:
            record_id = record_id.split(":")[1]

        return BackupMeta(
            id=record_id,
            status=BackupStatus(record.get("status", "pending")),
            started_at=record.get("started_at", datetime.now(timezone.utc)),
            completed_at=record.get("completed_at"),
            tables_backed_up=record.get("tables_backed_up", []),
            minio_path=record.get("minio_path", ""),
            size_bytes=record.get("size_bytes", 0),
            error=record.get("error"),
        )

    async def restore_backup(self, backup_id: str) -> bool:
        """Restore data from a backup.

        Args:
            backup_id: ID of the backup to restore.

        Returns:
            True if restore successful, False otherwise.
        """
        backup = await self.get_backup(backup_id)
        if not backup:
            logger.error(f"Backup {backup_id} not found")
            return False

        if backup.status != BackupStatus.COMPLETED:
            logger.error(f"Cannot restore incomplete backup: {backup.status}")
            return False

        try:
            # Read manifest
            manifest_path = f"{backup.minio_path}/manifest.json"
            manifest = self.minio.get_json(manifest_path)
            tables = manifest.get("tables", [])

            # Restore each table
            for table in tables:
                try:
                    object_path = f"{backup.minio_path}/{table}.json"
                    records = self.minio.get_json(object_path)

                    # Delete existing records in table
                    await execute_query(f"DELETE {table}")

                    # Insert backup records
                    for record in records:
                        # Remove SurrealDB internal fields for clean insert
                        clean_record = {
                            k: v
                            for k, v in record.items()
                            if not k.startswith("_") and k != "id"
                        }

                        # Get original ID if present
                        original_id = record.get("id", "")
                        if isinstance(original_id, str) and ":" in original_id:
                            original_id = original_id.split(":")[1]

                        # Create with original ID
                        if original_id:
                            await execute_query(
                                f"CREATE {table}:`{original_id}` CONTENT $data",
                                {"data": clean_record},
                            )
                        else:
                            await execute_query(
                                f"CREATE {table} CONTENT $data",
                                {"data": clean_record},
                            )

                    logger.info(f"Restored {table}: {len(records)} records")

                except Exception as e:
                    logger.error(f"Failed to restore table {table}: {e}")
                    return False

            logger.info(f"Restore from backup {backup_id} completed")
            return True

        except Exception as e:
            logger.error(f"Restore failed: {e}")
            return False

    async def delete_backup(self, backup_id: str) -> bool:
        """Delete a backup and its files from MinIO.

        Args:
            backup_id: ID of the backup to delete.

        Returns:
            True if deletion successful, False otherwise.
        """
        backup = await self.get_backup(backup_id)
        if not backup:
            logger.error(f"Backup {backup_id} not found")
            return False

        try:
            # Delete files from MinIO
            objects = self.minio.list_objects(prefix=backup.minio_path)
            for obj in objects:
                self.minio.delete(obj.object_name)
                logger.debug(f"Deleted {obj.object_name}")

            # Delete backup record from SurrealDB
            await execute_query(f"DELETE backup:`{backup_id}`")

            logger.info(f"Deleted backup {backup_id}")
            return True

        except Exception as e:
            logger.error(f"Failed to delete backup {backup_id}: {e}")
            return False


# Singleton instance
_backup_service: Optional[BackupService] = None


def get_backup_service() -> BackupService:
    """Get or create backup service singleton.

    Returns:
        BackupService instance.
    """
    global _backup_service
    if _backup_service is None:
        _backup_service = BackupService()
    return _backup_service