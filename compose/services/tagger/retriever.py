"""Semantic tag retrieval using Qdrant for normalization context."""

from pathlib import Path
from typing import Dict, List, Optional, Set

from compose.services.cache.qdrant_cache import QdrantCache
from compose.services.cache.config import CacheConfig


class SemanticTagRetriever:
    """Retrieve tags from semantically similar content for normalization context."""

    def __init__(self, cache: QdrantCache):
        """Initialize retriever.

        Args:
            cache: QdrantCache instance for semantic search
        """
        self.cache = cache

    def find_similar_content(
        self,
        query_text: str,
        limit: int = 5,
        min_score: float = 0.5
    ) -> List[Dict]:
        """Find semantically similar content.

        Args:
            query_text: Text to find similar content for
            limit: Maximum number of results
            min_score: Minimum similarity score (0-1)

        Returns:
            List of similar content dicts with metadata
        """
        results = self.cache.search(query_text, limit=limit)

        # Filter by score if available
        filtered = []
        for result in results:
            # Qdrant returns results with score
            if hasattr(result, 'score') and result.score >= min_score:
                filtered.append(result)
            else:
                # No score available, include all
                filtered.append(result)

        return filtered[:limit]

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

        # Handle structured metadata (new format)
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

    def extract_tags_from_result(self, result: Dict) -> Dict[str, Set[str]]:
        """Extract tags from Qdrant search result.

        Args:
            result: Result dict from cache.search()

        Returns:
            Dict with tag categories
        """
        import json

        extracted = {
            "subject_matter": set(),
            "entities": set(),
            "techniques": set(),
            "tools": set(),
            "tags": set(),
        }

        # Check for tags field (old format - JSON string)
        if "tags" in result:
            tags_value = result["tags"]
            if isinstance(tags_value, str):
                try:
                    data = json.loads(tags_value)
                    if isinstance(data, dict) and "tags" in data:
                        tags_list = data["tags"]
                        if isinstance(tags_list, list):
                            extracted["tags"].update(tags_list)
                except json.JSONDecodeError:
                    pass

        # Check for metadata field (new format - structured)
        if "_metadata" in result:
            metadata = result["_metadata"]
            metadata_tags = self.extract_tags_from_metadata(metadata)
            for key in extracted.keys():
                extracted[key].update(metadata_tags[key])

        # Also check flattened meta_ fields (if they exist)
        for key, value in result.items():
            if not key.startswith("meta_"):
                continue

            # Skip if not True/present
            if value != True and value != "True":
                continue

            # Parse field name: meta_subject_ai_agents -> ("subject", "ai_agents")
            parts = key.split("_", 2)
            if len(parts) < 3:
                continue

            field_type = parts[1]  # "subject", "entity", "technique", "tool"
            tag_name = parts[2].replace("_", "-")  # "ai_agents" -> "ai-agents"

            # Map to our categories
            if field_type == "subject":
                extracted["subject_matter"].add(tag_name)
            elif field_type == "entity":
                extracted["entities"].add(tag_name)
            elif field_type == "technique":
                extracted["techniques"].add(tag_name)
            elif field_type == "tool":
                extracted["tools"].add(tag_name)

        return extracted

    def get_context_tags(
        self,
        query_text: str,
        limit: int = 5,
        min_score: float = 0.5
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
            # Results are dicts from cache.search()
            if isinstance(result, dict):
                result_tags = self.extract_tags_from_result(result)
                for key in aggregated.keys():
                    aggregated[key].update(result_tags[key])

        return aggregated

    def format_context_for_prompt(
        self,
        context_tags: Dict[str, Set[str]],
        top_n_per_category: int = 10
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
        min_score: float = 0.5
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
            min_score=min_score
        )
        return self.format_context_for_prompt(context_tags, top_n_per_category)


def create_retriever(
    collection_name: str = "cached_content",
    qdrant_path: Optional[Path] = None,
    qdrant_url: Optional[str] = None,
    infinity_url: Optional[str] = None,
    infinity_model: str = "Alibaba-NLP/gte-large-en-v1.5"
) -> SemanticTagRetriever:
    """Create a semantic tag retriever.

    Args:
        collection_name: Qdrant collection name
        qdrant_path: Path to Qdrant storage (for local mode, if no qdrant_url)
        qdrant_url: URL for remote Qdrant server (e.g., "http://192.168.16.241:6333")
        infinity_url: URL for Infinity embedding server (e.g., "http://192.168.16.241:7997")
        infinity_model: Embedding model for Infinity (default: gte-large-en-v1.5)

    Returns:
        SemanticTagRetriever instance
    """
    import os

    # Check environment variables for defaults
    if qdrant_url is None:
        qdrant_url = os.getenv("QDRANT_URL")
    if infinity_url is None:
        infinity_url = os.getenv("INFINITY_URL")

    if qdrant_path is None and qdrant_url is None:
        # Use default path from project (local mode)
        project_root = Path(__file__).parent.parent.parent.parent
        qdrant_path = project_root / "compose" / "data" / "qdrant_storage"

    config = CacheConfig(
        cache_dir=qdrant_path or Path("."),  # Fallback path for config validation
        collection_name=collection_name,
        embedding_model="BAAI/bge-m3",
        qdrant_url=qdrant_url,
        infinity_url=infinity_url,
        infinity_model=infinity_model
    )

    cache = QdrantCache(config)

    return SemanticTagRetriever(cache)
