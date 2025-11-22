"""Projects REST API router."""

from typing import Optional

from fastapi import APIRouter, HTTPException, UploadFile, File
from pydantic import BaseModel

from compose.services.projects import (
    ProjectMeta,
    Project,
    ProjectFile,
    get_project_service,
)

router = APIRouter(prefix="/projects", tags=["projects"])


class CreateProjectRequest(BaseModel):
    """Request to create a new project."""

    name: str = "New Project"
    description: str = ""


class UpdateProjectRequest(BaseModel):
    """Request to update a project."""

    name: Optional[str] = None
    description: Optional[str] = None
    custom_instructions: Optional[str] = None


class ProjectListResponse(BaseModel):
    """Response containing list of projects."""

    projects: list[ProjectMeta]


class AddConversationRequest(BaseModel):
    """Request to add a conversation to a project."""

    conversation_id: str


@router.get("", response_model=ProjectListResponse)
async def list_projects():
    """List all projects (metadata only, sorted by most recent)."""
    service = get_project_service()
    projects = service.list_projects()
    return ProjectListResponse(projects=projects)


@router.post("", response_model=Project)
async def create_project(request: CreateProjectRequest):
    """Create a new project."""
    service = get_project_service()
    project = service.create_project(
        name=request.name,
        description=request.description,
    )
    return project


@router.get("/{project_id}", response_model=Project)
async def get_project(project_id: str):
    """Get a project by ID (includes all settings and file list)."""
    service = get_project_service()
    project = service.get_project(project_id)

    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    return project


@router.put("/{project_id}", response_model=Project)
async def update_project(project_id: str, request: UpdateProjectRequest):
    """Update project settings (name, description, custom instructions)."""
    service = get_project_service()
    project = service.update_project(
        project_id,
        name=request.name,
        description=request.description,
        custom_instructions=request.custom_instructions,
    )

    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    return project


@router.delete("/{project_id}")
async def delete_project(project_id: str):
    """Delete a project and all its files."""
    service = get_project_service()
    deleted = service.delete_project(project_id)

    if not deleted:
        raise HTTPException(status_code=404, detail="Project not found")

    return {"status": "deleted", "id": project_id}


@router.post("/{project_id}/conversations", response_model=Project)
async def add_conversation_to_project(
    project_id: str, request: AddConversationRequest
):
    """Add a conversation to a project."""
    service = get_project_service()
    project = service.add_conversation_to_project(
        project_id, request.conversation_id
    )

    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    return project


@router.delete("/{project_id}/conversations/{conversation_id}")
async def remove_conversation_from_project(project_id: str, conversation_id: str):
    """Remove a conversation from a project."""
    service = get_project_service()
    project = service.remove_conversation_from_project(project_id, conversation_id)

    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    return {"status": "removed", "project_id": project_id, "conversation_id": conversation_id}


@router.post("/{project_id}/files", response_model=ProjectFile)
async def upload_file(project_id: str, file: UploadFile = File(...)):
    """Upload a file to a project.

    The file will be stored and queued for processing (text extraction, RAG indexing).
    """
    service = get_project_service()

    # Check project exists
    project = service.get_project(project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    # Validate file
    if not file.filename:
        raise HTTPException(status_code=400, detail="Filename required")

    # Read file data
    file_data = await file.read()

    # Size limit: 50MB
    if len(file_data) > 50 * 1024 * 1024:
        raise HTTPException(status_code=400, detail="File too large (max 50MB)")

    # Sanitize filename
    import re
    safe_filename = re.sub(r'[^\w\-_\.]', '_', file.filename)

    # Add file to project
    file_record = service.add_file(
        project_id=project_id,
        filename=safe_filename,
        original_filename=file.filename,
        content_type=file.content_type or "application/octet-stream",
        file_data=file_data,
    )

    if not file_record:
        raise HTTPException(status_code=500, detail="Failed to save file")

    # TODO: Queue file for processing (Docling extraction, Qdrant indexing)
    # This would be an async background task

    return file_record


@router.get("/{project_id}/files/{file_id}")
async def get_file_info(project_id: str, file_id: str):
    """Get information about a specific file."""
    service = get_project_service()
    project = service.get_project(project_id)

    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    for f in project.files:
        if f.id == file_id:
            return f

    raise HTTPException(status_code=404, detail="File not found")


@router.delete("/{project_id}/files/{file_id}")
async def delete_file(project_id: str, file_id: str):
    """Delete a file from a project."""
    service = get_project_service()
    deleted = service.delete_file(project_id, file_id)

    if not deleted:
        raise HTTPException(status_code=404, detail="File not found")

    return {"status": "deleted", "project_id": project_id, "file_id": file_id}
