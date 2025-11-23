"""Writing styles API endpoints."""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from compose.services.styles import WritingStyle, get_styles_service

router = APIRouter(prefix="/styles", tags=["styles"])


class StylesListResponse(BaseModel):
    """Response for listing all styles."""

    styles: list[WritingStyle]


@router.get("", response_model=StylesListResponse)
async def list_styles():
    """List all available writing styles.

    Returns all preset writing styles with their names, descriptions,
    and system prompt modifiers.
    """
    service = get_styles_service()
    return StylesListResponse(styles=service.list_styles())


@router.get("/{style_id}", response_model=WritingStyle)
async def get_style(style_id: str):
    """Get a specific writing style by ID.

    Args:
        style_id: The style identifier (e.g., 'concise', 'detailed', 'formal')

    Returns:
        The writing style definition

    Raises:
        404: Style not found
    """
    service = get_styles_service()
    style = service.get_style(style_id)
    if not style:
        raise HTTPException(status_code=404, detail=f"Style '{style_id}' not found")
    return style
