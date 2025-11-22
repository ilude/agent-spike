"""Chainable ingestion pipeline with automatic versioning.

This pipeline framework provides:
- @pipeline_step decorator for registering steps
- Git-based automatic version detection
- Dependency tracking between steps
- Neo4j integration for backfill queries

Usage:
    from compose.services.pipeline import (
        pipeline_step,
        run_pipeline,
        get_backfill_queue,
        PipelineContext,
        StepResult,
    )

    @pipeline_step()
    def fetch_transcript(ctx: PipelineContext) -> StepResult[str]:
        transcript = get_transcript(ctx.url)
        return StepResult.ok(transcript)

    @pipeline_step(depends_on=["fetch_transcript"])
    def generate_tags(ctx: PipelineContext) -> StepResult[list[str]]:
        transcript = ctx.get_value("fetch_transcript")
        tags = tagger.generate(transcript)
        return StepResult.ok(tags)

    # Execute pipeline
    ctx = run_pipeline("dQw4w9WgXcQ", "https://youtube.com/watch?v=dQw4w9WgXcQ")

    # Find videos needing reprocessing
    queue = get_backfill_queue("generate_tags", limit=100)
"""

from .models import (
    StepResult,
    PipelineContext,
    StepMetadata,
    PipelineConfig,
)

from .decorator import (
    pipeline_step,
    get_step,
    get_all_steps,
    get_step_version,
    get_execution_order,
    clear_registry,
)

from .versioning import (
    get_version_hash,
    get_git_blob_hash,
    get_source_hash,
    invalidate_version_cache,
)

from .runner import (
    run_pipeline,
    get_backfill_queue,
    get_backfill_counts,
    run_backfill,
)

# Import steps to register them
from . import steps
from .steps import (
    fetch_transcript,
    fetch_metadata,
    archive_raw,
    generate_tags,
    cache_to_qdrant,
    update_graph,
    DEFAULT_PIPELINE_STEPS,
    MINIMAL_PIPELINE_STEPS,
)

__all__ = [
    # Models
    "StepResult",
    "PipelineContext",
    "StepMetadata",
    "PipelineConfig",
    # Decorator
    "pipeline_step",
    "get_step",
    "get_all_steps",
    "get_step_version",
    "get_execution_order",
    "clear_registry",
    # Versioning
    "get_version_hash",
    "get_git_blob_hash",
    "get_source_hash",
    "invalidate_version_cache",
    # Runner
    "run_pipeline",
    "get_backfill_queue",
    "get_backfill_counts",
    "run_backfill",
    # Steps
    "fetch_transcript",
    "fetch_metadata",
    "archive_raw",
    "generate_tags",
    "cache_to_qdrant",
    "update_graph",
    "DEFAULT_PIPELINE_STEPS",
    "MINIMAL_PIPELINE_STEPS",
]
