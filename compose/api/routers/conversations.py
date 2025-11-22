"""Conversations REST API router."""

from typing import Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from compose.services.conversations import (
    ConversationMeta,
    Conversation,
    get_conversation_service,
)

router = APIRouter(prefix="/conversations", tags=["conversations"])


class CreateConversationRequest(BaseModel):
    """Request to create a new conversation."""

    title: str = "New conversation"
    model: str = ""


class UpdateConversationRequest(BaseModel):
    """Request to update a conversation."""

    title: Optional[str] = None
    model: Optional[str] = None


class ConversationListResponse(BaseModel):
    """Response containing list of conversations."""

    conversations: list[ConversationMeta]


class SearchRequest(BaseModel):
    """Search request."""

    query: str


@router.get("", response_model=ConversationListResponse)
async def list_conversations():
    """List all conversations (metadata only, sorted by most recent)."""
    service = get_conversation_service()
    conversations = service.list_conversations()
    return ConversationListResponse(conversations=conversations)


@router.post("", response_model=Conversation)
async def create_conversation(request: CreateConversationRequest):
    """Create a new conversation."""
    service = get_conversation_service()
    conversation = service.create_conversation(
        title=request.title,
        model=request.model,
    )
    return conversation


@router.get("/search", response_model=ConversationListResponse)
async def search_conversations(q: str):
    """Search conversations by title and content."""
    if not q or len(q) < 2:
        raise HTTPException(
            status_code=400, detail="Search query must be at least 2 characters"
        )

    service = get_conversation_service()
    results = service.search_conversations(q)
    return ConversationListResponse(conversations=results)


@router.get("/{conversation_id}", response_model=Conversation)
async def get_conversation(conversation_id: str):
    """Get a conversation by ID (includes all messages)."""
    service = get_conversation_service()
    conversation = service.get_conversation(conversation_id)

    if not conversation:
        raise HTTPException(status_code=404, detail="Conversation not found")

    return conversation


@router.put("/{conversation_id}", response_model=Conversation)
async def update_conversation(
    conversation_id: str, request: UpdateConversationRequest
):
    """Update conversation metadata (title, model)."""
    service = get_conversation_service()
    conversation = service.update_conversation(
        conversation_id,
        title=request.title,
        model=request.model,
    )

    if not conversation:
        raise HTTPException(status_code=404, detail="Conversation not found")

    return conversation


@router.delete("/{conversation_id}")
async def delete_conversation(conversation_id: str):
    """Delete a conversation."""
    service = get_conversation_service()
    deleted = service.delete_conversation(conversation_id)

    if not deleted:
        raise HTTPException(status_code=404, detail="Conversation not found")

    return {"status": "deleted", "id": conversation_id}


class GenerateTitleRequest(BaseModel):
    """Request to generate a title."""

    message: str


class GenerateTitleResponse(BaseModel):
    """Response with generated title."""

    title: str


@router.post("/generate-title", response_model=GenerateTitleResponse)
async def generate_title(request: GenerateTitleRequest):
    """Generate a title for a conversation based on the first message."""
    if not request.message or len(request.message) < 3:
        raise HTTPException(
            status_code=400, detail="Message must be at least 3 characters"
        )

    service = get_conversation_service()
    title = await service.generate_title(request.message)
    return GenerateTitleResponse(title=title)
