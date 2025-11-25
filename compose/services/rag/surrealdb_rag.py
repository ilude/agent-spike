"""SurrealDB-based RAG service for context retrieval.

Provides semantic search and context formatting for LLM prompts
using SurrealDB vector search and MinIO transcript storage.
"""

import logging
from typing import Optional

from compose.services.minio import ArchiveStorage, create_minio_client
from compose.services.surrealdb.repository import search_videos_by_text

logger = logging.getLogger(__name__)


def get_transcript_from_minio(video_id: str, max_chars: int = 4000) -> str | None:
    """Fetch transcript from MinIO storage.

    Args:
        video_id: YouTube video ID.
        max_chars: Maximum characters to return (to fit context window).

    Returns:
        Transcript text (truncated if needed) or None if not found.
    """
    try:
        minio_client = create_minio_client()
        archive = ArchiveStorage(minio_client)
        transcript = archive.get_transcript(video_id)
        if transcript and len(transcript) > max_chars:
            # Truncate and indicate more content exists
            return transcript[:max_chars] + "\n\n[... transcript truncated ...]"
        return transcript
    except Exception as e:
        logger.warning(f"Failed to fetch transcript for {video_id}: {e}")
        return None


class SurrealDBRAG:
    """RAG service using SurrealDB for semantic search.

    Provides context retrieval and formatting for LLM prompts without
    any Qdrant dependencies.

    Example:
        >>> rag = SurrealDBRAG()
        >>> results = await rag.retrieve_context("How to build AI agents?")
        >>> context = await rag.format_context_for_llm("How to build AI agents?")
    """

    def __init__(
        self,
        default_limit: int = 5,
        min_score: float = 0.0,
        max_transcript_chars: int = 4000,
    ):
        """Initialize RAG service.

        Args:
            default_limit: Default number of results to retrieve (default: 5)
            min_score: Minimum similarity score threshold (0.0-1.0, default: 0.0)
            max_transcript_chars: Max chars per transcript (default: 4000)
        """
        self.default_limit = default_limit
        self.min_score = min_score
        self.max_transcript_chars = max_transcript_chars

    async def retrieve_context(
        self,
        query: str,
        limit: int | None = None,
        channel_filter: str | None = None,
    ) -> list[dict]:
        """Retrieve relevant video context for a query.

        Args:
            query: Text query to search for
            limit: Maximum number of results (uses default_limit if None)
            channel_filter: Filter by channel name (optional)

        Returns:
            List of video records with similarity scores

        Raises:
            ValueError: If query is empty or limit is invalid
            ConnectionError: If SurrealDB or Infinity service unavailable
        """
        # Validate inputs
        if not query or not query.strip():
            raise ValueError("Query cannot be empty")

        if limit is not None and limit < 0:
            raise ValueError(f"Limit must be non-negative, got {limit}")

        # Use default limit if not specified
        if limit is None:
            limit = self.default_limit

        # Search SurrealDB
        try:
            results = await search_videos_by_text(
                query_text=query,
                limit=limit,
                channel_filter=channel_filter,
            )
        except Exception as e:
            logger.error(f"SurrealDB search failed: {e}")
            raise

        # Filter by minimum score
        if self.min_score > 0.0:
            results = [r for r in results if r.get("score", 0.0) >= self.min_score]

        return results

    async def format_context_for_llm(
        self,
        query: str,
        limit: int | None = None,
        channel_filter: str | None = None,
    ) -> str:
        """Format retrieved context for LLM prompt.

        Args:
            query: Text query to search for
            limit: Maximum number of results (uses default_limit if None)
            channel_filter: Filter by channel name (optional)

        Returns:
            Formatted context string ready for LLM prompt
        """
        # Retrieve context
        results = await self.retrieve_context(query, limit, channel_filter)

        if not results:
            return ""

        # Build formatted context
        context_parts = []

        for result in results:
            video_id = result.get("video_id", "")
            title = result.get("title", "Unknown Video")
            channel = result.get("channel_name", "Unknown Channel")
            url = result.get("url", f"https://youtube.com/watch?v={video_id}")
            score = result.get("score", 0.0)

            # Fetch transcript from MinIO
            transcript = get_transcript_from_minio(video_id, self.max_transcript_chars)

            # Build context entry
            entry = f'[Video: "{title}"]\n'
            entry += f"Channel: {channel}\n"
            entry += f"Relevance: {score:.3f}\n"

            if transcript:
                entry += f"\nTranscript:\n{transcript}"
            else:
                entry += "\n(Transcript not available)"

            context_parts.append(entry)

        return "\n\n---\n\n".join(context_parts)

    def extract_sources(self, results: list[dict]) -> list[dict]:
        """Extract source citations from search results.

        Args:
            results: Search results from retrieve_context()

        Returns:
            List of source dictionaries with video_id, title, url, score
        """
        sources = []

        for result in results:
            sources.append({
                "video_id": result.get("video_id", ""),
                "title": result.get("title", "Unknown Video"),
                "url": result.get("url", ""),
                "relevance_score": result.get("score", 0.0),
            })

        return sources

    async def get_context_and_sources(
        self,
        query: str,
        limit: int | None = None,
        channel_filter: str | None = None,
    ) -> tuple[str, list[dict]]:
        """Get both formatted context and source citations.

        Convenience method for common RAG use case.

        Args:
            query: Text query to search for
            limit: Maximum number of results (uses default_limit if None)
            channel_filter: Filter by channel name (optional)

        Returns:
            Tuple of (formatted_context, sources)
        """
        results = await self.retrieve_context(query, limit, channel_filter)
        context = await self.format_context_for_llm(query, limit, channel_filter)
        sources = self.extract_sources(results)

        return context, sources
