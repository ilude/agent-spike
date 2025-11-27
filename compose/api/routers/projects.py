"""Projects REST API router."""

import asyncio
from typing import Optional

from fastapi import APIRouter, HTTPException, UploadFile, File, BackgroundTasks
from pydantic import BaseModel

from compose.services.projects import (
    ProjectMeta,
    Project,
    ProjectFile,
    get_project_service,
)
# TEMPORARILY DISABLED: file_processor module not yet implemented
# from compose.services.file_processor import (
#     process_and_index_file,
#     search_project_files,
#     delete_file_from_index,
# )

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


async def process_file_background(
    project_id: str,
    file_id: str,
    file_path: str,
    filename: str,
    content_type: str,
):
    """Background task to process and index uploaded file."""
    from pathlib import Path

    service = get_project_service()

    try:
        result = await process_and_index_file(
            project_id=project_id,
            file_id=file_id,
            file_path=Path(file_path),
            filename=filename,
            content_type=content_type,
        )

        # Update file record with processing status
        service.mark_file_processed(
            project_id=project_id,
            file_id=file_id,
            qdrant_indexed=result.get("success", False),
            error=result.get("error"),
        )

        if result.get("success"):
            print(f"Indexed file {filename}: {result.get('chunks_indexed')} chunks")
        else:
            print(f"Failed to index file {filename}: {result.get('error')}")

    except Exception as e:
        print(f"Background file processing error: {e}")
        service.mark_file_processed(
            project_id=project_id,
            file_id=file_id,
            qdrant_indexed=False,
            error=str(e),
        )


@router.post("/{project_id}/files", response_model=ProjectFile)
async def upload_file(
    project_id: str,
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
):
    """Upload a file to a project.

    The file will be stored and processed in the background (text extraction, RAG indexing).
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

    # Get file path for processing
    file_path = service.get_file_path(project_id, file_record.id)

    # Queue background processing
    if file_path:
        background_tasks.add_task(
            process_file_background,
            project_id=project_id,
            file_id=file_record.id,
            file_path=str(file_path),
            filename=safe_filename,
            content_type=file.content_type or "application/octet-stream",
        )

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
    """Delete a file from a project and remove from index."""
    service = get_project_service()
    deleted = service.delete_file(project_id, file_id)

    if not deleted:
        raise HTTPException(status_code=404, detail="File not found")

    # Remove from Qdrant index
    delete_file_from_index(project_id, file_id)

    return {"status": "deleted", "project_id": project_id, "file_id": file_id}


class SearchFilesRequest(BaseModel):
    """Request to search project files."""

    query: str
    limit: int = 5


class SearchResult(BaseModel):
    """A single search result."""

    score: float
    text: str
    filename: str
    file_id: str
    chunk_index: int


class SearchFilesResponse(BaseModel):
    """Search results response."""

    results: list[SearchResult]


@router.post("/{project_id}/search", response_model=SearchFilesResponse)
async def search_files(project_id: str, request: SearchFilesRequest):
    """Search project files using semantic search."""
    service = get_project_service()

    # Check project exists
    project = service.get_project(project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    results = await search_project_files(
        project_id=project_id,
        query=request.query,
        limit=request.limit,
    )

    return SearchFilesResponse(results=[SearchResult(**r) for r in results])
