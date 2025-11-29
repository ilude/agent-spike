"""Semantic tag retriever using SurrealDB vector search.

Replaces the Qdrant-based retriever with SurrealDB's native HNSW vector search.
Loads detailed metadata from local archive files for context-aware tag retrieval.
"""

import asyncio
import json
import logging
from pathlib import Path
from typing import Optional

from compose.services.surrealdb.repository import (
    semantic_search,
    search_videos_by_text,
)

logger = logging.getLogger(__name__)


class SemanticTagRetriever:
    """Retrieves semantically similar content from SurrealDB for tag normalization.

    Uses SurrealDB's native vector search to find similar content, then loads
    detailed metadata from archive files to extract existing tags for context.
    """

    def __init__(
        self,
        archive_base_path: Optional[Path] = None,
    ):
        """Initialize the retriever.

        Args:
            archive_base_path: Base path for archive files. Defaults to
                compose/data/archive relative to project root.
        """
        if archive_base_path is None:
            # Default to compose/data/archive
            self.archive_base_path = Path(__file__).parent.parent.parent / "data" / "archive"
        else:
            self.archive_base_path = archive_base_path

    def find_similar_content(
        self,
        query: str,
        limit: int = 5,
        min_score: float = 0.0,
    ) -> list[dict]:
        """Find semantically similar content using text query.

        Args:
            query: Text query to search for
            limit: Maximum number of results
            min_score: Minimum similarity score (0-1)

        Returns:
            List of search results with video metadata
        """
        try:
            # Run async search synchronously
            results = asyncio.get_event_loop().run_until_complete(
                search_videos_by_text(query, limit=limit)
            )
        except RuntimeError:
            # No event loop, create one
            results = asyncio.run(search_videos_by_text(query, limit=limit))

        # Filter by minimum score and convert to dict format
        filtered = []
        for r in results:
            score = r.get("score", 0)
            if score >= min_score:
                filtered.append({
                    "video_id": r.get("video_id"),
                    "title": r.get("title"),
                    "url": r.get("url"),
                    "similarity_score": score,
                    "channel_name": r.get("channel_name"),
                    "archive_path": r.get("archive_path"),
                })

        return filtered

    async def find_similar_content_async(
        self,
        query: str,
        limit: int = 5,
        min_score: float = 0.0,
    ) -> list[dict]:
        """Async version of find_similar_content."""
        results = await search_videos_by_text(query, limit=limit)

        filtered = []
        for r in results:
            score = r.get("score", 0)
            if score >= min_score:
                filtered.append({
                    "video_id": r.get("video_id"),
                    "title": r.get("title"),
                    "url": r.get("url"),
                    "similarity_score": score,
                    "channel_name": r.get("channel_name"),
                    "archive_path": r.get("archive_path"),
                })

        return filtered

    def load_archive_metadata(self, video_id: str) -> Optional[dict]:
        """Load metadata from archive file for a video.

        Args:
            video_id: YouTube video ID

        Returns:
            Archive data dict or None if not found
        """
        # Search for archive file in monthly directories
        youtube_archive = self.archive_base_path / "youtube"
        if not youtube_archive.exists():
            return None

        for month_dir in youtube_archive.iterdir():
            if month_dir.is_dir():
                archive_file = month_dir / f"{video_id}.json"
                if archive_file.exists():
                    try:
                        return json.loads(archive_file.read_text(encoding="utf-8"))
                    except (json.JSONDecodeError, IOError) as e:
                        logger.warning(f"Failed to load archive {archive_file}: {e}")
                        return None

        return None

    def extract_tags_from_archive(self, archive_data: dict) -> dict[str, set[str]]:
        """Extract tags from archive metadata.

        Args:
            archive_data: Archive JSON data

        Returns:
            Dict with categorized tags: subject_matter, entities, techniques, tools, tags
        """
        result = {
            "subject_matter": set(),
            "entities": set(),
            "techniques": set(),
            "tools": set(),
            "tags": set(),
        }

        if not archive_data:
            return result

        # Extract from youtube_metadata.tags
        yt_meta = archive_data.get("youtube_metadata", {})
        if yt_meta.get("tags"):
            for tag in yt_meta["tags"]:
                result["tags"].add(tag.lower().strip())

        # Extract from llm_outputs
        for llm_output in archive_data.get("llm_outputs", []):
            if llm_output.get("output_type") == "tags":
                try:
                    output_value = llm_output.get("output_value", "{}")
                    if isinstance(output_value, str):
                        tag_data = json.loads(output_value)
                    else:
                        tag_data = output_value

                    # Extract tags array
                    if "tags" in tag_data and isinstance(tag_data["tags"], list):
                        for tag in tag_data["tags"]:
                            result["tags"].add(tag.lower().strip())

                except (json.JSONDecodeError, TypeError):
                    pass

        # Extract from structured_metadata if present
        structured = archive_data.get("structured_metadata", {})
        if structured:
            if "subject_matter" in structured:
                for item in structured.get("subject_matter", []):
                    result["subject_matter"].add(item.lower().strip())

            if "entities" in structured:
                entities = structured.get("entities", {})
                for entity_type in ["people", "companies", "organizations"]:
                    for entity in entities.get(entity_type, []):
                        result["entities"].add(entity)

            if "techniques_or_concepts" in structured:
                for item in structured.get("techniques_or_concepts", []):
                    result["techniques"].add(item.lower().strip())

            if "tools_or_materials" in structured:
                for item in structured.get("tools_or_materials", []):
                    result["tools"].add(item.lower().strip())

        return result

    def get_context_tags(
        self,
        query: str,
        limit: int = 5,
        min_score: float = 0.0,
    ) -> dict[str, set[str]]:
        """Get aggregated tags from semantically similar content.

        Args:
            query: Text query to search for
            limit: Maximum number of similar items to retrieve
            min_score: Minimum similarity score

        Returns:
            Dict with aggregated tags by category
        """
        results = self.find_similar_content(query, limit=limit, min_score=min_score)

        aggregated = {
            "subject_matter": set(),
            "entities": set(),
            "techniques": set(),
            "tools": set(),
            "tags": set(),
        }

        for result in results:
            video_id = result.get("video_id")
            if video_id:
                archive_data = self.load_archive_metadata(video_id)
                tags = self.extract_tags_from_archive(archive_data)

                for category in aggregated:
                    aggregated[category].update(tags.get(category, set()))

        return aggregated

    async def get_context_tags_async(
        self,
        query: str,
        limit: int = 5,
        min_score: float = 0.0,
    ) -> dict[str, set[str]]:
        """Async version of get_context_tags."""
        results = await self.find_similar_content_async(query, limit=limit, min_score=min_score)

        aggregated = {
            "subject_matter": set(),
            "entities": set(),
            "techniques": set(),
            "tools": set(),
            "tags": set(),
        }

        for result in results:
            video_id = result.get("video_id")
            if video_id:
                archive_data = self.load_archive_metadata(video_id)
                tags = self.extract_tags_from_archive(archive_data)

                for category in aggregated:
                    aggregated[category].update(tags.get(category, set()))

        return aggregated

    def format_context_for_prompt(
        self,
        context: dict[str, set[str]],
        top_n_per_category: int = 10,
    ) -> str:
        """Format context tags for inclusion in LLM prompt.

        Args:
            context: Dict of categorized tags
            top_n_per_category: Maximum tags per category

        Returns:
            Formatted string for prompt
        """
        lines = ["Tags from similar content:"]

        category_labels = {
            "subject_matter": "Subject Matter",
            "entities": "Entities",
            "techniques": "Techniques",
            "tools": "Tools",
            "tags": "General Tags",
        }

        for category, label in category_labels.items():
            tags = context.get(category, set())
            if tags:
                lines.append(f"\n{label}:")
                sorted_tags = sorted(tags)[:top_n_per_category]
                for tag in sorted_tags:
                    lines.append(f"  - {tag}")

        return "\n".join(lines)

    def get_formatted_context(
        self,
        query: str,
        limit: int = 5,
        top_n_per_category: int = 10,
    ) -> str:
        """Get formatted context for a query in one call.

        Args:
            query: Text query
            limit: Number of similar items to retrieve
            top_n_per_category: Max tags per category

        Returns:
            Formatted context string for LLM prompt
        """
        context = self.get_context_tags(query, limit=limit)
        return self.format_context_for_prompt(context, top_n_per_category)


def create_retriever(
    archive_base_path: Optional[Path] = None,
) -> SemanticTagRetriever:
    """Factory function to create a SemanticTagRetriever.

    Args:
        archive_base_path: Optional custom archive path

    Returns:
        Configured SemanticTagRetriever instance
    """
    return SemanticTagRetriever(archive_base_path=archive_base_path)
