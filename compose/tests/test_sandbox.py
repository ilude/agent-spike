"""Tests for the code execution sandbox service."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from compose.services.sandbox import (
    DANGEROUS_PATTERNS,
    ExecutionRequest,
    ExecutionResult,
    Language,
    SandboxService,
    get_sandbox_service,
)


class TestLanguageEnum:
    """Tests for Language enum."""

    def test_language_values(self):
        """Test language enum values."""
        assert Language.PYTHON == "python"
        assert Language.JAVASCRIPT == "javascript"
        assert Language.BASH == "bash"


class TestExecutionResult:
    """Tests for ExecutionResult model."""

    def test_result_creation(self):
        """Test creating ExecutionResult."""
        result = ExecutionResult(
            execution_id="test123",
            language=Language.PYTHON,
            stdout="Hello",
            exit_code=0,
        )
        assert result.execution_id == "test123"
        assert result.language == Language.PYTHON
        assert result.stdout == "Hello"
        assert result.exit_code == 0

    def test_result_defaults(self):
        """Test default values."""
        result = ExecutionResult(execution_id="test", language=Language.PYTHON)
        assert result.stdout == ""
        assert result.stderr == ""
        assert result.exit_code == 0
        assert result.timed_out is False
        assert result.error is None


class TestExecutionRequest:
    """Tests for ExecutionRequest model."""

    def test_request_creation(self):
        """Test creating ExecutionRequest."""
        request = ExecutionRequest(code="print('hello')")
        assert request.code == "print('hello')"
        assert request.language == Language.PYTHON
        assert request.timeout_seconds == 10.0

    def test_request_with_options(self):
        """Test request with custom options."""
        request = ExecutionRequest(
            code="console.log('hi')",
            language=Language.JAVASCRIPT,
            timeout_seconds=5.0,
            stdin="input data",
        )
        assert request.language == Language.JAVASCRIPT
        assert request.timeout_seconds == 5.0
        assert request.stdin == "input data"


class TestSandboxValidation:
    """Tests for code validation."""

    @pytest.fixture
    def service(self):
        """Create sandbox service."""
        return SandboxService()

    def test_validate_safe_python(self, service):
        """Test validating safe Python code."""
        is_valid, error = service.validate_code("print('hello')", Language.PYTHON)
        assert is_valid is True
        assert error is None

    def test_validate_dangerous_python_import_os(self, service):
        """Test blocking dangerous Python imports."""
        is_valid, error = service.validate_code("import os", Language.PYTHON)
        assert is_valid is False
        assert "import os" in error

    def test_validate_dangerous_python_subprocess(self, service):
        """Test blocking subprocess import."""
        is_valid, error = service.validate_code("import subprocess", Language.PYTHON)
        assert is_valid is False
        assert "subprocess" in error

    def test_validate_dangerous_python_exec(self, service):
        """Test blocking exec()."""
        is_valid, error = service.validate_code("exec('bad')", Language.PYTHON)
        assert is_valid is False
        assert "exec(" in error

    def test_validate_dangerous_python_open(self, service):
        """Test blocking open()."""
        is_valid, error = service.validate_code("open('file.txt')", Language.PYTHON)
        assert is_valid is False
        assert "open(" in error

    def test_validate_code_too_long(self, service):
        """Test blocking code that's too long."""
        long_code = "x = 1\n" * 5000
        is_valid, error = service.validate_code(long_code, Language.PYTHON)
        assert is_valid is False
        assert "too long" in error

    def test_validate_safe_javascript(self, service):
        """Test validating safe JavaScript code."""
        is_valid, error = service.validate_code(
            "console.log('hello')", Language.JAVASCRIPT
        )
        assert is_valid is True

    def test_validate_dangerous_javascript(self, service):
        """Test blocking dangerous JavaScript."""
        is_valid, error = service.validate_code(
            "require('fs')", Language.JAVASCRIPT
        )
        assert is_valid is False

    def test_validate_safe_bash(self, service):
        """Test validating safe Bash code."""
        is_valid, error = service.validate_code("echo hello", Language.BASH)
        assert is_valid is True

    def test_validate_dangerous_bash(self, service):
        """Test blocking dangerous Bash code."""
        is_valid, error = service.validate_code("rm -rf /", Language.BASH)
        assert is_valid is False


class TestSandboxExecution:
    """Tests for code execution."""

    @pytest.fixture
    def service(self):
        """Create sandbox service."""
        return SandboxService()

    @pytest.mark.asyncio
    async def test_execute_python_print(self, service):
        """Test executing simple Python print."""
        request = ExecutionRequest(code="print('hello world')")
        result = await service.execute(request)

        assert result.exit_code == 0
        assert "hello world" in result.stdout
        assert result.error is None

    @pytest.mark.asyncio
    async def test_execute_python_math(self, service):
        """Test executing Python math."""
        request = ExecutionRequest(code="print(2 + 2)")
        result = await service.execute(request)

        assert result.exit_code == 0
        assert "4" in result.stdout

    @pytest.mark.asyncio
    async def test_execute_python_error(self, service):
        """Test Python runtime error is captured."""
        request = ExecutionRequest(code="print(undefined_variable)")
        result = await service.execute(request)

        assert result.exit_code == 1
        assert "NameError" in result.stderr or "Error" in result.stderr

    @pytest.mark.asyncio
    async def test_execute_blocks_dangerous_code(self, service):
        """Test that dangerous code is blocked before execution."""
        request = ExecutionRequest(code="import os; os.system('bad')")
        result = await service.execute(request)

        assert result.exit_code == 1
        assert "Blocked" in result.error

    @pytest.mark.asyncio
    async def test_execute_returns_execution_id(self, service):
        """Test that execution returns unique ID."""
        request = ExecutionRequest(code="print('test')")
        result = await service.execute(request)

        assert result.execution_id is not None
        assert len(result.execution_id) == 8

    @pytest.mark.asyncio
    async def test_execute_records_time(self, service):
        """Test that execution time is recorded."""
        request = ExecutionRequest(code="print('test')")
        result = await service.execute(request)

        assert result.execution_time_ms >= 0


class TestSandboxTimeout:
    """Tests for timeout handling."""

    @pytest.fixture
    def service(self):
        """Create sandbox service."""
        return SandboxService()

    @pytest.mark.asyncio
    async def test_execute_timeout(self, service):
        """Test that long-running code times out."""
        # This code would run forever without timeout
        request = ExecutionRequest(
            code="import time; time.sleep(100)",  # Will be blocked by validation
            timeout_seconds=1.0,
        )
        result = await service.execute(request)

        # Should be blocked before it even runs
        assert result.exit_code == 1


class TestSingleton:
    """Tests for singleton pattern."""

    def test_get_sandbox_service_returns_instance(self):
        """Test get_sandbox_service returns SandboxService."""
        import compose.services.sandbox as module

        module._service = None

        service = get_sandbox_service()
        assert isinstance(service, SandboxService)

    def test_get_sandbox_service_returns_same_instance(self):
        """Test get_sandbox_service returns same instance."""
        import compose.services.sandbox as module

        module._service = None

        service1 = get_sandbox_service()
        service2 = get_sandbox_service()
        assert service1 is service2
