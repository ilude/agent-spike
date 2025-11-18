"""Central version tracking for all transformations.

This module provides a single source of truth for transformation versions
used throughout the archive reprocessing system. Bump versions here when
you change logic, prompts, models, or schemas.

Version format: Use semantic versioning for transformations (v1.0, v1.1, v2.0)
               Use simple strings for models/schemas
"""

from datetime import datetime
from typing import Dict, Any


# Transformation versions - bump these when logic changes
VERSIONS: Dict[str, str] = {
    # Tag extraction and normalization
    "tag_extractor": "v1.0",           # Tag extraction from transcript
    "normalizer": "v1.0",               # lesson-010 tag normalizer
    "vocabulary": "v1",                 # Vocabulary version (from vocabulary.json)

    # Metadata transformation
    "qdrant_flattener": "v1.0",         # Metadata flattening for Qdrant filters
    "weight_calculator": "v1.0",        # Recommendation weight calculation

    # Data schema
    "qdrant_schema": "v1",              # Qdrant payload structure
    "archive_schema": "v1",             # Archive JSON structure

    # Models used
    "embedding_model": "all-MiniLM-L6-v2",  # sentence-transformers model
    "llm_model": "claude-3-5-haiku-20241022",  # Default LLM
}


def get_transform_manifest() -> Dict[str, Any]:
    """Get current state of all transformation versions.

    Returns a dictionary with all current versions plus timestamp.
    This manifest should be stored alongside transformed data for
    tracking and staleness detection.

    Returns:
        Dict with all versions and created_at timestamp

    Example:
        >>> manifest = get_transform_manifest()
        >>> manifest['normalizer']
        'v1.0'
        >>> 'created_at' in manifest
        True
    """
    return {
        **VERSIONS,
        "created_at": datetime.now().isoformat(),
    }


def get_version(key: str) -> str:
    """Get specific transformation version.

    Args:
        key: Version key (e.g., "normalizer", "vocabulary")

    Returns:
        Version string

    Raises:
        KeyError: If version key doesn't exist
    """
    return VERSIONS[key]


def compare_versions(stored_manifest: Dict[str, Any], current_manifest: Dict[str, Any]) -> Dict[str, tuple[str, str]]:
    """Compare two transformation manifests to find differences.

    Args:
        stored_manifest: Manifest from archived/cached data
        current_manifest: Current manifest from get_transform_manifest()

    Returns:
        Dict mapping changed keys to (old_version, new_version) tuples

    Example:
        >>> stored = {"normalizer": "v1.0", "vocabulary": "v1"}
        >>> current = {"normalizer": "v1.1", "vocabulary": "v1"}
        >>> changes = compare_versions(stored, current)
        >>> changes
        {'normalizer': ('v1.0', 'v1.1')}
    """
    changes = {}

    for key in current_manifest.keys():
        if key == "created_at":
            continue

        stored_value = stored_manifest.get(key, "unknown")
        current_value = current_manifest[key]

        if stored_value != current_value:
            changes[key] = (stored_value, current_value)

    return changes


def is_stale(stored_manifest: Dict[str, Any], check_keys: list[str] = None) -> tuple[bool, list[str]]:
    """Check if stored data is stale based on version changes.

    Args:
        stored_manifest: Manifest from archived/cached data
        check_keys: Optional list of specific keys to check. If None, checks all.

    Returns:
        Tuple of (is_stale, list of changed keys)

    Example:
        >>> stored = {"normalizer": "v1.0", "vocabulary": "v1"}
        >>> is_stale(stored, check_keys=["normalizer"])
        (False, [])
        >>> # After bumping normalizer to v1.1
        >>> is_stale(stored, check_keys=["normalizer"])
        (True, ['normalizer'])
    """
    current = get_transform_manifest()
    changes = compare_versions(stored_manifest, current)

    if check_keys:
        # Only check specified keys
        relevant_changes = [k for k in changes.keys() if k in check_keys]
    else:
        # Check all changes
        relevant_changes = list(changes.keys())

    return len(relevant_changes) > 0, relevant_changes
