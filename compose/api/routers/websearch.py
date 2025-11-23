"""Web search API router."""

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel

from compose.services.websearch import (
    SearchResponse,
    get_freedium_service,
    get_search_service,
)

router = APIRouter(prefix="/search")


class FreediumRequest(BaseModel):
    """Request for Freedium article fetch."""

    url: str


class FreediumResponse(BaseModel):
    """Response with Freedium URL and content."""

    original_url: str
    freedium_url: str
    is_medium: bool
    content: str | None = None


@router.get("", response_model=SearchResponse)
async def search(
    q: str = Query(..., min_length=1, description="Search query"),
    num: int = Query(5, ge=1, le=10, description="Number of results"),
):
    """Perform a web search.

    Searches the web using available backends (Serper > Brave > DuckDuckGo).
    Returns search results with titles, URLs, and snippets.
    """
    service = get_search_service()
    return await service.search(q, num_results=num)


@router.get("/freedium", response_model=FreediumResponse)
async def check_freedium(
    url: str = Query(..., description="URL to check/convert"),
):
    """Check if URL is Medium and get Freedium version.

    Converts Medium URLs to Freedium URLs for bypassing paywalls.
    Does not fetch the article content (use POST to fetch).
    """
    service = get_freedium_service()
    is_medium = service.is_medium_url(url)

    return FreediumResponse(
        original_url=url,
        freedium_url=service.get_freedium_url(url) if is_medium else url,
        is_medium=is_medium,
    )


@router.post("/freedium", response_model=FreediumResponse)
async def fetch_via_freedium(request: FreediumRequest):
    """Fetch article content via Freedium.

    For Medium articles, fetches the content through Freedium to bypass paywall.
    For non-Medium URLs, returns the URL unchanged without fetching.
    """
    service = get_freedium_service()
    is_medium = service.is_medium_url(request.url)

    if not is_medium:
        return FreediumResponse(
            original_url=request.url,
            freedium_url=request.url,
            is_medium=False,
        )

    content = await service.fetch_article(request.url)

    return FreediumResponse(
        original_url=request.url,
        freedium_url=service.get_freedium_url(request.url),
        is_medium=True,
        content=content,
    )
