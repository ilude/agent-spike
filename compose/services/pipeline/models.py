"""Pipeline data models.

Defines the core data structures for pipeline steps:
- StepResult: Output from a pipeline step
- PipelineContext: Shared context passed through pipeline
- StepMetadata: Step configuration and version info
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Optional, TypeVar, Generic


T = TypeVar("T")


@dataclass
class StepResult(Generic[T]):
    """Result from executing a pipeline step.

    Attributes:
        value: The output value from the step
        success: Whether the step succeeded
        error: Error message if failed
        duration_ms: Execution time in milliseconds
        cached: Whether result was from cache
    """

    value: Optional[T]
    success: bool = True
    error: Optional[str] = None
    duration_ms: float = 0.0
    cached: bool = False

    @classmethod
    def ok(cls, value: T, duration_ms: float = 0.0, cached: bool = False) -> "StepResult[T]":
        """Create a successful result."""
        return cls(value=value, success=True, duration_ms=duration_ms, cached=cached)

    @classmethod
    def fail(cls, error: str, duration_ms: float = 0.0) -> "StepResult[T]":
        """Create a failed result."""
        return cls(value=None, success=False, error=error, duration_ms=duration_ms)


@dataclass
class PipelineContext:
    """Shared context passed through pipeline execution.

    Holds intermediate results from each step, allowing downstream
    steps to access outputs from upstream steps.

    Attributes:
        video_id: YouTube video ID being processed
        url: Video URL
        results: Dict of step_name -> StepResult
        metadata: Additional metadata
        started_at: Pipeline start time
    """

    video_id: str
    url: str
    results: dict[str, StepResult] = field(default_factory=dict)
    metadata: dict[str, Any] = field(default_factory=dict)
    started_at: datetime = field(default_factory=datetime.now)

    def get_result(self, step_name: str) -> Optional[StepResult]:
        """Get result from a previous step."""
        return self.results.get(step_name)

    def get_value(self, step_name: str) -> Any:
        """Get the value from a previous step's result."""
        result = self.get_result(step_name)
        return result.value if result and result.success else None

    def set_result(self, step_name: str, result: StepResult) -> None:
        """Store a step's result."""
        self.results[step_name] = result

    def has_step(self, step_name: str) -> bool:
        """Check if a step has been executed."""
        return step_name in self.results

    def all_successful(self) -> bool:
        """Check if all executed steps succeeded."""
        return all(r.success for r in self.results.values())


@dataclass
class StepMetadata:
    """Metadata about a pipeline step.

    Attributes:
        name: Step name (derived from function name)
        version_hash: Git-based hash of step code
        dependencies: List of step names this step depends on
        description: Human-readable description
        source_file: Path to source file containing step
    """

    name: str
    version_hash: str
    dependencies: list[str] = field(default_factory=list)
    description: Optional[str] = None
    source_file: Optional[str] = None

    def __hash__(self) -> int:
        return hash((self.name, self.version_hash))


@dataclass
class PipelineConfig:
    """Configuration for pipeline execution.

    Attributes:
        steps: List of step names to execute (in order)
        skip_cached: Skip steps that have already run with current version
        continue_on_error: Continue pipeline if a step fails
        update_graph: Update Neo4j pipeline state after each step
    """

    steps: list[str] = field(default_factory=list)
    skip_cached: bool = True
    continue_on_error: bool = False
    update_graph: bool = True
