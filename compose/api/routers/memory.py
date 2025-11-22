"""Memory API router for global memory management."""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from compose.services.memory import MemoryItem, get_memory_service

router = APIRouter(prefix="/memory")


class AddMemoryRequest(BaseModel):
    """Request body for adding a memory."""

    content: str
    category: str = "general"
    source_conversation_id: str | None = None


class UpdateMemoryRequest(BaseModel):
    """Request body for updating a memory."""

    content: str | None = None
    category: str | None = None
    relevance_score: float | None = None


class MemoryListResponse(BaseModel):
    """Response for listing memories."""

    memories: list[MemoryItem]
    count: int


class DeleteResponse(BaseModel):
    """Response for delete operations."""

    success: bool
    message: str


class ClearResponse(BaseModel):
    """Response for clear operation."""

    deleted_count: int
    message: str


@router.get("", response_model=MemoryListResponse)
async def list_memories(category: str | None = None):
    """List all memories, optionally filtered by category."""
    service = get_memory_service()
    memories = service.list_memories(category=category)
    return MemoryListResponse(memories=memories, count=len(memories))


@router.post("", response_model=MemoryItem)
async def add_memory(request: AddMemoryRequest):
    """Add a new memory."""
    service = get_memory_service()
    memory = service.add_memory(
        content=request.content,
        category=request.category,
        source_conversation_id=request.source_conversation_id,
    )
    return memory


@router.get("/search", response_model=MemoryListResponse)
async def search_memories(q: str):
    """Search memories by content."""
    service = get_memory_service()
    memories = service.search_memories(q)
    return MemoryListResponse(memories=memories, count=len(memories))


@router.get("/{memory_id}", response_model=MemoryItem)
async def get_memory(memory_id: str):
    """Get a memory by ID."""
    service = get_memory_service()
    memory = service.get_memory(memory_id)
    if memory is None:
        raise HTTPException(status_code=404, detail="Memory not found")
    return memory


@router.put("/{memory_id}", response_model=MemoryItem)
async def update_memory(memory_id: str, request: UpdateMemoryRequest):
    """Update a memory."""
    service = get_memory_service()
    memory = service.update_memory(
        memory_id=memory_id,
        content=request.content,
        category=request.category,
        relevance_score=request.relevance_score,
    )
    if memory is None:
        raise HTTPException(status_code=404, detail="Memory not found")
    return memory


@router.delete("/{memory_id}", response_model=DeleteResponse)
async def delete_memory(memory_id: str):
    """Delete a memory."""
    service = get_memory_service()
    deleted = service.delete_memory(memory_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Memory not found")
    return DeleteResponse(success=True, message="Memory deleted")


@router.delete("", response_model=ClearResponse)
async def clear_all_memories():
    """Clear all memories."""
    service = get_memory_service()
    count = service.clear_all()
    return ClearResponse(deleted_count=count, message=f"Deleted {count} memories")
