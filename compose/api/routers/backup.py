"""Backup API endpoints for SurrealDB data management."""

from typing import Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from compose.services.backup import BackupMeta, BackupStatus, get_backup_service

router = APIRouter(prefix="/backup", tags=["backup"])


class BackupResponse(BaseModel):
    """Response model for backup operations."""

    success: bool
    message: str
    backup: Optional[BackupMeta] = None


class RestoreResponse(BaseModel):
    """Response model for restore operations."""

    success: bool
    message: str


@router.get("", response_model=list[BackupMeta])
async def list_backups():
    """List all backups.

    Returns:
        List of backup metadata records.
    """
    service = get_backup_service()
    return await service.list_backups()


@router.post("", response_model=BackupResponse)
async def start_backup():
    """Start a new backup job.

    Creates a backup of all SurrealDB tables and stores them in MinIO.
    The backup runs in the background - use GET /backup/{backup_id} to
    check status.

    Returns:
        Backup metadata with pending status.
    """
    service = get_backup_service()
    backup = await service.start_backup()
    return BackupResponse(
        success=True,
        message="Backup job started",
        backup=backup,
    )


@router.get("/{backup_id}", response_model=BackupMeta)
async def get_backup(backup_id: str):
    """Get backup status and details.

    Args:
        backup_id: ID of the backup.

    Returns:
        Backup metadata.

    Raises:
        HTTPException: If backup not found.
    """
    service = get_backup_service()
    backup = await service.get_backup(backup_id)
    if not backup:
        raise HTTPException(status_code=404, detail=f"Backup {backup_id} not found")
    return backup


@router.post("/{backup_id}/restore", response_model=RestoreResponse)
async def restore_backup(backup_id: str):
    """Restore data from a backup.

    WARNING: This will DELETE all existing data in the backed-up tables
    and replace it with the backup data.

    Args:
        backup_id: ID of the backup to restore.

    Returns:
        Restore operation result.

    Raises:
        HTTPException: If backup not found or restore fails.
    """
    service = get_backup_service()
    backup = await service.get_backup(backup_id)
    if not backup:
        raise HTTPException(status_code=404, detail=f"Backup {backup_id} not found")

    if backup.status != BackupStatus.COMPLETED:
        raise HTTPException(
            status_code=400,
            detail=f"Cannot restore incomplete backup with status: {backup.status}",
        )

    success = await service.restore_backup(backup_id)
    if not success:
        raise HTTPException(status_code=500, detail="Restore operation failed")

    return RestoreResponse(
        success=True,
        message=f"Restored {len(backup.tables_backed_up)} tables from backup {backup_id}",
    )


@router.delete("/{backup_id}", response_model=RestoreResponse)
async def delete_backup(backup_id: str):
    """Delete a backup.

    Removes the backup record from SurrealDB and deletes all backup
    files from MinIO.

    Args:
        backup_id: ID of the backup to delete.

    Returns:
        Deletion result.

    Raises:
        HTTPException: If backup not found or deletion fails.
    """
    service = get_backup_service()
    backup = await service.get_backup(backup_id)
    if not backup:
        raise HTTPException(status_code=404, detail=f"Backup {backup_id} not found")

    success = await service.delete_backup(backup_id)
    if not success:
        raise HTTPException(status_code=500, detail="Delete operation failed")

    return RestoreResponse(
        success=True,
        message=f"Deleted backup {backup_id}",
    )
