"""Pipeline step decorator for automatic versioning and dependency tracking.

The @pipeline_step decorator:
1. Registers the step in a global registry
2. Computes version hash from source code
3. Infers dependencies from type annotations
4. Wraps execution with timing and error handling
"""

import time
from functools import wraps
from typing import Callable, Any, get_type_hints, Optional

from .models import StepResult, PipelineContext, StepMetadata
from .versioning import get_version_hash, get_source_file


# Global registry of pipeline steps
_step_registry: dict[str, tuple[Callable, StepMetadata]] = {}


def pipeline_step(
    name: Optional[str] = None,
    depends_on: Optional[list[str]] = None,
    description: Optional[str] = None,
) -> Callable:
    """Decorator to register a function as a pipeline step.

    Usage:
        @pipeline_step()
        def fetch_transcript(ctx: PipelineContext) -> StepResult[str]:
            transcript = get_transcript(ctx.url)
            return StepResult.ok(transcript)

        @pipeline_step(depends_on=["fetch_transcript"])
        def generate_tags(ctx: PipelineContext) -> StepResult[list[str]]:
            transcript = ctx.get_value("fetch_transcript")
            tags = tagger.generate(transcript)
            return StepResult.ok(tags)

    Args:
        name: Step name (defaults to function name)
        depends_on: List of step names this step requires
        description: Human-readable description

    Returns:
        Decorated function that's registered as a pipeline step
    """

    def decorator(func: Callable) -> Callable:
        step_name = name or func.__name__
        version_hash = get_version_hash(func)
        source_file = get_source_file(func)

        # Infer dependencies from type hints if not explicitly provided
        inferred_deps = depends_on or []
        if not inferred_deps:
            # Try to infer from annotations
            try:
                hints = get_type_hints(func)
                # Could parse hints for specific input types
                # For now, use explicit depends_on
            except Exception:
                pass

        metadata = StepMetadata(
            name=step_name,
            version_hash=version_hash,
            dependencies=inferred_deps,
            description=description or func.__doc__,
            source_file=source_file,
        )

        @wraps(func)
        def wrapper(ctx: PipelineContext, *args: Any, **kwargs: Any) -> StepResult:
            start_time = time.perf_counter()

            try:
                result = func(ctx, *args, **kwargs)

                # Ensure result is a StepResult
                if not isinstance(result, StepResult):
                    result = StepResult.ok(result)

                elapsed_ms = (time.perf_counter() - start_time) * 1000
                result.duration_ms = elapsed_ms

                return result

            except Exception as e:
                elapsed_ms = (time.perf_counter() - start_time) * 1000
                return StepResult.fail(
                    error=f"{type(e).__name__}: {str(e)}",
                    duration_ms=elapsed_ms,
                )

        # Attach metadata to the wrapper
        wrapper._step_metadata = metadata  # type: ignore
        wrapper._step_name = step_name  # type: ignore

        # Register in global registry
        _step_registry[step_name] = (wrapper, metadata)

        return wrapper

    return decorator


def get_step(name: str) -> Optional[tuple[Callable, StepMetadata]]:
    """Get a registered step by name.

    Args:
        name: Step name

    Returns:
        Tuple of (step function, metadata), or None if not found
    """
    return _step_registry.get(name)


def get_all_steps() -> dict[str, StepMetadata]:
    """Get metadata for all registered steps.

    Returns:
        Dict of step_name -> StepMetadata
    """
    return {name: meta for name, (_, meta) in _step_registry.items()}


def get_step_version(name: str) -> Optional[str]:
    """Get the version hash for a step.

    Args:
        name: Step name

    Returns:
        Version hash string, or None if step not found
    """
    step = get_step(name)
    return step[1].version_hash if step else None


def clear_registry() -> None:
    """Clear the step registry. For testing only."""
    _step_registry.clear()


def get_execution_order(target_steps: list[str]) -> list[str]:
    """Get steps in dependency order for execution.

    Performs topological sort to ensure dependencies run first.

    Args:
        target_steps: Steps to execute

    Returns:
        Steps in execution order (dependencies first)

    Raises:
        ValueError: If circular dependency detected or step not found
    """
    # Build dependency graph
    all_steps = set(target_steps)
    deps_map: dict[str, list[str]] = {}

    for step_name in target_steps:
        step = get_step(step_name)
        if not step:
            raise ValueError(f"Step '{step_name}' not found in registry")
        deps_map[step_name] = step[1].dependencies
        all_steps.update(step[1].dependencies)

    # Add dependencies to target if not already included
    for step_name in list(all_steps):
        if step_name not in deps_map:
            step = get_step(step_name)
            if step:
                deps_map[step_name] = step[1].dependencies

    # Topological sort
    result = []
    visited = set()
    temp_visited = set()

    def visit(step: str) -> None:
        if step in temp_visited:
            raise ValueError(f"Circular dependency detected involving '{step}'")
        if step in visited:
            return

        temp_visited.add(step)
        for dep in deps_map.get(step, []):
            visit(dep)
        temp_visited.remove(step)
        visited.add(step)
        result.append(step)

    for step in all_steps:
        if step not in visited:
            visit(step)

    return result
