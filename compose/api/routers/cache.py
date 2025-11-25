"""Cache search endpoints using SurrealDB and MinIO."""

from fastapi import APIRouter, HTTPException

from compose.api.models import CacheSearchRequest, CacheSearchResponse, CacheSearchResult
# from compose.services.surrealdb import semantic_search  # OLD: inline RAG
from compose.services.rag import SurrealDBRAG

router = APIRouter()


@router.post("/search", response_model=CacheSearchResponse)
async def search_cache(request: CacheSearchRequest):
    """
    Search the semantic cache using SurrealDB vector search.

    This endpoint searches cached content using semantic similarity.
    """
    try:
        # NEW: Use SurrealDBRAG service for semantic search
        rag = SurrealDBRAG()
        results = await rag.retrieve_context(
            query=request.query,
            limit=request.limit
        )

        # Format results
        search_results = []
        for r in results:
            search_results.append(
                CacheSearchResult(
                    video_id=r.get("video_id", ""),
                    title=r.get("title", "Unknown"),
                    score=r.get("score", 0.0),
                    url=r.get("url", ""),
                )
            )

        return CacheSearchResponse(
            query=request.query,
            results=search_results,
            total_found=len(search_results),
        )

        # OLD: Placeholder (commented out - delete in Phase 4)
        # # For semantic search, we would need embeddings
        # # This is a simplified version that uses SurrealDB's vector search
        # # In production, you'd generate embeddings from the query first
        #
        # # Since we don't have a query embedding here, return empty results
        # # Real implementation would:
        # # 1. Generate embedding from request.query
        # # 2. Call semantic_search(embedding, limit=request.limit)
        # # 3. Format and return results

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Cache search failed: {str(e)}")


@router.get("/{key}")
async def get_cached_item(key: str):
    """Get a specific item from cache by key (video lookup from SurrealDB)."""
    try:
        from compose.services.surrealdb import get_video

        # Extract video_id from cache key format: "youtube:video:{video_id}"
        if not key.startswith("youtube:video:"):
            raise HTTPException(status_code=404, detail=f"Invalid cache key format: {key}")

        video_id = key.split(":")[-1]
        video = await get_video(video_id)

        if not video:
            raise HTTPException(status_code=404, detail=f"Key '{key}' not found in cache")

        return {
            "key": key,
            "data": {
                "video_id": video.video_id,
                "url": video.url,
                "title": video.title,
                "channel_id": video.channel_id,
                "channel_name": video.channel_name,
            }
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get cached item: {str(e)}")
