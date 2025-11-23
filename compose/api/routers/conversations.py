"""Conversations REST API router."""

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel

from compose.services.conversations import (
    ConversationMeta,
    Conversation,
    get_conversation_service,
)
from compose.services.auth.models import User
from compose.api.routers.auth import get_current_user

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
async def list_conversations(user: User = Depends(get_current_user)):
    """List user's conversations (metadata only, sorted by most recent)."""
    service = get_conversation_service()
    conversations = await service.list_conversations(user_id=user.id)
    return ConversationListResponse(conversations=conversations)


@router.post("", response_model=Conversation)
async def create_conversation(
    request: CreateConversationRequest,
    user: User = Depends(get_current_user),
):
    """Create a new conversation for the current user."""
    service = get_conversation_service()
    conversation = await service.create_conversation(
        title=request.title,
        model=request.model,
        user_id=user.id,
    )
    return conversation


@router.get("/search", response_model=ConversationListResponse)
async def search_conversations(q: str, user: User = Depends(get_current_user)):
    """Search user's conversations by title and content."""
    if not q or len(q) < 2:
        raise HTTPException(
            status_code=400, detail="Search query must be at least 2 characters"
        )

    service = get_conversation_service()
    results = await service.search_conversations(q, user_id=user.id)
    return ConversationListResponse(conversations=results)


@router.get("/{conversation_id}", response_model=Conversation)
async def get_conversation(
    conversation_id: str,
    user: User = Depends(get_current_user),
):
    """Get a conversation by ID (includes all messages).

    User must own the conversation or be admin to access it.
    """
    service = get_conversation_service()
    conversation = await service.get_conversation(conversation_id)

    if not conversation:
        raise HTTPException(status_code=404, detail="Conversation not found")

    # Check ownership - conversation must belong to user (or user is admin)
    conv_user_id = await service.get_conversation_user_id(conversation_id)
    if conv_user_id and conv_user_id != user.id and not user.is_admin():
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied to this conversation",
        )

    return conversation


@router.put("/{conversation_id}", response_model=Conversation)
async def update_conversation(
    conversation_id: str,
    request: UpdateConversationRequest,
    user: User = Depends(get_current_user),
):
    """Update conversation metadata (title, model).

    User must own the conversation or be admin to update it.
    """
    service = get_conversation_service()

    # Check ownership first
    conv_user_id = await service.get_conversation_user_id(conversation_id)
    if conv_user_id and conv_user_id != user.id and not user.is_admin():
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied to this conversation",
        )

    conversation = await service.update_conversation(
        conversation_id,
        title=request.title,
        model=request.model,
    )

    if not conversation:
        raise HTTPException(status_code=404, detail="Conversation not found")

    return conversation


@router.delete("/{conversation_id}")
async def delete_conversation(
    conversation_id: str,
    user: User = Depends(get_current_user),
):
    """Delete a conversation.

    User must own the conversation or be admin to delete it.
    """
    service = get_conversation_service()

    # Check ownership first
    conv_user_id = await service.get_conversation_user_id(conversation_id)
    if conv_user_id and conv_user_id != user.id and not user.is_admin():
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied to this conversation",
        )

    deleted = await service.delete_conversation(conversation_id)

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


class GenerateFilenameRequest(BaseModel):
    """Request to generate a filename."""

    content: str
    model: str = "ollama:llama3.2"
    content_type: str = "conversation"  # "message" or "conversation"
    prompt: Optional[str] = None  # Custom prompt template


class GenerateFilenameResponse(BaseModel):
    """Response with generated filename."""

    filename: str


@router.post("/generate-filename", response_model=GenerateFilenameResponse)
async def generate_filename(request: GenerateFilenameRequest):
    """Generate a descriptive filename for content export."""
    if not request.content or len(request.content) < 10:
        raise HTTPException(
            status_code=400, detail="Content must be at least 10 characters"
        )

    service = get_conversation_service()
    filename = await service.generate_filename(
        content=request.content,
        model=request.model,
        content_type=request.content_type,
        custom_prompt=request.prompt,
    )
    return GenerateFilenameResponse(filename=filename)
