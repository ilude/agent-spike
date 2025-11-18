# Archive Reprocessing System

Flexible, version-tracked system for reprocessing archive data with metadata transformations.

## Overview

This system solves the problem of applying new transformations to existing archive data without duplicating code or losing track of what's been processed. It uses semantic versioning instead of git hashes to work during active development.

### Key Components

1. **Version Tracking** (`transform_versions.py`)
   - Central registry of transformation versions
   - Semantic versioning for all transformations, models, and schemas
   - Manifest generation for staleness detection

2. **Metadata Transformers** (`metadata_transformers.py`)
   - Strategy pattern for pluggable transformations
   - Pre-built transformers: QdrantMetadataFlattener, RecommendationWeightCalculator
   - Composable with version dependencies

3. **Reprocessing Pipeline** (`reprocessing_pipeline.py`)
   - Template Method pattern for reprocessing workflows
   - Automatic staleness detection and incremental processing
   - Observer hooks for progress tracking
   - Error handling and statistics

4. **Archive Models** (`compose/services/archive/models.py`)
   - Extended with `DerivedOutput` support
   - Tracks transformation versions and manifests
   - Enables staleness detection per-archive

## Design Patterns Used

### Strategy Pattern (MetadataTransformer)
- **Problem**: Copy-paste transformation logic across multiple scripts
- **Solution**: Extract to reusable transformer classes
- **Benefit**: Single source of truth, easy to test, composable

### Template Method Pattern (ReprocessingPipeline)
- **Problem**: Boilerplate iteration, error handling, progress tracking
- **Solution**: Base class handles common logic, subclasses implement specifics
- **Benefit**: Consistent behavior, less duplication, easier to extend

### Observer Pattern (ReprocessingHooks)
- **Problem**: Need visibility into reprocessing progress
- **Solution**: Hooks for lifecycle events (start, skip, success, error, complete)
- **Benefit**: Console output, logging, metrics collection

## Version Tracking

Version tracking uses semantic versioning that works during experimentation:

```python
# compose/lib/reprocessing/transform_versions.py
VERSIONS = {
    "normalizer": "v1.0",        # Bump when normalization logic changes
    "vocabulary": "v1",           # Bump when vocabulary updated
    "llm_model": "claude-3-5-haiku-20241022",  # Track model changes
}
```

**When to bump versions:**
- Logic changes: Bump transformer version (e.g., normalizer v1.0 → v1.1)
- Vocabulary updates: Bump vocabulary version (v1 → v2)
- Model changes: Update model string
- Breaking changes: Bump major version (v1.x → v2.0)

**How staleness detection works:**
1. Each derived output stores a transform_manifest (snapshot of all versions)
2. When reprocessing, compare stored manifest to current manifest
3. If any tracked version changed, reprocess that archive
4. Skip archives with up-to-date versions (incremental processing)

## Usage

### Built-in Scripts

**Reprocess Qdrant metadata:**
```bash
# Dry run (show what would be reprocessed)
uv run python compose/cli/reprocess_qdrant_metadata.py --dry-run

# Reprocess all archives
uv run python compose/cli/reprocess_qdrant_metadata.py

# Test on first 10 archives
uv run python compose/cli/reprocess_qdrant_metadata.py --limit 10
```

**Reprocess with lesson-010 normalizer:**
```bash
# Dry run
uv run python compose/cli/reprocess_normalized_tags.py --dry-run --limit 5

# Full reprocessing (all archives)
uv run python compose/cli/reprocess_normalized_tags.py

# Skip semantic context (faster, lower quality)
uv run python compose/cli/reprocess_normalized_tags.py --no-context
```

### Writing Custom Pipelines

Create a subclass of `BaseReprocessingPipeline`:

```python
from compose.lib.reprocessing.reprocessing_pipeline import BaseReprocessingPipeline, ConsoleHooks
from compose.services.archive import YouTubeArchive
import json

class MyCustomPipeline(BaseReprocessingPipeline):
    def get_output_type(self) -> str:
        """Output type for derived outputs."""
        return "my_transformation_v1"

    def get_version_keys(self) -> list[str]:
        """Version keys to check for staleness."""
        return ["my_transformer", "llm_model"]

    def get_source_outputs(self, archive: YouTubeArchive) -> list[str]:
        """Source outputs used in transformation."""
        return ["tags"]  # Uses tags from llm_outputs

    def process_archive(self, archive: YouTubeArchive) -> str:
        """Transform archive data.

        Returns:
            JSON-serialized output
        """
        # Your transformation logic here
        result = {"transformed": True}
        return json.dumps(result)

# Run it
pipeline = MyCustomPipeline(hooks=ConsoleHooks())
stats = pipeline.run(limit=10)
```

### Creating Custom Transformers

Implement the `MetadataTransformer` protocol:

```python
from compose.lib.reprocessing.metadata_transformers import BaseTransformer
from compose.lib.reprocessing.transform_versions import get_version

class MyCustomTransformer(BaseTransformer):
    def get_version(self) -> str:
        return get_version("my_transformer")

    def get_dependencies(self) -> list[str]:
        return ["vocabulary", "llm_model"]

    def transform(self, archive_data: dict) -> dict:
        # Transform logic
        return {"transformed_field": "value"}

# Use it
transformer = MyCustomTransformer()
metadata = transformer.transform(archive_data)
```

## File Structure

```
compose/lib/reprocessing/
├── README.md                      # This file
├── transform_versions.py          # Central version registry
├── metadata_transformers.py       # Strategy pattern transformers
└── reprocessing_pipeline.py       # Template Method base class

compose/cli/
├── reprocess_qdrant_metadata.py   # Qdrant metadata reprocessing
└── reprocess_normalized_tags.py   # lesson-010 normalization reprocessing

compose/services/archive/
├── models.py                      # Extended with DerivedOutput
└── local_writer.py                # Extended with add_derived_output()
```

## Archive Data Structure

Archives now support three types of outputs:

```json
{
  "video_id": "abc123",
  "raw_transcript": "...",

  "llm_outputs": [
    {
      "output_type": "tags",
      "output_value": "...",
      "model": "claude-3-5-haiku-20241022",
      "cost_usd": 0.0012
    }
  ],

  "derived_outputs": [
    {
      "output_type": "normalized_metadata_v1",
      "output_value": "...",
      "transformer_version": "v1.0+v1",
      "transform_manifest": {
        "normalizer": "v1.0",
        "vocabulary": "v1",
        "created_at": "2025-11-10T..."
      },
      "source_outputs": ["tags"]
    }
  ],

  "processing_history": [
    {
      "version": "v1_full_embed",
      "collection_name": "cached_content",
      "processed_at": "2025-11-10T..."
    }
  ]
}
```

## Performance

**Incremental processing** is the key win:
- First run: Processes all 470 videos (~12 minutes for Qdrant metadata)
- Subsequent runs: Skips up-to-date archives (seconds)
- After version bump: Only reprocesses affected archives

**Example:**
```bash
# First run: Process all 470 videos
uv run python compose/cli/reprocess_qdrant_metadata.py
# Processed: 470, Skipped: 0, Errors: 0 (12 minutes)

# Second run: All up-to-date
uv run python compose/cli/reprocess_qdrant_metadata.py
# Processed: 0, Skipped: 470, Errors: 0 (5 seconds)

# After bumping qdrant_flattener to v1.1
uv run python compose/cli/reprocess_qdrant_metadata.py
# Processed: 470, Skipped: 0, Errors: 0 (12 minutes)
```

## Extending the System

### Adding New Transformers

1. Add version to `transform_versions.py`:
   ```python
   VERSIONS = {
       "my_transformer": "v1.0",  # New transformer
   }
   ```

2. Create transformer class in `metadata_transformers.py`:
   ```python
   class MyTransformer(BaseTransformer):
       def get_version(self) -> str:
           return get_version("my_transformer")

       def transform(self, archive_data: dict) -> dict:
           # Your logic here
           pass
   ```

3. Create reprocessing script:
   ```python
   class MyReprocessor(BaseReprocessingPipeline):
       def get_output_type(self) -> str:
           return "my_output_v1"

       def get_version_keys(self) -> list[str]:
           return ["my_transformer"]

       def process_archive(self, archive: YouTubeArchive) -> str:
           transformer = MyTransformer()
           result = transformer.transform(archive.model_dump())
           return json.dumps(result)
   ```

### Adding Hooks for Monitoring

```python
class MetricsHooks:
    """Track metrics during reprocessing."""

    def __init__(self):
        self.start_time = None
        self.errors = []

    def on_start(self, total_archives: int):
        self.start_time = time.time()
        print(f"Starting {total_archives} archives...")

    def on_archive_error(self, video_id: str, error: Exception):
        self.errors.append((video_id, str(error)))

    def on_complete(self, stats: dict):
        elapsed = time.time() - self.start_time
        print(f"Completed in {elapsed:.2f}s")
        print(f"Errors: {len(self.errors)}")
        for video_id, error in self.errors:
            print(f"  {video_id}: {error}")

# Use it
pipeline = MyPipeline(hooks=MetricsHooks())
pipeline.run()
```

## Comparison to Old Approach

**Before (reingest_from_archive.py):**
- ❌ Hardcoded logic for specific transformation
- ❌ Copy-pasted flattening code across 3+ scripts
- ❌ No version tracking (regenerates everything)
- ❌ No staleness detection (wasteful reprocessing)
- ❌ No progress visibility

**After (reprocessing system):**
- ✅ Strategy pattern for reusable transformers
- ✅ Single source of truth for transformations
- ✅ Semantic version tracking with manifests
- ✅ Incremental processing (skip up-to-date archives)
- ✅ Observer hooks for progress, errors, metrics
- ✅ Template Method reduces boilerplate
- ✅ Works during development (not git-dependent)

## Future Enhancements

Potential improvements (not implemented):

1. **Parallel processing**: Process multiple archives concurrently
   - **Decision**: Not needed (12min for 470 videos is fine, incremental is the real win)

2. **Map-reduce pattern**: Distribute across workers
   - **Decision**: Over-engineering for current scale

3. **Cache invalidation**: Auto-detect when Qdrant cache is stale
   - **Could add**: Compare derived_outputs manifest to cache metadata

4. **Rollback support**: Revert to previous vocabulary version
   - **Already supported**: Vocabulary versioning (v1, v2, etc.)

5. **Dry-run diffs**: Show what would change
   - **Partially done**: --dry-run shows what would be processed

## Summary

This system provides a **good enough** solution for reprocessing archives with version tracking that works during experimentation. It eliminates copy-paste violations, enables incremental processing, and makes it easy to add new transformations without modifying existing code.

**Key wins:**
- Semantic versioning (works during development)
- Incremental processing (skip unchanged archives)
- Strategy pattern (reusable transformers)
- Template Method (consistent pipelines)
- Observer hooks (visibility and metrics)

**Non-goals:**
- Parallelization (12min is acceptable)
- Distributed processing (single machine is fine)
- Git integration (semantic versions are better for iteration)
