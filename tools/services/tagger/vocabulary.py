"""Vocabulary manager with versioning and evolution tracking."""

import json
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Set


class VocabularyManager:
    """Manage tag vocabulary with versioning and evolution."""

    def __init__(self, vocabulary_path: Optional[Path] = None):
        """Initialize vocabulary manager.

        Args:
            vocabulary_path: Path to vocabulary JSON file. If None, starts empty.
        """
        self.vocabulary_path = vocabulary_path
        self.version: str = "v1"
        self.created_at: Optional[str] = None
        self.updated_at: Optional[str] = None
        self.total_tags: int = 0
        self.seed_tags: Dict[str, Dict] = {}
        self.categories: Dict[str, List[str]] = {}
        self.evolution_history: List[Dict] = []

        if vocabulary_path and vocabulary_path.exists():
            self.load()

    def load(self) -> None:
        """Load vocabulary from JSON file."""
        if not self.vocabulary_path or not self.vocabulary_path.exists():
            raise FileNotFoundError(f"Vocabulary file not found: {self.vocabulary_path}")

        with open(self.vocabulary_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        self.version = data.get("version", "v1")
        self.created_at = data.get("created_at")
        self.updated_at = data.get("updated_at")
        self.total_tags = data.get("total_tags", 0)
        self.seed_tags = data.get("seed_tags", {})
        self.categories = data.get("categories", {})
        self.evolution_history = data.get("evolution_history", [])

    def save(self, path: Optional[Path] = None) -> None:
        """Save vocabulary to JSON file.

        Args:
            path: Optional path to save to. If None, uses self.vocabulary_path.
        """
        save_path = path or self.vocabulary_path
        if not save_path:
            raise ValueError("No save path specified")

        data = {
            "version": self.version,
            "created_at": self.created_at,
            "updated_at": datetime.now().isoformat(),
            "total_tags": self.total_tags,
            "seed_tags": self.seed_tags,
            "categories": self.categories,
            "evolution_history": self.evolution_history,
        }

        save_path.parent.mkdir(parents=True, exist_ok=True)
        with open(save_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

        self.updated_at = data["updated_at"]

    def get_canonical_form(self, tag: str) -> str:
        """Get canonical form of a tag.

        Args:
            tag: Tag to normalize

        Returns:
            Canonical form, or original tag if not in vocabulary
        """
        tag_lower = tag.lower().strip()

        # Check if tag is already canonical
        if tag_lower in self.seed_tags:
            return self.seed_tags[tag_lower]["canonical_form"]

        # Check aliases
        for canonical, info in self.seed_tags.items():
            aliases = info.get("aliases", [])
            if tag_lower in [alias.lower() for alias in aliases]:
                return canonical

        # Not found - return original
        return tag

    def add_tag(
        self,
        tag: str,
        count: int = 1,
        aliases: Optional[List[str]] = None,
        category: Optional[str] = None,
    ) -> None:
        """Add or update a tag in the vocabulary.

        Args:
            tag: Tag to add (will be normalized to lowercase)
            count: Usage count
            aliases: Alternative forms of this tag
            category: Category for this tag
        """
        tag_lower = tag.lower().strip()

        if tag_lower in self.seed_tags:
            # Update existing tag
            self.seed_tags[tag_lower]["count"] += count
            if aliases:
                existing_aliases = set(self.seed_tags[tag_lower].get("aliases", []))
                existing_aliases.update(aliases)
                self.seed_tags[tag_lower]["aliases"] = list(existing_aliases)
        else:
            # Add new tag
            self.seed_tags[tag_lower] = {
                "canonical_form": tag_lower,
                "count": count,
                "confidence": min(count / 10.0, 1.0),
                "aliases": aliases or [tag_lower],
            }
            self.total_tags += 1

        # Add to category if specified
        if category:
            if category not in self.categories:
                self.categories[category] = []
            if tag_lower not in self.categories[category]:
                self.categories[category].append(tag_lower)

    def consolidate_tags(self, tag_mapping: Dict[str, str]) -> None:
        """Consolidate multiple tags into canonical forms.

        Args:
            tag_mapping: Dict mapping old tag -> canonical form
        """
        for old_tag, canonical in tag_mapping.items():
            old_lower = old_tag.lower().strip()
            canonical_lower = canonical.lower().strip()

            # Skip if already consolidated
            if old_lower == canonical_lower:
                continue

            # Move count to canonical form
            if old_lower in self.seed_tags:
                old_info = self.seed_tags[old_lower]

                if canonical_lower in self.seed_tags:
                    # Merge counts
                    self.seed_tags[canonical_lower]["count"] += old_info["count"]

                    # Merge aliases
                    existing_aliases = set(
                        self.seed_tags[canonical_lower].get("aliases", [])
                    )
                    existing_aliases.update(old_info.get("aliases", []))
                    existing_aliases.add(old_lower)
                    self.seed_tags[canonical_lower]["aliases"] = list(existing_aliases)
                else:
                    # Create canonical with old tag's info
                    self.seed_tags[canonical_lower] = {
                        "canonical_form": canonical_lower,
                        "count": old_info["count"],
                        "confidence": old_info["confidence"],
                        "aliases": list(
                            set(old_info.get("aliases", []) + [old_lower])
                        ),
                    }

                # Remove old tag
                del self.seed_tags[old_lower]

        # Record consolidation in history
        self.evolution_history.append(
            {
                "action": "consolidate",
                "timestamp": datetime.now().isoformat(),
                "consolidations": len(tag_mapping),
                "mapping": tag_mapping,
            }
        )

    def bump_version(self, reason: str = "manual") -> str:
        """Bump vocabulary version.

        Args:
            reason: Reason for version bump

        Returns:
            New version string
        """
        # Parse current version (v1 -> v2)
        current_num = int(self.version.lstrip("v"))
        new_num = current_num + 1
        new_version = f"v{new_num}"

        # Record version bump in history
        self.evolution_history.append(
            {
                "action": "version_bump",
                "timestamp": datetime.now().isoformat(),
                "from_version": self.version,
                "to_version": new_version,
                "reason": reason,
            }
        )

        self.version = new_version
        return new_version

    def get_tags_by_category(self, category: str) -> List[str]:
        """Get all tags in a category.

        Args:
            category: Category name

        Returns:
            List of canonical tags in this category
        """
        return self.categories.get(category, [])

    def get_all_tags(self) -> List[str]:
        """Get all canonical tags in vocabulary.

        Returns:
            List of all canonical tag names
        """
        return list(self.seed_tags.keys())

    def get_tag_info(self, tag: str) -> Optional[Dict]:
        """Get detailed information about a tag.

        Args:
            tag: Tag to look up

        Returns:
            Tag info dict, or None if not found
        """
        tag_lower = tag.lower().strip()
        return self.seed_tags.get(tag_lower)

    def find_similar_tags(self, tag: str, threshold: float = 0.7) -> List[str]:
        """Find tags similar to the given tag (simple string similarity).

        Args:
            tag: Tag to find similar tags for
            threshold: Similarity threshold (0-1)

        Returns:
            List of similar canonical tags
        """
        tag_lower = tag.lower().strip()
        similar = []

        for canonical in self.seed_tags.keys():
            # Simple similarity: substring match
            if tag_lower in canonical or canonical in tag_lower:
                similar.append(canonical)

        return similar

    def get_stats(self) -> Dict:
        """Get vocabulary statistics.

        Returns:
            Dict with statistics about the vocabulary
        """
        return {
            "version": self.version,
            "total_tags": len(self.seed_tags),
            "total_occurrences": sum(
                tag["count"] for tag in self.seed_tags.values()
            ),
            "categories": len(self.categories),
            "evolution_events": len(self.evolution_history),
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }

    def export_for_prompt(self, category: Optional[str] = None, top_n: int = 50) -> str:
        """Export vocabulary in a format suitable for LLM prompts.

        Args:
            category: Optional category to filter by
            top_n: Maximum number of tags to include

        Returns:
            Formatted string for prompt inclusion
        """
        if category:
            tags = self.get_tags_by_category(category)
            tag_items = [
                (tag, self.seed_tags[tag]["count"])
                for tag in tags
                if tag in self.seed_tags
            ]
        else:
            tag_items = [
                (tag, info["count"]) for tag, info in self.seed_tags.items()
            ]

        # Sort by count descending
        tag_items.sort(key=lambda x: x[1], reverse=True)

        # Take top N
        tag_items = tag_items[:top_n]

        # Format
        lines = []
        if category:
            lines.append(f"Category: {category}")
        lines.append("Tags (by frequency):")
        for tag, count in tag_items:
            lines.append(f"  - {tag} ({count})")

        return "\n".join(lines)


def load_vocabulary(path: Path) -> VocabularyManager:
    """Load vocabulary from file.

    Args:
        path: Path to vocabulary JSON file

    Returns:
        Loaded VocabularyManager instance
    """
    return VocabularyManager(vocabulary_path=path)
