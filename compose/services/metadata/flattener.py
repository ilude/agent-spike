"""Flatten structured video metadata for SurrealDB storage.

This module converts nested tag structures into flat key-value pairs
suitable for SurrealDB metadata filtering and search.

Example:
    >>> from compose.services.metadata import flatten_video_metadata
    >>> tags = {
    ...     "subject_matter": ["AI Agents", "Python"],
    ...     "entities": {"people": ["Sam Altman"], "companies": ["Anthropic"]},
    ...     "content_style": "tutorial",
    ...     "difficulty": "intermediate"
    ... }
    >>> metadata = flatten_video_metadata(tags)
    >>> metadata["subject_ai_agents"]
    True
    >>> metadata["person_sam_altman"]
    True
"""

import json
from typing import Any


def flatten_video_metadata(tags_data: dict[str, Any]) -> dict[str, Any]:
    """Convert structured tags to flat SurrealDB metadata.

    Handles flattening of:
    - subject_matter: List of topics -> subject_{topic} = True
    - entities.named_things: List -> named_thing_{name} = True
    - entities.people: List -> person_{name} = True
    - entities.companies: List -> company_{name} = True
    - references: List of dicts -> ref_{name} = True, ref_type_{type} = True
    - content_style: str (pass through)
    - difficulty: str (pass through)

    Args:
        tags_data: Structured metadata dict with subject_matter, entities, etc.

    Returns:
        Flat dict with safe keys for SurrealDB filtering + tags_json backup

    Example:
        >>> tags = {
        ...     "subject_matter": ["AI Agents", "Multi-Agent Systems"],
        ...     "entities": {
        ...         "people": ["Sam Altman"],
        ...         "companies": ["Anthropic", "OpenAI"]
        ...     },
        ...     "references": [
        ...         {"name": "MCP", "type": "protocol"},
        ...         {"name": "Claude", "type": "model"}
        ...     ],
        ...     "content_style": "tutorial",
        ...     "difficulty": "advanced"
        ... }
        >>> flat = flatten_video_metadata(tags)
        >>> flat["subject_ai_agents"]
        True
        >>> flat["person_sam_altman"]
        True
        >>> flat["company_anthropic"]
        True
        >>> flat["ref_mcp"]
        True
        >>> flat["ref_type_protocol"]
        True
        >>> flat["content_style"]
        'tutorial'
    """
    metadata: dict[str, Any] = {}

    # Pass through simple fields
    if content_style := tags_data.get("content_style"):
        metadata["content_style"] = content_style
    if difficulty := tags_data.get("difficulty"):
        metadata["difficulty"] = difficulty

    # Flatten subject_matter list
    for subject in tags_data.get("subject_matter", []):
        safe_key = _make_safe_key("subject", subject)
        metadata[safe_key] = True

    # Flatten entities (3 types)
    entities = tags_data.get("entities", {})

    # named_things -> named_thing_{name}
    for thing in entities.get("named_things", []):
        safe_key = _make_safe_key("named_thing", thing)
        metadata[safe_key] = True

    # people -> person_{name}
    for person in entities.get("people", []):
        safe_key = _make_safe_key("person", person)
        metadata[safe_key] = True

    # companies -> company_{name}
    for company in entities.get("companies", []):
        safe_key = _make_safe_key("company", company)
        metadata[safe_key] = True

    # Flatten references
    for ref in tags_data.get("references", []):
        if name := ref.get("name"):
            safe_key = _make_safe_key("ref", name)
            metadata[safe_key] = True
        if ref_type := ref.get("type"):
            # ref_type uses underscore-safe version
            safe_type = ref_type.replace("-", "_").replace(" ", "_").lower()
            metadata[f"ref_type_{safe_type}"] = True

    # Store full JSON for backup/migration
    metadata["tags_json"] = json.dumps(tags_data)

    return metadata


def _make_safe_key(prefix: str, value: str) -> str:
    """Convert human-readable text to safe Qdrant key.

    Args:
        prefix: Key prefix (e.g., 'subject', 'person', 'company')
        value: Human-readable value (e.g., 'AI Agents', 'Sam Altman')

    Returns:
        Safe key like 'subject_ai_agents' or 'person_sam_altman'

    Examples:
        >>> _make_safe_key("subject", "AI Agents")
        'subject_ai_agents'
        >>> _make_safe_key("person", "Sam Altman")
        'person_sam_altman'
        >>> _make_safe_key("company", "Anthropic-AI")
        'company_anthropic_ai'
    """
    # Replace hyphens and spaces with underscores, lowercase
    safe_value = value.replace("-", "_").replace(" ", "_").lower()
    return f"{prefix}_{safe_value}"
