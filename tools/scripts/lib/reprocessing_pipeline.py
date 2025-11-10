"""Template Method pattern for archive reprocessing pipelines.

This module provides a base class for building reprocessing workflows that:
1. Read archives from disk
2. Check if reprocessing is needed (version staleness)
3. Apply transformations
4. Update archives and caches
5. Track progress and handle errors

Design pattern: Template Method
- Subclasses implement specific transformation logic
- Base class handles iteration, staleness detection, and error handling
"""

import json
import sys
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any, Dict, Iterator, Optional, Protocol, Tuple

# Add project root to path
project_root = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(project_root))

from tools.services.archive import create_local_archive_writer, YouTubeArchive
from tools.services.archive.local_reader import LocalArchiveReader
from tools.services.archive.config import ArchiveConfig

from .transform_versions import get_transform_manifest, compare_versions, is_stale


class ReprocessingHooks(Protocol):
    """Observer pattern hooks for reprocessing events."""

    def on_start(self, total_archives: int) -> None:
        """Called before reprocessing starts."""
        ...

    def on_archive_start(self, video_id: str, index: int, total: int) -> None:
        """Called before processing each archive."""
        ...

    def on_archive_skip(self, video_id: str, reason: str) -> None:
        """Called when archive is skipped."""
        ...

    def on_archive_success(self, video_id: str, elapsed_seconds: float) -> None:
        """Called after successful processing."""
        ...

    def on_archive_error(self, video_id: str, error: Exception) -> None:
        """Called when archive processing fails."""
        ...

    def on_complete(self, stats: Dict[str, int]) -> None:
        """Called after all archives processed."""
        ...


class BaseReprocessingPipeline(ABC):
    """Base class for archive reprocessing pipelines.

    Implements Template Method pattern:
    - Base class handles iteration, error handling, progress tracking
    - Subclasses implement specific transformation logic

    Subclasses must implement:
    - get_output_type(): Return output type name (e.g., "normalized_metadata_v1")
    - get_version_keys(): Return list of version keys to check for staleness
    - process_archive(): Transform archive data and return output

    Example:
        class MyPipeline(BaseReprocessingPipeline):
            def get_output_type(self) -> str:
                return "my_transformation_v1"

            def get_version_keys(self) -> list[str]:
                return ["my_transformer", "vocabulary"]

            def process_archive(self, archive: YouTubeArchive) -> str:
                # Transform archive data
                return json.dumps({"transformed": True})

        pipeline = MyPipeline()
        stats = pipeline.run()
    """

    def __init__(
        self,
        archive_base_dir: Optional[Path] = None,
        dry_run: bool = False,
        hooks: Optional[ReprocessingHooks] = None,
    ):
        """Initialize reprocessing pipeline.

        Args:
            archive_base_dir: Path to archive directory (default: projects/data/archive)
            dry_run: If True, don't write changes to disk
            hooks: Optional observer hooks for progress tracking
        """
        self.dry_run = dry_run
        self.hooks = hooks

        # Set up archive services
        if archive_base_dir is None:
            archive_base_dir = project_root / "projects" / "data" / "archive"

        archive_config = ArchiveConfig(base_dir=archive_base_dir, organize_by_month=True)
        self.archive_reader = LocalArchiveReader(config=archive_config)
        self.archive_writer = create_local_archive_writer(base_dir=archive_base_dir)

        # Stats tracking
        self.stats = {
            "processed": 0,
            "skipped": 0,
            "errors": 0,
            "total": 0,
        }

    @abstractmethod
    def get_output_type(self) -> str:
        """Get output type name for derived outputs.

        Returns:
            Output type string (e.g., "normalized_metadata_v1")
        """
        pass

    @abstractmethod
    def get_version_keys(self) -> list[str]:
        """Get list of version keys to check for staleness.

        Returns:
            List of keys from transform_versions.VERSIONS
            (e.g., ["normalizer", "vocabulary"])
        """
        pass

    @abstractmethod
    def process_archive(self, archive: YouTubeArchive) -> str:
        """Process archive and return transformed output.

        Args:
            archive: Archive to process

        Returns:
            JSON-serialized output value

        Raises:
            Exception: If processing fails
        """
        pass

    def should_reprocess(self, archive: YouTubeArchive) -> Tuple[bool, str]:
        """Check if archive needs reprocessing.

        Args:
            archive: Archive to check

        Returns:
            Tuple of (should_reprocess, reason)
        """
        # Check if archive has derived output of this type
        existing_output = archive.get_latest_derived_output(self.get_output_type())

        if not existing_output:
            return True, "no existing output"

        # Check version staleness
        stored_manifest = existing_output.transform_manifest
        stale, changed_keys = is_stale(stored_manifest, check_keys=self.get_version_keys())

        if stale:
            return True, f"stale versions: {', '.join(changed_keys)}"

        return False, "up-to-date"

    def iter_archives(self) -> Iterator[Tuple[str, YouTubeArchive]]:
        """Iterate over all archives.

        Yields:
            Tuples of (video_id, archive)
        """
        youtube_dir = self.archive_reader.youtube_dir

        # Search all month directories
        if self.archive_reader.config.organize_by_month:
            for month_dir in sorted(youtube_dir.iterdir()):
                if not month_dir.is_dir():
                    continue
                for archive_file in sorted(month_dir.glob("*.json")):
                    video_id = archive_file.stem
                    archive = self.archive_reader.get(video_id)
                    if archive:
                        yield video_id, archive
        else:
            for archive_file in sorted(youtube_dir.glob("*.json")):
                video_id = archive_file.stem
                archive = self.archive_reader.get(video_id)
                if archive:
                    yield video_id, archive

    def run(self, limit: Optional[int] = None) -> Dict[str, int]:
        """Run reprocessing pipeline.

        Args:
            limit: Optional limit on number of archives to process

        Returns:
            Dict with stats: {processed, skipped, errors, total}
        """
        import time

        # Count total archives
        archives = list(self.iter_archives())
        total = min(len(archives), limit) if limit else len(archives)
        self.stats["total"] = total

        # Notify start
        if self.hooks:
            self.hooks.on_start(total)

        # Process each archive
        for i, (video_id, archive) in enumerate(archives, 1):
            if limit and i > limit:
                break

            # Notify archive start
            if self.hooks:
                self.hooks.on_archive_start(video_id, i, total)

            try:
                # Check if reprocessing needed
                should_process, reason = self.should_reprocess(archive)

                if not should_process:
                    if self.hooks:
                        self.hooks.on_archive_skip(video_id, reason)
                    self.stats["skipped"] += 1
                    continue

                # Process archive
                start_time = time.time()
                output_value = self.process_archive(archive)
                elapsed = time.time() - start_time

                # Update archive with derived output (unless dry run)
                if not self.dry_run:
                    current_manifest = get_transform_manifest()
                    transformer_version = "+".join([
                        current_manifest.get(key, "unknown")
                        for key in self.get_version_keys()
                    ])

                    self.archive_writer.add_derived_output(
                        video_id=video_id,
                        output_type=self.get_output_type(),
                        output_value=output_value,
                        transformer_version=transformer_version,
                        transform_manifest=current_manifest,
                        source_outputs=self.get_source_outputs(archive),
                    )

                # Notify success
                if self.hooks:
                    self.hooks.on_archive_success(video_id, elapsed)
                self.stats["processed"] += 1

            except Exception as e:
                if self.hooks:
                    self.hooks.on_archive_error(video_id, e)
                self.stats["errors"] += 1

        # Notify complete
        if self.hooks:
            self.hooks.on_complete(self.stats)

        return self.stats

    def get_source_outputs(self, archive: YouTubeArchive) -> list[str]:
        """Get list of source output types used in processing.

        Override this to specify which LLM outputs your transformation uses.

        Args:
            archive: Archive being processed

        Returns:
            List of output_type names (e.g., ["tags"])
        """
        return []


class ConsoleHooks:
    """Simple console-based progress hooks."""

    def on_start(self, total_archives: int) -> None:
        print(f"\n{'='*70}")
        print(f"Starting reprocessing pipeline")
        print(f"Total archives: {total_archives}")
        print(f"{'='*70}\n")

    def on_archive_start(self, video_id: str, index: int, total: int) -> None:
        print(f"[{index}/{total}] {video_id}", end=" - ")

    def on_archive_skip(self, video_id: str, reason: str) -> None:
        print(f"SKIP ({reason})")

    def on_archive_success(self, video_id: str, elapsed_seconds: float) -> None:
        print(f"OK ({elapsed_seconds:.2f}s)")

    def on_archive_error(self, video_id: str, error: Exception) -> None:
        print(f"ERROR: {error}")

    def on_complete(self, stats: Dict[str, int]) -> None:
        print(f"\n{'='*70}")
        print(f"Reprocessing complete")
        print(f"{'='*70}")
        print(f"Processed: {stats['processed']}")
        print(f"Skipped: {stats['skipped']}")
        print(f"Errors: {stats['errors']}")
        print(f"Total: {stats['total']}")
        print(f"{'='*70}\n")
