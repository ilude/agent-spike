"""Cache search endpoints."""

from fastapi import APIRouter, HTTPException

from api.models import CacheSearchRequest, CacheSearchResponse, CacheSearchResult
from tools.services.cache import create_qdrant_cache

router = APIRouter()


@router.post("/search", response_model=CacheSearchResponse)
async def search_cache(request: CacheSearchRequest):
    """
    Search the semantic cache using Qdrant.

    This endpoint searches cached content using semantic similarity.
    """
    try:
        # Create cache manager
        cache = create_qdrant_cache(collection_name="cached_content")

        # Perform search
        results = cache.search(
            query=request.query,
            limit=request.limit,
            filters=request.filters or {},
        )

        # Format results
        search_results = []
        for result in results:
            payload = result.get("payload", {})
            search_results.append(
                CacheSearchResult(
                    video_id=payload.get("video_id", ""),
                    score=result.get("score", 0.0),
                    title=payload.get("title"),
                    summary=payload.get("summary"),
                    tags=payload.get("tags"),
                    url=payload.get("url"),
                )
            )

        return CacheSearchResponse(
            query=request.query,
            results=search_results,
            total_found=len(results),
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Cache search failed: {str(e)}")


@router.get("/{key}")
async def get_cached_item(key: str):
    """Get a specific item from cache by key."""
    try:
        cache = create_qdrant_cache(collection_name="cached_content")

        if not cache.exists(key):
            raise HTTPException(status_code=404, detail=f"Key '{key}' not found in cache")

        data = cache.get(key)
        return {"key": key, "data": data}

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get cached item: {str(e)}")
