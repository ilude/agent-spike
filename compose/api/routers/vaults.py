"""Vaults REST API router."""

from typing import Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from compose.services.vaults import (
    Vault,
    VaultMeta,
    get_vault_service,
)
from compose.services.surrealdb.models import FileTreeNode

router = APIRouter(prefix="/vaults", tags=["vaults"])


class CreateVaultRequest(BaseModel):
    """Request to create a new vault."""

    name: str
    storage_type: str = "minio"
    settings: Optional[dict] = None


class UpdateVaultRequest(BaseModel):
    """Request to update a vault."""

    name: Optional[str] = None
    settings: Optional[dict] = None


class VaultListResponse(BaseModel):
    """Response containing list of vaults."""

    vaults: list[VaultMeta]


class FileTreeResponse(BaseModel):
    """Response containing file tree structure."""

    tree: list[FileTreeNode]


@router.get("", response_model=VaultListResponse)
async def list_vaults():
    """List all vaults."""
    service = get_vault_service()
    vaults = await service.list_vaults()
    return VaultListResponse(vaults=vaults)


@router.post("", response_model=Vault)
async def create_vault(request: CreateVaultRequest):
    """Create a new vault."""
    service = get_vault_service()
    vault = await service.create_vault(
        name=request.name,
        storage_type=request.storage_type,
        settings=request.settings,
    )
    return vault


@router.get("/{vault_id}", response_model=Vault)
async def get_vault(vault_id: str):
    """Get a vault by ID."""
    service = get_vault_service()
    vault = await service.get_vault(vault_id)

    if not vault:
        raise HTTPException(status_code=404, detail="Vault not found")

    return vault


@router.get("/by-slug/{slug}", response_model=Vault)
async def get_vault_by_slug(slug: str):
    """Get a vault by slug."""
    service = get_vault_service()
    vault = await service.get_vault_by_slug(slug)

    if not vault:
        raise HTTPException(status_code=404, detail="Vault not found")

    return vault


@router.put("/{vault_id}", response_model=Vault)
async def update_vault(vault_id: str, request: UpdateVaultRequest):
    """Update a vault."""
    service = get_vault_service()
    vault = await service.update_vault(
        vault_id,
        name=request.name,
        settings=request.settings,
    )

    if not vault:
        raise HTTPException(status_code=404, detail="Vault not found")

    return vault


@router.delete("/{vault_id}")
async def delete_vault(vault_id: str):
    """Delete a vault and all its contents."""
    service = get_vault_service()
    deleted = await service.delete_vault(vault_id)

    if not deleted:
        raise HTTPException(status_code=404, detail="Vault not found")

    return {"status": "deleted", "id": vault_id}


@router.get("/{vault_id}/tree", response_model=FileTreeResponse)
async def get_file_tree(vault_id: str):
    """Get file tree structure for a vault."""
    service = get_vault_service()

    # Verify vault exists
    vault = await service.get_vault(vault_id)
    if not vault:
        raise HTTPException(status_code=404, detail="Vault not found")

    tree = await service.get_file_tree(vault_id)
    return FileTreeResponse(tree=tree)
