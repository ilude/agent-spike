"""YouTube RAG router for semantic search and query answering.

Provides REST endpoints for:
1. Semantic search over YouTube transcripts (via SurrealDB)
2. Query answering using retrieved context (RAG pattern)
"""

from pydantic import BaseModel, Field
from fastapi import APIRouter, HTTPException

from compose.services.surrealdb import semantic_search

router = APIRouter()

# Configuration
SURREALDB_URL = "http://localhost:8000"
INFINITY_URL = "http://localhost:7997"


# -----------------------------------------------------------------------------
# Request/Response Models
# -----------------------------------------------------------------------------


class SearchRequest(BaseModel):
    """Request for semantic search over YouTube transcripts."""

    query: str = Field(..., min_length=1, max_length=1000, description="Search query")
    limit: int = Field(default=10, ge=1, le=100, description="Max results to return")
    channel: str | None = Field(default=None, description="Filter by channel name")


class SearchResult(BaseModel):
    """Single search result from YouTube transcript search."""

    video_id: str
    title: str
    channel: str
    score: float
    transcript_preview: str
    url: str


class SearchResponse(BaseModel):
    """Response from semantic search."""

    query: str
    results: list[SearchResult]
    total_found: int


class QueryRequest(BaseModel):
    """Request for RAG-based query answering."""

    question: str = Field(..., min_length=1, max_length=2000, description="Question to answer")
    limit: int = Field(default=5, ge=1, le=20, description="Number of context sources")
    channel: str | None = Field(default=None, description="Filter by channel name")


class QuerySource(BaseModel):
    """Source video used to answer a query."""

    video_id: str
    title: str
    url: str
    relevance_score: float


class QueryResponse(BaseModel):
    """Response from RAG query."""

    question: str
    answer: str
    sources: list[QuerySource]
    context_used: bool = Field(description="Whether RAG context was used in the answer")


# -----------------------------------------------------------------------------
# Endpoints
# -----------------------------------------------------------------------------


@router.post("/search", response_model=SearchResponse)
async def search_transcripts(request: SearchRequest):
    """
    Semantic search over YouTube video transcripts.

    Searches the Qdrant vector database for videos matching the query.
    Returns videos ranked by semantic similarity.
    """
    try:
        cache = create_qdrant_cache(
            collection_name=COLLECTION_NAME,
            qdrant_url=QDRANT_URL,
            infinity_url=INFINITY_URL,
        )

        try:
            # Build filters
            filters = {"type": "youtube_video"}
            if request.channel:
                filters["youtube_channel"] = request.channel

            # Perform search
            results = cache.search(request.query, limit=request.limit, filters=filters)

            # Format results
            search_results = []
            for r in results:
                metadata = r.get("_metadata", {})
                video_id = r.get("video_id", "unknown")
                transcript = r.get("transcript", "")

                search_results.append(
                    SearchResult(
                        video_id=video_id,
                        title=metadata.get("youtube_title", "Unknown"),
                        channel=metadata.get("youtube_channel", "Unknown"),
                        score=round(r.get("_score", 0), 3),
                        transcript_preview=transcript[:500] + "..." if len(transcript) > 500 else transcript,
                        url=f"https://youtube.com/watch?v={video_id}",
                    )
                )

            return SearchResponse(
                query=request.query,
                results=search_results,
                total_found=len(search_results),
            )
        finally:
            cache.close()

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Search failed: {str(e)}")


@router.post("/query", response_model=QueryResponse)
async def query_videos(request: QueryRequest):
    """
    Answer a question using RAG over YouTube transcripts.

    Retrieves relevant video context and generates an answer.
    Note: This is a simplified version that returns context without LLM generation.
    For full RAG with LLM, use the WebSocket /ws/rag-chat endpoint.
    """
    try:
        cache = create_qdrant_cache(
            collection_name=COLLECTION_NAME,
            qdrant_url=QDRANT_URL,
            infinity_url=INFINITY_URL,
        )

        try:
            # Build filters
            filters = {"type": "youtube_video"}
            if request.channel:
                filters["youtube_channel"] = request.channel

            # Search for relevant context
            results = cache.search(request.question, limit=request.limit, filters=filters)

            # Build sources list
            sources = []
            context_chunks = []
            seen_ids = set()

            for r in results:
                metadata = r.get("_metadata", {})
                video_id = r.get("video_id", "unknown")

                if video_id not in seen_ids:
                    sources.append(
                        QuerySource(
                            video_id=video_id,
                            title=metadata.get("youtube_title", "Unknown"),
                            url=f"https://youtube.com/watch?v={video_id}",
                            relevance_score=round(r.get("_score", 0), 3),
                        )
                    )
                    seen_ids.add(video_id)

                transcript = r.get("transcript", "")
                if transcript:
                    context_chunks.append(transcript[:1000])

            # Build answer from context (simplified - no LLM)
            # In production, this would call an LLM with the context
            if context_chunks:
                answer = (
                    f"Based on {len(sources)} relevant video(s), here is context that may help answer your question:\n\n"
                    + "\n\n---\n\n".join(context_chunks[:3])
                )
                context_used = True
            else:
                answer = "No relevant video content found for your question."
                context_used = False

            return QueryResponse(
                question=request.question,
                answer=answer,
                sources=sources,
                context_used=context_used,
            )
        finally:
            cache.close()

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Query failed: {str(e)}")
