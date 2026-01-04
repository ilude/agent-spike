"""Notes REST API router for Mentat Studio."""

from typing import Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from compose.services.notes import (
    Note,
    NoteLink,
    NoteMeta,
    get_note_service,
)
from compose.services.surrealdb.models import AISuggestionRecord

router = APIRouter(prefix="/notes", tags=["notes"])


class CreateNoteRequest(BaseModel):
    """Request to create a new note."""

    vault_id: str
    path: str
    content: str = ""
    title: Optional[str] = None


class UpdateNoteRequest(BaseModel):
    """Request to update a note."""

    content: Optional[str] = None
    title: Optional[str] = None
    path: Optional[str] = None


class CreateLinkRequest(BaseModel):
    """Request to create a link."""

    target_id: str
    link_text: str


class NoteListResponse(BaseModel):
    """Response containing list of notes."""

    notes: list[NoteMeta]


class LinksResponse(BaseModel):
    """Response containing links."""

    outlinks: list[NoteLink]
    backlinks: list[NoteLink]


class SuggestionsResponse(BaseModel):
    """Response containing AI suggestions."""

    suggestions: list[AISuggestionRecord]


@router.get("", response_model=NoteListResponse)
async def list_notes(
    vault_id: str,
    folder_path: Optional[str] = None,
):
    """List notes in a vault, optionally filtered by folder."""
    service = get_note_service()
    notes = await service.list_notes(vault_id=vault_id, folder_path=folder_path)
    return NoteListResponse(notes=notes)


@router.post("", response_model=Note)
async def create_note(request: CreateNoteRequest):
    """Create a new note."""
    service = get_note_service()
    note = await service.create_note(
        vault_id=request.vault_id,
        path=request.path,
        content=request.content,
        title=request.title,
    )
    return note


@router.get("/{note_id}", response_model=Note)
async def get_note(note_id: str):
    """Get a note by ID."""
    service = get_note_service()
    note = await service.get_note(note_id)

    if not note:
        raise HTTPException(status_code=404, detail="Note not found")

    return note


@router.get("/by-path/{vault_id}/{path:path}", response_model=Note)
async def get_note_by_path(vault_id: str, path: str):
    """Get a note by vault and path."""
    service = get_note_service()
    note = await service.get_note_by_path(vault_id, path)

    if not note:
        raise HTTPException(status_code=404, detail="Note not found")

    return note


@router.put("/{note_id}", response_model=Note)
async def update_note(note_id: str, request: UpdateNoteRequest):
    """Update a note."""
    service = get_note_service()
    note = await service.update_note(
        note_id,
        content=request.content,
        title=request.title,
        path=request.path,
    )

    if not note:
        raise HTTPException(status_code=404, detail="Note not found")

    return note


@router.delete("/{note_id}")
async def delete_note(note_id: str):
    """Delete a note."""
    service = get_note_service()
    deleted = await service.delete_note(note_id)

    if not deleted:
        raise HTTPException(status_code=404, detail="Note not found")

    return {"status": "deleted", "id": note_id}


# =============================================================================
# Links
# =============================================================================


@router.get("/{note_id}/links", response_model=LinksResponse)
async def get_note_links(note_id: str):
    """Get outgoing and incoming links for a note."""
    service = get_note_service()

    # Verify note exists
    note = await service.get_note(note_id)
    if not note:
        raise HTTPException(status_code=404, detail="Note not found")

    outlinks = await service.get_outlinks(note_id)
    backlinks = await service.get_backlinks(note_id)

    return LinksResponse(outlinks=outlinks, backlinks=backlinks)


@router.post("/{note_id}/links", response_model=NoteLink)
async def create_link(note_id: str, request: CreateLinkRequest):
    """Create a link from this note to another."""
    service = get_note_service()

    # Verify source note exists
    note = await service.get_note(note_id)
    if not note:
        raise HTTPException(status_code=404, detail="Note not found")

    link = await service.create_link(
        source_id=note_id,
        target_id=request.target_id,
        link_text=request.link_text,
    )

    return link


@router.delete("/{note_id}/links/{link_id}")
async def delete_link(note_id: str, link_id: str):
    """Delete a link."""
    service = get_note_service()
    await service.delete_link(link_id)
    return {"status": "deleted", "id": link_id}


# =============================================================================
# AI Suggestions
# =============================================================================


@router.get("/{note_id}/suggestions", response_model=SuggestionsResponse)
async def get_suggestions(note_id: str, status: str = "pending"):
    """Get AI suggestions for a note."""
    service = get_note_service()

    # Verify note exists
    note = await service.get_note(note_id)
    if not note:
        raise HTTPException(status_code=404, detail="Note not found")

    suggestions = await service.get_suggestions(note_id, status=status)
    return SuggestionsResponse(suggestions=suggestions)


@router.post("/{note_id}/suggestions/{suggestion_id}/accept")
async def accept_suggestion(note_id: str, suggestion_id: str):
    """Accept an AI suggestion."""
    service = get_note_service()
    accepted = await service.accept_suggestion(suggestion_id)

    if not accepted:
        raise HTTPException(status_code=404, detail="Suggestion not found")

    return {"status": "accepted", "id": suggestion_id}


@router.post("/{note_id}/suggestions/{suggestion_id}/reject")
async def reject_suggestion(note_id: str, suggestion_id: str):
    """Reject an AI suggestion."""
    service = get_note_service()
    rejected = await service.reject_suggestion(suggestion_id)

    if not rejected:
        raise HTTPException(status_code=404, detail="Suggestion not found")

    return {"status": "rejected", "id": suggestion_id}


# =============================================================================
# Search
# =============================================================================


@router.get("/search/{vault_id}", response_model=NoteListResponse)
async def search_notes(vault_id: str, q: str, limit: int = 20):
    """Search notes by title or content."""
    service = get_note_service()
    notes = await service.search_notes(vault_id, q, limit=limit)
    return NoteListResponse(notes=notes)
