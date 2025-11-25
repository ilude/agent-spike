"""YouTube RAG router for semantic search and query answering.

Provides REST endpoints for:
1. Semantic search over YouTube transcripts (via SurrealDB)
2. Query answering using retrieved context (RAG pattern)
"""

import os
import httpx
from pydantic import BaseModel, Field
from fastapi import APIRouter, HTTPException

# from compose.services.surrealdb import semantic_search  # OLD: inline RAG
from compose.services.rag import SurrealDBRAG

router = APIRouter()

# Configuration
INFINITY_URL = os.getenv("INFINITY_URL", "http://192.168.16.241:7997")
INFINITY_MODEL = os.getenv("INFINITY_MODEL", "Alibaba-NLP/gte-large-en-v1.5")


# OLD: get_embedding (now handled by SurrealDBRAG service)
# async def get_embedding(text: str) -> list[float]:
#     """Get embedding from Infinity service."""
#     async with httpx.AsyncClient(timeout=60.0) as client:
#         response = await client.post(
#             f"{INFINITY_URL}/embeddings",
#             json={"model": INFINITY_MODEL, "input": [text]}
#         )
#         response.raise_for_status()
#         data = response.json()
#         return data["data"][0]["embedding"]
#


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

    Searches the SurrealDB vector database for videos matching the query.
    Returns videos ranked by semantic similarity.
    """
    try:
        # NEW: Use SurrealDBRAG service
        rag = SurrealDBRAG()
        results = await rag.retrieve_context(
            query=request.query,
            limit=request.limit,
            channel_filter=request.channel
        )

        # Format results
        search_results = []
        for r in results:
            search_results.append(
                SearchResult(
                    video_id=r.get("video_id", ""),
                    title=r.get("title", "Unknown"),
                    channel=r.get("channel_name", "Unknown"),
                    score=round(r.get("score", 0.0), 3),
                    transcript_preview="",  # Transcript in MinIO, not fetched here
                    url=r.get("url", f"https://youtube.com/watch?v={r.get('video_id', '')}"),
                )
            )

        return SearchResponse(
            query=request.query,
            results=search_results,
            total_found=len(search_results),
        )

        # OLD: Inline RAG (commented out - delete in Phase 4)
        # # Step 1: Get embedding for query
        # query_vector = await get_embedding(request.query)
        #
        # # Step 2: Search SurrealDB
        # results = await semantic_search(query_vector, limit=request.limit)
        #
        # # Step 3: Format results
        # search_results = []
        # for r in results:
        #     # TODO: Filter by channel if request.channel is set
        #     search_results.append(
        #         SearchResult(
        #             video_id=r.video_id,
        #             title=r.title or "Unknown",
        #             channel="Unknown",  # Channel stored separately in SurrealDB
        #             score=round(r.similarity_score, 3),
        #             transcript_preview="",  # Transcript in MinIO, not fetched here
        #             url=r.url or f"https://youtube.com/watch?v={r.video_id}",
        #         )
        #     )

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
        # Step 1: Get embedding for query
        query_vector = await get_embedding(request.question)

        # Step 2: Search SurrealDB
        results = await semantic_search(query_vector, limit=request.limit)

        # Step 3: Build sources list
        sources = []
        seen_ids = set()

        for r in results:
            if r.video_id not in seen_ids:
                sources.append(
                    QuerySource(
                        video_id=r.video_id,
                        title=r.title or "Unknown",
                        url=r.url or f"https://youtube.com/watch?v={r.video_id}",
                        relevance_score=round(r.similarity_score, 3),
                    )
                )
                seen_ids.add(r.video_id)

        # Build answer from context (simplified - no LLM)
        if sources:
            video_list = "\n".join([f"- {s.title} ({s.relevance_score:.3f})" for s in sources])
            answer = (
                f"Found {len(sources)} relevant video(s):\n\n{video_list}\n\n"
                "Use the /ws/rag-chat WebSocket for full LLM-powered answers."
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

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Query failed: {str(e)}")
