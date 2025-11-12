#!/usr/bin/env python
"""Reprocess archives with lesson-010 tag normalization.

This script applies the two-phase tag normalization system from lesson-010
to all archives, generating normalized metadata with consistent vocabulary.

Usage:
    # Dry run (show what would be reprocessed)
    uv run python tools/scripts/reprocess_normalized_tags.py --dry-run

    # Reprocess all archives
    uv run python tools/scripts/reprocess_normalized_tags.py

    # Reprocess first 10 archives (for testing)
    uv run python tools/scripts/reprocess_normalized_tags.py --limit 10

    # Skip semantic context (faster, lower quality)
    uv run python tools/scripts/reprocess_normalized_tags.py --no-context
"""

import asyncio
import json
import sys
from pathlib import Path
from typing import Optional

# Setup script environment
sys.path.insert(0, str(Path(__file__).parent))
from script_base import setup_script_environment
project_root = setup_script_environment()

from tools.services.archive import YouTubeArchive
from tools.scripts.lib.reprocessing_pipeline import BaseReprocessingPipeline, ConsoleHooks


class NormalizedTagsReprocessor(BaseReprocessingPipeline):
    """Reprocess archives with lesson-010 tag normalization.

    Applies two-phase normalization:
    1. Raw extraction from transcript (if not cached)
    2. Semantic normalization with vocabulary
    """

    def __init__(self, use_context: bool = True, use_vocabulary: bool = True, **kwargs):
        """Initialize normalized tags reprocessor.

        Args:
            use_context: Use semantic context from Qdrant
            use_vocabulary: Use vocabulary for normalization
            **kwargs: Passed to BaseReprocessingPipeline
        """
        super().__init__(**kwargs)
        self.use_context = use_context
        self.use_vocabulary = use_vocabulary

        # Lazy load normalizer (requires async initialization)
        self._normalizer = None
        self._retriever = None
        self._vocabulary = None

    def _ensure_normalizer(self):
        """Ensure normalizer is initialized (lazy loading)."""
        if self._normalizer is not None:
            return

        # Import lesson-010 components
        lesson_010_path = project_root / "lessons" / "lesson-010"
        sys.path.insert(0, str(lesson_010_path))

        from tag_normalizer.normalizer import create_normalizer
        from tag_normalizer.retriever import create_retriever
        from tag_normalizer.vocabulary import load_vocabulary

        # Load vocabulary
        vocab_path = lesson_010_path / "data" / "seed_vocabulary_v1.json"
        if self.use_vocabulary and vocab_path.exists():
            self._vocabulary = load_vocabulary(vocab_path)

        # Create retriever
        if self.use_context:
            try:
                self._retriever = create_retriever()
            except Exception as e:
                print(f"[WARN] Could not create retriever: {e}")
                self._retriever = None

        # Create normalizer
        self._normalizer = create_normalizer(
            retriever=self._retriever,
            vocabulary=self._vocabulary,
        )

    def get_output_type(self) -> str:
        """Output type for derived outputs."""
        return "normalized_metadata_v1"

    def get_version_keys(self) -> list[str]:
        """Version keys to check for staleness."""
        return ["normalizer", "vocabulary", "llm_model"]

    def get_source_outputs(self, archive: YouTubeArchive) -> list[str]:
        """Source outputs used in transformation."""
        # Uses raw structured metadata if available, otherwise transcript
        return ["structured_metadata", "tags"]

    def process_archive(self, archive: YouTubeArchive) -> str:
        """Normalize tags for archive.

        Args:
            archive: Archive to process

        Returns:
            JSON-serialized normalized metadata
        """
        self._ensure_normalizer()

        # Run async normalization
        result = asyncio.run(self._normalize_async(archive))
        return json.dumps(result)

    async def _normalize_async(self, archive: YouTubeArchive) -> dict:
        """Async normalization implementation.

        Args:
            archive: Archive to process

        Returns:
            Dict with normalized metadata
        """
        # Get transcript
        transcript = archive.raw_transcript
        if not transcript:
            raise ValueError("Archive has no transcript")

        # Check if we have cached structured metadata (Phase 1)
        structured_output = archive.get_latest_output("structured_metadata")

        if structured_output:
            # We have cached Phase 1 output, just run Phase 2
            from tag_normalizer.normalizer import StructuredMetadata
            raw_metadata = StructuredMetadata(**json.loads(structured_output.output_value))

            # Get context for normalization
            context_tags = None
            if self.use_context and self._retriever:
                context_tags = self._retriever.get_context_tags(
                    transcript[:1000],
                    limit=5,
                )

            # Get vocabulary tags
            vocabulary_tags = None
            if self.use_vocabulary and self._vocabulary:
                vocabulary_tags = self._vocabulary.get_all_tags()

            # Run Phase 2 only
            normalized = await self._normalizer.normalize_metadata(
                raw_metadata,
                context_tags=context_tags,
                vocabulary_tags=vocabulary_tags,
            )

            return {
                "normalized": normalized.model_dump(mode="json"),
                "source": "cached_phase1",
            }
        else:
            # No cached Phase 1, run full two-phase normalization
            result = await self._normalizer.normalize_from_transcript(
                transcript,
                video_title=archive.youtube_metadata.get("title", "unknown"),
                use_semantic_context=self.use_context,
                use_vocabulary=self.use_vocabulary,
            )

            return {
                "raw": result["raw"].model_dump(mode="json"),
                "normalized": result["normalized"].model_dump(mode="json"),
                "source": "full_pipeline",
            }


def main():
    """Main entry point."""
    import argparse

    parser = argparse.ArgumentParser(
        description="Reprocess archives with lesson-010 tag normalization"
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
    parser.add_argument(
        "--no-context",
        action="store_true",
        help="Skip semantic context (faster, lower quality)",
    )
    parser.add_argument(
        "--no-vocabulary",
        action="store_true",
        help="Skip vocabulary normalization",
    )

    args = parser.parse_args()

    # Create pipeline with console hooks
    pipeline = NormalizedTagsReprocessor(
        use_context=not args.no_context,
        use_vocabulary=not args.no_vocabulary,
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
