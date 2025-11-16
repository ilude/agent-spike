"""Request and response models for the API."""

from pydantic import BaseModel, HttpUrl, Field


class AnalyzeVideoRequest(BaseModel):
    """Request to analyze a YouTube video."""

    url: HttpUrl
    fetch_metadata: bool = Field(
        default=False,
        description="Fetch fresh metadata from YouTube API (uses quota). If False, uses archive if available.",
    )


class AnalyzeVideoResponse(BaseModel):
    """Response from YouTube video analysis."""

    video_id: str
    tags: list[str]
    summary: str
    metadata: dict | None = None
    cached: bool = Field(
        description="True if data was retrieved from archive/cache without API calls"
    )


class CacheSearchRequest(BaseModel):
    """Request to search the semantic cache."""

    query: str
    limit: int = Field(default=5, ge=1, le=100, description="Number of results to return")
    filters: dict | None = Field(
        default=None, description="Optional filters to apply to search"
    )


class CacheSearchResult(BaseModel):
    """Single search result from cache."""

    video_id: str
    score: float
    title: str | None = None
    summary: str | None = None
    tags: list[str] | None = None
    url: str | None = None


class CacheSearchResponse(BaseModel):
    """Response from cache search."""

    query: str
    results: list[CacheSearchResult]
    total_found: int


class HealthCheckResponse(BaseModel):
    """Health check response."""

    status: str
    checks: dict[str, dict]
