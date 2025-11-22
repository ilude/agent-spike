"""Unit tests for pipeline framework.

Tests the core pipeline functionality:
- Step registration and metadata
- Version hashing
- Dependency ordering
- Pipeline execution
"""

import pytest
from compose.services.pipeline import (
    pipeline_step,
    get_step,
    get_all_steps,
    get_execution_order,
    clear_registry,
    run_pipeline,
    StepResult,
    PipelineContext,
    PipelineConfig,
    get_version_hash,
    get_source_hash,
)


@pytest.fixture(autouse=True)
def clean_registry():
    """Clean the step registry before and after each test."""
    clear_registry()
    yield
    clear_registry()


class TestStepResult:
    """Tests for StepResult dataclass."""

    def test_ok_result(self):
        result = StepResult.ok("success")
        assert result.success is True
        assert result.value == "success"
        assert result.error is None

    def test_fail_result(self):
        result = StepResult.fail("something broke")
        assert result.success is False
        assert result.value is None
        assert result.error == "something broke"

    def test_ok_with_duration(self):
        result = StepResult.ok("data", duration_ms=100.5)
        assert result.duration_ms == 100.5

    def test_ok_with_cached_flag(self):
        result = StepResult.ok("cached_data", cached=True)
        assert result.cached is True


class TestPipelineContext:
    """Tests for PipelineContext."""

    def test_context_creation(self):
        ctx = PipelineContext(video_id="abc123", url="https://test.com")
        assert ctx.video_id == "abc123"
        assert ctx.url == "https://test.com"
        assert ctx.results == {}

    def test_set_and_get_result(self):
        ctx = PipelineContext(video_id="abc123", url="https://test.com")
        result = StepResult.ok("test_value")
        ctx.set_result("step1", result)

        assert ctx.has_step("step1")
        assert ctx.get_result("step1") == result
        assert ctx.get_value("step1") == "test_value"

    def test_get_missing_result(self):
        ctx = PipelineContext(video_id="abc123", url="https://test.com")
        assert ctx.get_result("missing") is None
        assert ctx.get_value("missing") is None

    def test_all_successful(self):
        ctx = PipelineContext(video_id="abc123", url="https://test.com")
        ctx.set_result("step1", StepResult.ok("a"))
        ctx.set_result("step2", StepResult.ok("b"))
        assert ctx.all_successful() is True

    def test_all_successful_with_failure(self):
        ctx = PipelineContext(video_id="abc123", url="https://test.com")
        ctx.set_result("step1", StepResult.ok("a"))
        ctx.set_result("step2", StepResult.fail("error"))
        assert ctx.all_successful() is False


class TestPipelineStepDecorator:
    """Tests for @pipeline_step decorator."""

    def test_step_registration(self):
        @pipeline_step()
        def my_step(ctx: PipelineContext) -> StepResult:
            return StepResult.ok("done")

        step = get_step("my_step")
        assert step is not None
        func, metadata = step
        assert metadata.name == "my_step"

    def test_step_custom_name(self):
        @pipeline_step(name="custom_name")
        def some_function(ctx: PipelineContext) -> StepResult:
            return StepResult.ok("done")

        step = get_step("custom_name")
        assert step is not None

    def test_step_with_dependencies(self):
        @pipeline_step()
        def step_a(ctx: PipelineContext) -> StepResult:
            return StepResult.ok("a")

        @pipeline_step(depends_on=["step_a"])
        def step_b(ctx: PipelineContext) -> StepResult:
            return StepResult.ok("b")

        step = get_step("step_b")
        assert step is not None
        _, metadata = step
        assert "step_a" in metadata.dependencies

    def test_step_version_hash(self):
        @pipeline_step()
        def versioned_step(ctx: PipelineContext) -> StepResult:
            return StepResult.ok("done")

        step = get_step("versioned_step")
        _, metadata = step
        assert metadata.version_hash is not None
        assert len(metadata.version_hash) == 12


class TestVersionHashing:
    """Tests for version hashing functions."""

    def test_source_hash_deterministic(self):
        def test_func():
            pass

        hash1 = get_source_hash(test_func)
        hash2 = get_source_hash(test_func)
        assert hash1 == hash2

    def test_version_hash_returns_string(self):
        def test_func():
            pass

        version = get_version_hash(test_func)
        assert isinstance(version, str)
        assert len(version) == 12


class TestExecutionOrder:
    """Tests for dependency-based execution ordering."""

    def test_simple_chain(self):
        @pipeline_step()
        def step_a(ctx: PipelineContext) -> StepResult:
            return StepResult.ok("a")

        @pipeline_step(depends_on=["step_a"])
        def step_b(ctx: PipelineContext) -> StepResult:
            return StepResult.ok("b")

        @pipeline_step(depends_on=["step_b"])
        def step_c(ctx: PipelineContext) -> StepResult:
            return StepResult.ok("c")

        order = get_execution_order(["step_c"])
        assert order == ["step_a", "step_b", "step_c"]

    def test_independent_steps(self):
        @pipeline_step()
        def independent_a(ctx: PipelineContext) -> StepResult:
            return StepResult.ok("a")

        @pipeline_step()
        def independent_b(ctx: PipelineContext) -> StepResult:
            return StepResult.ok("b")

        order = get_execution_order(["independent_a", "independent_b"])
        assert set(order) == {"independent_a", "independent_b"}

    def test_diamond_dependency(self):
        @pipeline_step()
        def diamond_root(ctx: PipelineContext) -> StepResult:
            return StepResult.ok("root")

        @pipeline_step(depends_on=["diamond_root"])
        def diamond_left(ctx: PipelineContext) -> StepResult:
            return StepResult.ok("left")

        @pipeline_step(depends_on=["diamond_root"])
        def diamond_right(ctx: PipelineContext) -> StepResult:
            return StepResult.ok("right")

        @pipeline_step(depends_on=["diamond_left", "diamond_right"])
        def diamond_end(ctx: PipelineContext) -> StepResult:
            return StepResult.ok("end")

        order = get_execution_order(["diamond_end"])
        assert order[0] == "diamond_root"
        assert order[-1] == "diamond_end"
        assert set(order[1:3]) == {"diamond_left", "diamond_right"}

    def test_missing_step_raises(self):
        with pytest.raises(ValueError, match="not found"):
            get_execution_order(["nonexistent_step"])


class TestPipelineExecution:
    """Tests for pipeline execution."""

    def test_simple_pipeline(self):
        @pipeline_step()
        def simple_step(ctx: PipelineContext) -> StepResult:
            return StepResult.ok(f"processed {ctx.video_id}")

        config = PipelineConfig(update_graph=False)
        ctx = run_pipeline("test123", "https://test.com", steps=["simple_step"], config=config)

        assert ctx.all_successful()
        assert ctx.get_value("simple_step") == "processed test123"

    def test_chained_pipeline(self):
        @pipeline_step()
        def chain_first(ctx: PipelineContext) -> StepResult:
            return StepResult.ok("first")

        @pipeline_step(depends_on=["chain_first"])
        def chain_second(ctx: PipelineContext) -> StepResult:
            first = ctx.get_value("chain_first")
            return StepResult.ok(f"{first} -> second")

        config = PipelineConfig(update_graph=False)
        ctx = run_pipeline("test123", "https://test.com", steps=["chain_second"], config=config)

        assert ctx.all_successful()
        assert ctx.get_value("chain_second") == "first -> second"

    def test_step_failure_stops_pipeline(self):
        @pipeline_step()
        def failing_step(ctx: PipelineContext) -> StepResult:
            return StepResult.fail("intentional failure")

        @pipeline_step(depends_on=["failing_step"])
        def dependent_step(ctx: PipelineContext) -> StepResult:
            return StepResult.ok("should not run")

        config = PipelineConfig(update_graph=False, continue_on_error=False)
        ctx = run_pipeline("test123", "https://test.com", steps=["dependent_step"], config=config)

        assert not ctx.all_successful()
        assert "dependent_step" not in ctx.results or not ctx.get_result("dependent_step").success

    def test_exception_handling(self):
        @pipeline_step()
        def raising_step(ctx: PipelineContext) -> StepResult:
            raise ValueError("unexpected error")

        config = PipelineConfig(update_graph=False)
        ctx = run_pipeline("test123", "https://test.com", steps=["raising_step"], config=config)

        result = ctx.get_result("raising_step")
        assert result is not None
        assert not result.success
        assert "ValueError" in result.error


class TestGetAllSteps:
    """Tests for get_all_steps function."""

    def test_returns_all_registered(self):
        @pipeline_step()
        def all_step_a(ctx: PipelineContext) -> StepResult:
            return StepResult.ok("a")

        @pipeline_step()
        def all_step_b(ctx: PipelineContext) -> StepResult:
            return StepResult.ok("b")

        steps = get_all_steps()
        assert "all_step_a" in steps
        assert "all_step_b" in steps

    def test_empty_registry(self):
        steps = get_all_steps()
        assert steps == {}
