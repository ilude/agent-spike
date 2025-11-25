"""Artifacts REST API router."""

from typing import Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from compose.services.artifacts import (
    ArtifactMeta,
    Artifact,
    get_artifact_service,
)

router = APIRouter(prefix="/artifacts", tags=["artifacts"])


class CreateArtifactRequest(BaseModel):
    """Request to create a new artifact."""

    title: str = "Untitled"
    content: str = ""
    artifact_type: str = "document"
    language: Optional[str] = None
    conversation_id: Optional[str] = None
    project_id: Optional[str] = None


class UpdateArtifactRequest(BaseModel):
    """Request to update an artifact."""

    title: Optional[str] = None
    content: Optional[str] = None
    artifact_type: Optional[str] = None
    language: Optional[str] = None


class ArtifactListResponse(BaseModel):
    """Response containing list of artifacts."""

    artifacts: list[ArtifactMeta]


class LinkRequest(BaseModel):
    """Request to link artifact to conversation or project."""

    conversation_id: Optional[str] = None
    project_id: Optional[str] = None


@router.get("", response_model=ArtifactListResponse)
async def list_artifacts(
    conversation_id: Optional[str] = None,
    project_id: Optional[str] = None,
):
    """List all artifacts, optionally filtered by conversation or project."""
    service = get_artifact_service()
    artifacts = service.list_artifacts(
        conversation_id=conversation_id,
        project_id=project_id,
    )
    return ArtifactListResponse(artifacts=artifacts)


@router.post("", response_model=Artifact)
async def create_artifact(request: CreateArtifactRequest):
    """Create a new artifact."""
    service = get_artifact_service()
    artifact = service.create_artifact(
        title=request.title,
        content=request.content,
        artifact_type=request.artifact_type,
        language=request.language,
        conversation_id=request.conversation_id,
        project_id=request.project_id,
    )
    return artifact


@router.get("/{artifact_id}", response_model=Artifact)
async def get_artifact(artifact_id: str):
    """Get an artifact by ID."""
    service = get_artifact_service()
    artifact = service.get_artifact(artifact_id)

    if not artifact:
        raise HTTPException(status_code=404, detail="Artifact not found")

    return artifact


@router.put("/{artifact_id}", response_model=Artifact)
async def update_artifact(artifact_id: str, request: UpdateArtifactRequest):
    """Update an artifact."""
    service = get_artifact_service()
    artifact = service.update_artifact(
        artifact_id,
        title=request.title,
        content=request.content,
        artifact_type=request.artifact_type,
        language=request.language,
    )

    if not artifact:
        raise HTTPException(status_code=404, detail="Artifact not found")

    return artifact


@router.delete("/{artifact_id}")
async def delete_artifact(artifact_id: str):
    """Delete an artifact."""
    service = get_artifact_service()
    deleted = service.delete_artifact(artifact_id)

    if not deleted:
        raise HTTPException(status_code=404, detail="Artifact not found")

    return {"status": "deleted", "id": artifact_id}


@router.post("/{artifact_id}/link", response_model=Artifact)
async def link_artifact(artifact_id: str, request: LinkRequest):
    """Link an artifact to a conversation and/or project."""
    service = get_artifact_service()
    artifact = service.get_artifact(artifact_id)

    if not artifact:
        raise HTTPException(status_code=404, detail="Artifact not found")

    if request.conversation_id:
        artifact = service.link_to_conversation(artifact_id, request.conversation_id)

    if request.project_id:
        artifact = service.link_to_project(artifact_id, request.project_id)

    return artifact
