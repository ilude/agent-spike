"""Semantic tag retrieval using SurrealDB for normalization context.

Replaces the Qdrant-based retriever with SurrealDB native vector search.
"""

from typing import Dict, List, Optional, Set

from compose.services.surrealdb import semantic_search
from compose.services.embeddings import get_embedding_sync


class SurrealDBTagRetriever:
    """Retrieve tags from semantically similar content for normalization context.

    Uses SurrealDB's native HNSW vector search instead of Qdrant.
    """

    def __init__(
        self,
        infinity_url: Optional[str] = None,
        infinity_model: str = "Alibaba-NLP/gte-large-en-v1.5",
    ):
        """Initialize retriever.

        Args:
            infinity_url: URL for Infinity embedding server
            infinity_model: Embedding model for Infinity
        """
        self.infinity_url = infinity_url
        self.infinity_model = infinity_model

    def find_similar_content(
        self,
        query_text: str,
        limit: int = 5,
        min_score: float = 0.5,
    ) -> List[Dict]:
        """Find semantically similar content using SurrealDB vector search.

        Args:
            query_text: Text to find similar content for
            limit: Maximum number of results
            min_score: Minimum similarity score (0-1)

        Returns:
            List of similar content dicts with metadata
        """
        import asyncio

        # Get embedding for query text
        embedding = get_embedding_sync(
            query_text,
            infinity_url=self.infinity_url,
            model=self.infinity_model,
        )

        if not embedding:
            return []

        # Search SurrealDB for similar videos
        async def _search():
            return await semantic_search(embedding, limit=limit)

        results = asyncio.run(_search())

        # Filter by score
        filtered = [r for r in results if r.similarity_score >= min_score]

        # Convert to dict format
        return [
            {
                "video_id": r.video_id,
                "title": r.title,
                "url": r.url,
                "similarity_score": r.similarity_score,
                "channel_name": r.channel_name,
                "archive_path": r.archive_path,
            }
            for r in filtered
        ]

    def extract_tags_from_metadata(self, metadata: Dict) -> Dict[str, Set[str]]:
        """Extract tags from cached content metadata.

        Args:
            metadata: Metadata dict from cached content

        Returns:
            Dict with tag categories (subject_matter, entities, etc.)
        """
        extracted = {
            "subject_matter": set(),
            "entities": set(),
            "techniques": set(),
            "tools": set(),
            "tags": set(),
        }

        # Handle structured metadata
        if isinstance(metadata, dict):
            # Subject matter
            subject = metadata.get("subject_matter", [])
            if isinstance(subject, list):
                extracted["subject_matter"].update(subject)

            # Entities
            entities = metadata.get("entities", {})
            if isinstance(entities, dict):
                for key, values in entities.items():
                    if isinstance(values, list):
                        extracted["entities"].update(values)

            # Techniques/concepts
            techniques = metadata.get("techniques_or_concepts", [])
            if isinstance(techniques, list):
                extracted["techniques"].update(techniques)

            # Tools/materials
            tools = metadata.get("tools_or_materials", [])
            if isinstance(tools, list):
                extracted["tools"].update(tools)

            # Direct tags
            tags = metadata.get("tags", [])
            if isinstance(tags, list):
                extracted["tags"].update(tags)

        return extracted

    def extract_tags_from_archive(self, archive_path: Optional[str]) -> Dict[str, Set[str]]:
        """Extract tags from archive metadata file.

        Args:
            archive_path: Path to archive (relative to archive root)

        Returns:
            Dict with tag categories
        """
        if not archive_path:
            return {
                "subject_matter": set(),
                "entities": set(),
                "techniques": set(),
                "tools": set(),
                "tags": set(),
            }

        # Load metadata from archive
        from compose.services.archive import create_local_archive_writer
        from pathlib import Path
        import json

        writer = create_local_archive_writer()
        archive_base = writer.config.base_dir
        archive_dir = archive_base / archive_path

        metadata_file = archive_dir / "metadata.json"
        if not metadata_file.exists():
            return {
                "subject_matter": set(),
                "entities": set(),
                "techniques": set(),
                "tools": set(),
                "tags": set(),
            }

        with open(metadata_file, "r", encoding="utf-8") as f:
            data = json.load(f)

        # Extract from metadata
        return self.extract_tags_from_metadata(data)

    def get_context_tags(
        self,
        query_text: str,
        limit: int = 5,
        min_score: float = 0.5,
    ) -> Dict[str, Set[str]]:
        """Get tags from similar content for normalization context.

        Args:
            query_text: Text to find similar content for (usually transcript)
            limit: Number of similar items to retrieve
            min_score: Minimum similarity score

        Returns:
            Dict with aggregated tags from similar content
        """
        similar = self.find_similar_content(query_text, limit=limit, min_score=min_score)

        aggregated = {
            "subject_matter": set(),
            "entities": set(),
            "techniques": set(),
            "tools": set(),
            "tags": set(),
        }

        for result in similar:
            # Load tags from archive
            archive_path = result.get("archive_path")
            if archive_path:
                result_tags = self.extract_tags_from_archive(archive_path)
                for key in aggregated.keys():
                    aggregated[key].update(result_tags[key])

        return aggregated

    def format_context_for_prompt(
        self,
        context_tags: Dict[str, Set[str]],
        top_n_per_category: int = 10,
    ) -> str:
        """Format context tags for inclusion in LLM prompt.

        Args:
            context_tags: Aggregated tags from similar content
            top_n_per_category: Max tags per category to include

        Returns:
            Formatted string for prompt
        """
        lines = ["Tags from similar content:"]

        for category, tags in context_tags.items():
            if not tags:
                continue

            # Convert to sorted list (by tag name)
            tag_list = sorted(list(tags))[:top_n_per_category]

            # Format category name
            category_name = category.replace("_", " ").title()
            lines.append(f"\n{category_name}:")
            for tag in tag_list:
                lines.append(f"  - {tag}")

        return "\n".join(lines)

    def get_formatted_context(
        self,
        query_text: str,
        limit: int = 5,
        top_n_per_category: int = 10,
        min_score: float = 0.5,
    ) -> str:
        """Get formatted context tags in one call.

        Args:
            query_text: Text to find similar content for
            limit: Number of similar items to retrieve
            top_n_per_category: Max tags per category
            min_score: Minimum similarity score

        Returns:
            Formatted context string for LLM prompt
        """
        context_tags = self.get_context_tags(
            query_text,
            limit=limit,
            min_score=min_score,
        )
        return self.format_context_for_prompt(context_tags, top_n_per_category)


def create_surrealdb_retriever(
    infinity_url: Optional[str] = None,
    infinity_model: str = "Alibaba-NLP/gte-large-en-v1.5",
) -> SurrealDBTagRetriever:
    """Create a SurrealDB-based semantic tag retriever.

    Args:
        infinity_url: URL for Infinity embedding server (e.g., "http://192.168.16.241:7997")
        infinity_model: Embedding model for Infinity (default: gte-large-en-v1.5)

    Returns:
        SurrealDBTagRetriever instance
    """
    import os

    # Check environment variables for defaults
    if infinity_url is None:
        infinity_url = os.getenv("INFINITY_URL")

    return SurrealDBTagRetriever(
        infinity_url=infinity_url,
        infinity_model=infinity_model,
    )
