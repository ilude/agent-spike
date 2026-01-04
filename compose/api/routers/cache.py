"""Cache search endpoints using SurrealDB and MinIO.

Provides two search modes:
1. Video-level search (/search) - Find videos using global embeddings
2. Chunk-level search (/search/chunks) - Find specific moments with timestamps
"""

from fastapi import APIRouter, HTTPException

from compose.api.models import (
    CacheSearchRequest,
    CacheSearchResponse,
    CacheSearchResult,
    ChunkSearchResponse,
    ChunkSearchResult,
)
from compose.services.embeddings import get_global_embedder, get_chunk_embedder
from compose.services.surrealdb import semantic_search, semantic_search_chunks

router = APIRouter()


def _format_timestamp(seconds: float) -> str:
    """Format seconds as MM:SS or H:MM:SS."""
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    secs = int(seconds % 60)
    if hours > 0:
        return f"{hours}:{minutes:02d}:{secs:02d}"
    return f"{minutes}:{secs:02d}"


@router.post("/search", response_model=CacheSearchResponse)
async def search_cache(request: CacheSearchRequest):
    """
    Search the semantic cache using SurrealDB vector search.

    Uses global embeddings (gte-large) for document-level similarity.
    Returns videos ranked by relevance to the query.
    """
    try:
        # Generate embedding from query using global embedder
        embedder = get_global_embedder()
        query_embedding = embedder.embed(request.query)

        # Search SurrealDB for similar videos
        results = await semantic_search(query_embedding, limit=request.limit)

        # Format results
        search_results = [
            CacheSearchResult(
                video_id=r.video_id,
                score=r.similarity_score,
                title=r.title,
                url=r.url,
                summary=None,
                tags=None,
            )
            for r in results
        ]

        return CacheSearchResponse(
            query=request.query,
            results=search_results,
            total_found=len(search_results),
        )

    except ConnectionError as e:
        raise HTTPException(
            status_code=503,
            detail=f"Embedding service unavailable: {str(e)}",
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Cache search failed: {str(e)}")


@router.post("/search/chunks", response_model=ChunkSearchResponse)
async def search_chunks(request: CacheSearchRequest):
    """
    Search for specific moments within videos using chunk-level embeddings.

    Uses chunk embeddings (bge-m3) for fine-grained semantic search.
    Returns chunks with timestamps for jumping to specific video moments.
    """
    try:
        # Generate embedding from query using chunk embedder
        embedder = get_chunk_embedder()
        query_embedding = embedder.embed(request.query)

        # Search SurrealDB for similar chunks
        results = await semantic_search_chunks(query_embedding, limit=request.limit)

        # Format results with timestamp ranges
        search_results = [
            ChunkSearchResult(
                chunk_id=r.chunk_id,
                video_id=r.video_id,
                chunk_index=r.chunk_index,
                text=r.text,
                start_time=r.start_time,
                end_time=r.end_time,
                timestamp_range=f"{_format_timestamp(r.start_time)} - {_format_timestamp(r.end_time)}",
                score=r.similarity_score,
                video_title=r.video_title,
                video_url=r.video_url,
            )
            for r in results
        ]

        return ChunkSearchResponse(
            query=request.query,
            results=search_results,
            total_found=len(search_results),
        )

    except ConnectionError as e:
        raise HTTPException(
            status_code=503,
            detail=f"Embedding service unavailable: {str(e)}",
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Chunk search failed: {str(e)}")


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
