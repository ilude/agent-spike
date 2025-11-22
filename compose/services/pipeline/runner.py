"""Pipeline execution and backfill management.

The runner:
1. Executes steps in dependency order
2. Updates Neo4j state after each successful step
3. Provides backfill querying for stale videos
"""

from datetime import datetime
from typing import Optional

from .models import PipelineContext, PipelineConfig, StepResult
from .decorator import get_step, get_all_steps, get_execution_order


def run_pipeline(
    video_id: str,
    url: str,
    steps: Optional[list[str]] = None,
    config: Optional[PipelineConfig] = None,
) -> PipelineContext:
    """Execute pipeline steps for a video.

    Args:
        video_id: YouTube video ID
        url: Video URL
        steps: List of step names to execute (or all if None)
        config: Pipeline configuration

    Returns:
        PipelineContext with results from all executed steps
    """
    config = config or PipelineConfig()

    # Get all registered steps if not specified
    if steps is None:
        steps = list(get_all_steps().keys())

    if not steps:
        ctx = PipelineContext(video_id=video_id, url=url)
        return ctx

    # Get execution order (dependency sorted)
    execution_order = get_execution_order(steps)

    ctx = PipelineContext(video_id=video_id, url=url)

    for step_name in execution_order:
        step_tuple = get_step(step_name)
        if not step_tuple:
            ctx.set_result(step_name, StepResult.fail(f"Step '{step_name}' not found"))
            if not config.continue_on_error:
                break
            continue

        step_func, metadata = step_tuple

        # Check dependencies succeeded
        for dep in metadata.dependencies:
            dep_result = ctx.get_result(dep)
            if not dep_result or not dep_result.success:
                ctx.set_result(
                    step_name,
                    StepResult.fail(f"Dependency '{dep}' failed or missing"),
                )
                if not config.continue_on_error:
                    return ctx
                continue

        # Execute step
        try:
            result = step_func(ctx)
            ctx.set_result(step_name, result)

            # Update Neo4j state if configured
            if config.update_graph and result.success:
                try:
                    _update_graph_state(video_id, step_name, metadata.version_hash)
                except Exception:
                    pass  # Non-fatal, graph update failure shouldn't break pipeline

        except Exception as e:
            result = StepResult.fail(f"{type(e).__name__}: {e}")
            ctx.set_result(step_name, result)

        if not result.success and not config.continue_on_error:
            break

    return ctx


def _update_graph_state(video_id: str, step_name: str, version_hash: str) -> None:
    """Update Neo4j pipeline state for a video.

    Only imports graph module when needed to avoid circular deps.
    """
    try:
        from compose.services.graph import update_pipeline_state
        update_pipeline_state(video_id, step_name, version_hash)
    except ImportError:
        pass  # Graph service not available


def get_backfill_queue(
    step_name: str,
    limit: int = 100,
) -> list[dict]:
    """Get videos that need reprocessing for a step.

    Queries Neo4j for videos where:
    1. The step has never been run
    2. The step was run with an outdated version

    Args:
        step_name: Pipeline step name
        limit: Maximum number of videos to return

    Returns:
        List of dicts with video_id, url, current_version, required_version
    """
    step_tuple = get_step(step_name)
    if not step_tuple:
        raise ValueError(f"Step '{step_name}' not found")

    _, metadata = step_tuple
    current_version = metadata.version_hash

    try:
        from compose.services.graph import find_stale_videos
        stale = find_stale_videos(step_name, current_version, limit)
        return [
            {
                "video_id": s.video_id,
                "url": s.url,
                "current_version": s.current_version,
                "required_version": s.required_version,
            }
            for s in stale
        ]
    except ImportError:
        return []


def get_backfill_counts() -> dict[str, int]:
    """Get count of videos needing reprocessing for each step.

    Returns:
        Dict of step_name -> count of stale videos
    """
    counts = {}

    try:
        from compose.services.graph import count_stale_videos

        for step_name, metadata in get_all_steps().items():
            counts[step_name] = count_stale_videos(step_name, metadata.version_hash)

    except ImportError:
        pass

    return counts


def run_backfill(
    step_name: str,
    batch_size: int = 10,
    config: Optional[PipelineConfig] = None,
) -> dict:
    """Process a batch of stale videos for a step.

    Args:
        step_name: Step to backfill
        batch_size: Number of videos to process
        config: Pipeline configuration

    Returns:
        Summary dict with processed, succeeded, failed counts
    """
    queue = get_backfill_queue(step_name, limit=batch_size)

    summary = {
        "step": step_name,
        "queued": len(queue),
        "succeeded": 0,
        "failed": 0,
        "errors": [],
    }

    for item in queue:
        ctx = run_pipeline(
            video_id=item["video_id"],
            url=item["url"],
            steps=[step_name],
            config=config,
        )

        result = ctx.get_result(step_name)
        if result and result.success:
            summary["succeeded"] += 1
        else:
            summary["failed"] += 1
            if result and result.error:
                summary["errors"].append({
                    "video_id": item["video_id"],
                    "error": result.error,
                })

    return summary
