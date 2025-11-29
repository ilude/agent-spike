"""Metadata transformation strategies for archive reprocessing.

This module provides pluggable transformers that extract, flatten, and enrich
metadata from archive records. Each transformer is versioned and can be applied
selectively during reprocessing.

Design pattern: Strategy pattern with Template Method
- Each transformer implements a common interface
- Transformers are composable and reusable
- Version tracking built into each transformer
"""

import json
from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional, Protocol
from datetime import datetime

from .transform_versions import get_version, get_transform_manifest


class MetadataTransformer(Protocol):
    """Protocol for metadata transformation strategies."""

    def transform(self, archive_data: Dict[str, Any]) -> Dict[str, Any]:
        """Transform archive data into enriched metadata.

        Args:
            archive_data: Raw archive record (YouTube video JSON, etc.)

        Returns:
            Dict with transformed metadata ready for storage/indexing
        """
        ...

    def get_version(self) -> str:
        """Get transformer version for change tracking."""
        ...

    def get_dependencies(self) -> List[str]:
        """Get list of version keys this transformer depends on.

        Returns:
            List of keys from VERSIONS dict (e.g., ['vocabulary', 'llm_model'])
        """
        ...


class BaseTransformer(ABC):
    """Base class for metadata transformers with common utilities."""

    @abstractmethod
    def transform(self, archive_data: Dict[str, Any]) -> Dict[str, Any]:
        """Transform archive data into enriched metadata."""
        pass

    @abstractmethod
    def get_version(self) -> str:
        """Get transformer version."""
        pass

    def get_dependencies(self) -> List[str]:
        """Get version dependencies. Override if needed."""
        return []

    def _safe_key(self, value: str) -> str:
        """Convert a tag/entity to a safe metadata key.

        Args:
            value: Raw tag or entity name

        Returns:
            Safe key (lowercase, underscores, alphanumeric)

        Example:
            >>> self._safe_key("AI Agents")
            'ai_agents'
            >>> self._safe_key("prompt-engineering")
            'prompt_engineering'
        """
        return value.replace("-", "_").replace(" ", "_").lower()


class SurrealDBMetadataFlattener(BaseTransformer):
    """Flattens structured metadata into SurrealDB-compatible filter fields.

    Transforms nested tag structures into flat boolean fields for efficient
    SurrealDB filtering (e.g., subject_ai_agents=True, entity_claude=True).

    Version tracking: Uses surrealdb_flattener version
    """

    def get_version(self) -> str:
        return get_version("surrealdb_flattener")

    def get_dependencies(self) -> List[str]:
        return ["surrealdb_schema", "archive_schema"]

    def transform(self, archive_data: Dict[str, Any]) -> Dict[str, Any]:
        """Flatten structured tags into filter fields.

        Args:
            archive_data: Archive record with llm_outputs containing tags

        Returns:
            Flattened metadata dict with boolean filter fields
        """
        # Extract tags from llm_outputs
        tags_data = self._extract_tags(archive_data)
        if not tags_data:
            return {}

        # Build flattened metadata
        metadata = {
            "type": "youtube_video",
            "source": "youtube-transcript-api",
            "video_id": archive_data.get("video_id", "unknown"),
            "content_style": tags_data.get("content_style"),
            "difficulty": tags_data.get("difficulty"),
        }

        # Flatten subject_matter
        for subject in tags_data.get("subject_matter", []):
            safe_key = self._safe_key(subject)
            metadata[f"subject_{safe_key}"] = True

        # Flatten entities
        entities = tags_data.get("entities", {})
        for entity in entities.get("named_things", []):
            safe_key = self._safe_key(entity)
            metadata[f"entity_{safe_key}"] = True

        for person in entities.get("people", []):
            safe_key = self._safe_key(person)
            metadata[f"person_{safe_key}"] = True

        for company in entities.get("companies", []):
            safe_key = self._safe_key(company)
            metadata[f"company_{safe_key}"] = True

        # Flatten references
        for ref in tags_data.get("references", []):
            ref_name = ref.get("name", "")
            ref_type = ref.get("type", "")
            if ref_name:
                safe_key = self._safe_key(ref_name)
                metadata[f"ref_{safe_key}"] = True
            if ref_type:
                metadata[f"ref_type_{ref_type}"] = True

        # Store full tags as JSON
        metadata["tags_json"] = json.dumps(tags_data)

        return metadata

    def _extract_tags(self, archive_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Extract tags from llm_outputs in archive.

        Looks for most recent 'tags' output_type in llm_outputs array.

        Args:
            archive_data: Archive record

        Returns:
            Tags dict or None if not found
        """
        llm_outputs = archive_data.get("llm_outputs", [])
        if not llm_outputs:
            return None

        # Find most recent tags output
        for output in reversed(llm_outputs):
            if output.get("output_type") == "tags":
                output_value = output.get("output_value")

                # Handle both old format (JSON string) and new format (dict)
                if isinstance(output_value, str):
                    try:
                        return json.loads(output_value)
                    except json.JSONDecodeError:
                        return None
                elif isinstance(output_value, dict):
                    return output_value

        return None


class RecommendationWeightCalculator(BaseTransformer):
    """Calculates recommendation weight based on import metadata.

    Assigns weights to videos based on how they were imported:
    - bulk_channel: 0.5 (lower priority, mass-imported)
    - single_import: 1.0 (higher priority, curated)

    Version tracking: Uses weight_calculator version
    """

    def get_version(self) -> str:
        return get_version("weight_calculator")

    def transform(self, archive_data: Dict[str, Any]) -> Dict[str, Any]:
        """Calculate recommendation weight from import metadata.

        Args:
            archive_data: Archive record with import_metadata

        Returns:
            Dict with source_type, recommendation_weight, is_bulk_import
        """
        import_metadata = archive_data.get("import_metadata", {})
        source_type = import_metadata.get("source_type", "single_import")

        # Calculate weight
        if source_type == "bulk_channel":
            weight = 0.5
            is_bulk = True
        else:
            weight = 1.0
            is_bulk = False

        return {
            "source_type": source_type,
            "recommendation_weight": weight,
            "is_bulk_import": is_bulk,
            "imported_at": import_metadata.get("imported_at", datetime.now().isoformat()),
        }


class CompositeTransformer(BaseTransformer):
    """Composes multiple transformers into a single pipeline.

    Runs transformers in sequence and merges their outputs.
    """

    def __init__(self, transformers: List[MetadataTransformer]):
        """Initialize composite transformer.

        Args:
            transformers: List of transformers to apply in order
        """
        self.transformers = transformers

    def get_version(self) -> str:
        """Get composite version from all transformers."""
        versions = [t.get_version() for t in self.transformers]
        return "+".join(versions)

    def get_dependencies(self) -> List[str]:
        """Get union of all transformer dependencies."""
        deps = set()
        for transformer in self.transformers:
            deps.update(transformer.get_dependencies())
        return list(deps)

    def transform(self, archive_data: Dict[str, Any]) -> Dict[str, Any]:
        """Apply all transformers and merge results.

        Args:
            archive_data: Archive record

        Returns:
            Merged metadata from all transformers
        """
        result = {}
        for transformer in self.transformers:
            output = transformer.transform(archive_data)
            result.update(output)
        return result


# Factory functions for common transformer combinations

def create_surrealdb_transformer() -> MetadataTransformer:
    """Create standard SurrealDB metadata transformer.

    Returns:
        CompositeTransformer with flattening + weight calculation
    """
    return CompositeTransformer([
        SurrealDBMetadataFlattener(),
        RecommendationWeightCalculator(),
    ])


def create_custom_transformer(transformers: List[MetadataTransformer]) -> MetadataTransformer:
    """Create custom transformer pipeline.

    Args:
        transformers: List of transformers to compose

    Returns:
        CompositeTransformer
    """
    return CompositeTransformer(transformers)
