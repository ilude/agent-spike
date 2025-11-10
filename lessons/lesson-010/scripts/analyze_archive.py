"""Analyze existing archive tags and generate seed vocabulary."""

import json
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path
from typing import Dict, List, Set, Tuple

# Add project root to path
project_root = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(project_root))


class ArchiveAnalyzer:
    """Analyze tags and metadata across the archive."""

    def __init__(self, archive_path: Path):
        self.archive_path = archive_path
        self.videos: List[Dict] = []
        self.format_stats = Counter()
        self.all_tags = Counter()
        self.structured_fields = defaultdict(Counter)
        self.variations = defaultdict(set)

    def load_archives(self) -> None:
        """Load all JSON files from archive directories."""
        print(f"Loading archives from: {self.archive_path}")

        json_files = list(self.archive_path.glob("**/*.json"))
        print(f"Found {len(json_files)} archive files")

        for json_file in json_files:
            try:
                with open(json_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    self.videos.append(data)
            except Exception as e:
                print(f"Error loading {json_file}: {e}")

        print(f"Loaded {len(self.videos)} videos")

    def detect_format(self, video_data: Dict) -> str:
        """Detect tag format: old, new, both, or none."""
        llm_outputs = video_data.get("llm_outputs", [])

        has_old = any(
            output.get("output_type") == "tags"
            for output in llm_outputs
        )
        has_new = any(
            output.get("output_type") in ["structured_metadata", "metadata"]
            for output in llm_outputs
        )

        if has_old and has_new:
            return "both"
        elif has_new:
            return "new"
        elif has_old:
            return "old"
        else:
            return "none"

    def extract_tags_old_format(self, output_value) -> List[str]:
        """Extract tags from old format (JSON string with tags array or comma-separated)."""
        if isinstance(output_value, str):
            # Try to parse as JSON first
            try:
                data = json.loads(output_value)
                if isinstance(data, dict) and "tags" in data:
                    tags = data["tags"]
                    if isinstance(tags, list):
                        return [str(tag).strip() for tag in tags if tag]
                    return []
            except json.JSONDecodeError:
                # Fall back to comma-separated
                tags = [tag.strip() for tag in output_value.split(",")]
                return [tag for tag in tags if tag]
        elif isinstance(output_value, list):
            # Already a list
            return [str(tag).strip() for tag in output_value if tag]
        else:
            return []

    def extract_tags_new_format(self, output_value) -> Dict[str, List[str]]:
        """Extract tags from new structured format."""
        if isinstance(output_value, str):
            try:
                output_value = json.loads(output_value)
            except json.JSONDecodeError:
                return {}

        if not isinstance(output_value, dict):
            return {}

        extracted = {}

        # Extract subject_matter
        subject = output_value.get("subject_matter", [])
        if isinstance(subject, list):
            extracted["subject_matter"] = subject

        # Extract entities
        entities = output_value.get("entities", {})
        if isinstance(entities, dict):
            all_entities = []
            for key, values in entities.items():
                if isinstance(values, list):
                    all_entities.extend(values)
            extracted["entities"] = all_entities

        # Extract techniques/concepts
        techniques = output_value.get("techniques_or_concepts", [])
        if isinstance(techniques, list):
            extracted["techniques"] = techniques

        # Extract tools/materials
        tools = output_value.get("tools_or_materials", [])
        if isinstance(tools, list):
            extracted["tools"] = tools

        # Extract tags if present
        tags = output_value.get("tags", [])
        if isinstance(tags, list):
            extracted["tags"] = tags

        return extracted

    def normalize_tag(self, tag: str) -> str:
        """Basic normalization: lowercase, strip whitespace."""
        return tag.lower().strip()

    def analyze_all(self) -> None:
        """Run full analysis on all videos."""
        print("\nAnalyzing tags...")

        for video in self.videos:
            format_type = self.detect_format(video)
            self.format_stats[format_type] += 1

            llm_outputs = video.get("llm_outputs", [])

            for output in llm_outputs:
                output_type = output.get("output_type", "")
                output_value = output.get("output_value", "")

                # Extract old format tags
                if output_type == "tags":
                    tags = self.extract_tags_old_format(output_value)
                    for tag in tags:
                        normalized = self.normalize_tag(tag)
                        self.all_tags[normalized] += 1
                        self.variations[normalized].add(tag)

                # Extract new format tags
                elif output_type in ["structured_metadata", "metadata"]:
                    structured = self.extract_tags_new_format(output_value)

                    for field, tags in structured.items():
                        for tag in tags:
                            if isinstance(tag, str):
                                normalized = self.normalize_tag(tag)
                                self.all_tags[normalized] += 1
                                self.structured_fields[field][normalized] += 1
                                self.variations[normalized].add(tag)

    def find_tag_variations(self) -> Dict[str, List[str]]:
        """Find tags that are variations of each other."""
        variation_groups = {}

        for normalized, originals in self.variations.items():
            if len(originals) > 1:
                variation_groups[normalized] = sorted(originals)

        return variation_groups

    def cluster_by_category(self) -> Dict[str, List[Tuple[str, int]]]:
        """Cluster tags into semantic categories (simple keyword-based)."""
        categories = {
            "AI/ML Concepts": [],
            "Tools & Frameworks": [],
            "Companies & People": [],
            "Techniques & Patterns": [],
            "Content Types": [],
            "Domains": [],
            "Other": [],
        }

        # Simple keyword matching (can be improved)
        ai_keywords = {"ai", "agent", "llm", "rag", "embedding", "model", "gpt", "claude", "neural", "machine-learning"}
        tool_keywords = {"langchain", "llamaindex", "openai", "anthropic", "python", "framework", "library", "tool"}
        company_keywords = {"google", "microsoft", "meta", "anthropic", "openai", "nvidia", "amazon"}
        technique_keywords = {"prompt", "engineering", "fine-tuning", "rag", "retrieval", "optimization", "evaluation"}
        content_keywords = {"tutorial", "demo", "review", "news", "interview", "guide", "walkthrough"}
        domain_keywords = {"web", "development", "devops", "security", "data", "backend", "frontend"}

        for tag, count in self.all_tags.most_common():
            tag_lower = tag.lower()

            # Check which category matches
            if any(kw in tag_lower for kw in ai_keywords):
                categories["AI/ML Concepts"].append((tag, count))
            elif any(kw in tag_lower for kw in tool_keywords):
                categories["Tools & Frameworks"].append((tag, count))
            elif any(kw in tag_lower for kw in company_keywords):
                categories["Companies & People"].append((tag, count))
            elif any(kw in tag_lower for kw in technique_keywords):
                categories["Techniques & Patterns"].append((tag, count))
            elif any(kw in tag_lower for kw in content_keywords):
                categories["Content Types"].append((tag, count))
            elif any(kw in tag_lower for kw in domain_keywords):
                categories["Domains"].append((tag, count))
            else:
                categories["Other"].append((tag, count))

        return categories

    def generate_seed_vocabulary(self, top_n: int = 50) -> Dict:
        """Generate seed vocabulary from analysis."""
        # Get top N most frequent tags
        top_tags = self.all_tags.most_common(top_n)

        # Cluster by category
        categories = self.cluster_by_category()

        # Build vocabulary structure
        vocabulary = {
            "version": "v1",
            "created_at": None,  # Will be set when saved
            "total_tags": len(self.all_tags),
            "seed_tags": {},
            "categories": {},
        }

        # Add seed tags with metadata
        for tag, count in top_tags:
            vocabulary["seed_tags"][tag] = {
                "canonical_form": tag,
                "count": count,
                "confidence": min(count / 10.0, 1.0),  # Simple confidence score
                "aliases": list(self.variations.get(tag, {tag})),
            }

        # Add category information
        for category, tags in categories.items():
            if tags:
                vocabulary["categories"][category] = [tag for tag, _ in tags[:20]]

        return vocabulary

    def generate_report(self) -> str:
        """Generate comprehensive markdown report."""
        lines = []

        lines.append("# Archive Tag Analysis Report\n")
        lines.append("## Executive Summary\n")
        lines.append(f"- **Total videos analyzed**: {len(self.videos)}")
        lines.append(f"- **Total unique tags**: {len(self.all_tags)}")
        lines.append(f"- **Total tag occurrences**: {sum(self.all_tags.values())}")
        lines.append(f"- **Average tags per video**: {sum(self.all_tags.values()) / max(len(self.videos), 1):.1f}\n")

        lines.append("## Format Distribution\n")
        total = sum(self.format_stats.values())
        for format_type, count in self.format_stats.most_common():
            pct = (count / total * 100) if total > 0 else 0
            lines.append(f"- **{format_type}**: {count} ({pct:.1f}%)")
        lines.append("")

        lines.append("## Top 50 Most Frequent Tags\n")
        lines.append("| Rank | Tag | Count | % of Videos |")
        lines.append("|------|-----|-------|-------------|")
        for i, (tag, count) in enumerate(self.all_tags.most_common(50), 1):
            pct = (count / len(self.videos) * 100) if len(self.videos) > 0 else 0
            lines.append(f"| {i} | {tag} | {count} | {pct:.1f}% |")
        lines.append("")

        lines.append("## Structured Field Distribution\n")
        for field, tags in self.structured_fields.items():
            lines.append(f"\n### {field.replace('_', ' ').title()}\n")
            lines.append(f"Total unique: {len(tags)}\n")
            lines.append("Top 10:")
            for tag, count in tags.most_common(10):
                lines.append(f"- {tag}: {count}")
        lines.append("")

        lines.append("## Tag Variations (Need Normalization)\n")
        variations = self.find_tag_variations()
        if variations:
            lines.append(f"Found {len(variations)} tags with variations:\n")
            for normalized, originals in sorted(variations.items())[:20]:
                lines.append(f"- **{normalized}**: {', '.join(f'`{o}`' for o in originals)}")
        else:
            lines.append("No significant variations found.")
        lines.append("")

        lines.append("## Tag Categories\n")
        categories = self.cluster_by_category()
        for category, tags in categories.items():
            if tags:
                lines.append(f"\n### {category}\n")
                lines.append(f"Total: {len(tags)}\n")
                lines.append("Top 10:")
                for tag, count in tags[:10]:
                    lines.append(f"- {tag} ({count})")
        lines.append("")

        lines.append("## Recommendations\n")
        lines.append("### Should we use a seed vocabulary?\n")
        lines.append("**YES** - For the following reasons:\n")
        lines.append(f"1. **High frequency concentration**: Top 50 tags cover a significant portion of usage")
        lines.append(f"2. **Domain focus**: Content is primarily AI/ML related, enabling predictable vocabulary")
        lines.append(f"3. **Variation consolidation**: {len(variations)} tags have variations that need normalization")
        lines.append("4. **Better search**: Consistent tags improve search and recommendation quality")
        lines.append("5. **Knowledge graph foundation**: Normalized tags enable relationship mapping\n")
        lines.append("### Proposed Seed Set\n")
        lines.append("- **Size**: 30-50 core tags")
        lines.append("- **Selection criteria**: Frequency, domain coverage, consolidation potential")
        lines.append("- **Evolution**: Track usage, add new tags organically, consolidate variations")
        lines.append("- **Re-tagging**: Trigger when vocabulary significantly improves (v1 → v2)")

        return "\n".join(lines)


def main():
    """Run archive analysis."""
    # Find archive directory
    project_root = Path(__file__).parent.parent.parent.parent
    archive_path = project_root / "projects" / "data" / "archive" / "youtube"

    if not archive_path.exists():
        print(f"Archive path not found: {archive_path}")
        return

    # Run analysis
    analyzer = ArchiveAnalyzer(archive_path)
    analyzer.load_archives()
    analyzer.analyze_all()

    # Generate report
    report = analyzer.generate_report()

    # Save report
    output_path = Path(__file__).parent.parent / "archive_tag_analysis_report.md"
    output_path.write_text(report, encoding="utf-8")
    print(f"\n[OK] Report saved to: {output_path}")

    # Generate seed vocabulary
    vocabulary = analyzer.generate_seed_vocabulary(top_n=50)

    # Save vocabulary
    vocab_path = Path(__file__).parent.parent / "data" / "seed_vocabulary_v1.json"
    vocab_path.parent.mkdir(parents=True, exist_ok=True)

    from datetime import datetime
    vocabulary["created_at"] = datetime.now().isoformat()

    with open(vocab_path, "w", encoding="utf-8") as f:
        json.dump(vocabulary, f, indent=2, ensure_ascii=False)

    print(f"[OK] Seed vocabulary saved to: {vocab_path}")
    print(f"\n[DONE] Analysis complete!")
    print(f"   - {len(analyzer.videos)} videos")
    print(f"   - {len(analyzer.all_tags)} unique tags")
    print(f"   - {len(vocabulary['seed_tags'])} seed tags")


if __name__ == "__main__":
    main()
