#!/usr/bin/env python
"""Reprocess archives to generate Qdrant-compatible metadata.

This script demonstrates the ReprocessingPipeline template with a concrete
implementation for generating Qdrant metadata transformations.

Usage:
    # Dry run (show what would be reprocessed)
    uv run python tools/scripts/reprocess_qdrant_metadata.py --dry-run

    # Reprocess all archives
    uv run python tools/scripts/reprocess_qdrant_metadata.py

    # Reprocess first 10 archives
    uv run python tools/scripts/reprocess_qdrant_metadata.py --limit 10
"""

import json
import sys
from pathlib import Path

# Setup script environment
sys.path.insert(0, str(Path(__file__).parent))
from compose.cli.base import setup_script_environment
setup_script_environment(load_env=False)

from compose.services.archive import YouTubeArchive
from compose.lib.reprocessing.pipeline import BaseReprocessingPipeline, ConsoleHooks
from compose.lib.reprocessing.transformers import create_qdrant_transformer


class QdrantMetadataReprocessor(BaseReprocessingPipeline):
    """Reprocess archives to generate Qdrant metadata.

    Applies QdrantMetadataFlattener + RecommendationWeightCalculator to
    generate flattened metadata for Qdrant filtering.
    """

    def __init__(self, **kwargs):
        """Initialize Qdrant metadata reprocessor."""
        super().__init__(**kwargs)
        self.transformer = create_qdrant_transformer()

    def get_output_type(self) -> str:
        """Output type for derived outputs."""
        return "qdrant_metadata"

    def get_version_keys(self) -> list[str]:
        """Version keys to check for staleness."""
        return ["qdrant_flattener", "weight_calculator", "qdrant_schema"]

    def get_source_outputs(self, archive: YouTubeArchive) -> list[str]:
        """Source outputs used in transformation."""
        return ["tags"]  # Uses tags from llm_outputs

    def process_archive(self, archive: YouTubeArchive) -> str:
        """Transform archive to Qdrant metadata.

        Args:
            archive: Archive to transform

        Returns:
            JSON-serialized Qdrant metadata
        """
        # Convert to dict for transformer
        archive_data = archive.model_dump(mode="json")

        # Apply transformation
        metadata = self.transformer.transform(archive_data)

        # Return as JSON
        return json.dumps(metadata)


def main():
    """Main entry point."""
    import argparse

    parser = argparse.ArgumentParser(
        description="Reprocess archives to generate Qdrant metadata"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be reprocessed without writing changes",
    )
    parser.add_argument(
        "--limit",
        type=int,
        help="Limit number of archives to process (for testing)",
    )

    args = parser.parse_args()

    # Create pipeline with console hooks
    pipeline = QdrantMetadataReprocessor(
        dry_run=args.dry_run,
        hooks=ConsoleHooks(),
    )

    # Run reprocessing
    stats = pipeline.run(limit=args.limit)

    # Exit with error code if there were errors
    if stats["errors"] > 0:
        sys.exit(1)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\nInterrupted by user. Exiting...")
        sys.exit(0)
