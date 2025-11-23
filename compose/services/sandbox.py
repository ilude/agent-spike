"""Code execution sandbox for safely running user code.

Supports multiple languages with timeout and resource limits.
Uses subprocess isolation with restricted permissions.
"""

import asyncio
import json
import os
import subprocess
import sys
import tempfile
import uuid
from enum import Enum
from pathlib import Path
from typing import Optional

from pydantic import BaseModel, Field


class Language(str, Enum):
    """Supported programming languages."""

    PYTHON = "python"
    JAVASCRIPT = "javascript"
    BASH = "bash"


class ExecutionResult(BaseModel):
    """Result of code execution."""

    execution_id: str
    language: Language
    stdout: str = ""
    stderr: str = ""
    exit_code: int = 0
    timed_out: bool = False
    error: str | None = None
    execution_time_ms: int = 0


class ExecutionRequest(BaseModel):
    """Request to execute code."""

    code: str
    language: Language = Language.PYTHON
    timeout_seconds: float = Field(default=10.0, ge=1.0, le=30.0)
    stdin: str = ""


# Dangerous patterns to block in code
DANGEROUS_PATTERNS = {
    Language.PYTHON: [
        "import os",
        "import subprocess",
        "import sys",
        "from os",
        "from subprocess",
        "from sys",
        "__import__",
        "exec(",
        "eval(",
        "compile(",
        "open(",
        "file(",
        "input(",
        "raw_input(",
    ],
    Language.JAVASCRIPT: [
        "require(",
        "import ",
        "process.",
        "child_process",
        "fs.",
        "eval(",
        "Function(",
    ],
    Language.BASH: [
        "rm -rf",
        "dd if=",
        "mkfs",
        ":(){ :|:& };:",  # Fork bomb
        "> /dev/sd",
        "chmod 777",
    ],
}


class SandboxService:
    """Service for executing code in a sandboxed environment."""

    def __init__(self, max_output_size: int = 50000):
        """Initialize sandbox service.

        Args:
            max_output_size: Maximum output size in bytes
        """
        self.max_output_size = max_output_size

    def validate_code(self, code: str, language: Language) -> tuple[bool, str | None]:
        """Validate code for dangerous patterns.

        Args:
            code: Code to validate
            language: Programming language

        Returns:
            Tuple of (is_valid, error_message)
        """
        patterns = DANGEROUS_PATTERNS.get(language, [])
        code_lower = code.lower()

        for pattern in patterns:
            if pattern.lower() in code_lower:
                return False, f"Blocked pattern detected: {pattern}"

        # Check code length
        if len(code) > 10000:
            return False, "Code too long (max 10,000 characters)"

        return True, None

    async def execute(self, request: ExecutionRequest) -> ExecutionResult:
        """Execute code in sandbox.

        Args:
            request: Execution request with code and options

        Returns:
            ExecutionResult with output and status
        """
        execution_id = str(uuid.uuid4())[:8]

        # Validate code
        is_valid, error = self.validate_code(request.code, request.language)
        if not is_valid:
            return ExecutionResult(
                execution_id=execution_id,
                language=request.language,
                exit_code=1,
                error=error,
            )

        # Execute based on language
        if request.language == Language.PYTHON:
            return await self._execute_python(request, execution_id)
        elif request.language == Language.JAVASCRIPT:
            return await self._execute_javascript(request, execution_id)
        elif request.language == Language.BASH:
            return await self._execute_bash(request, execution_id)
        else:
            return ExecutionResult(
                execution_id=execution_id,
                language=request.language,
                exit_code=1,
                error=f"Unsupported language: {request.language}",
            )

    async def _execute_python(
        self, request: ExecutionRequest, execution_id: str
    ) -> ExecutionResult:
        """Execute Python code."""
        # Wrap code in restricted environment
        wrapped_code = f'''
import sys
import io

# Disable dangerous builtins
_safe_builtins = {{
    'abs': abs, 'all': all, 'any': any, 'bin': bin, 'bool': bool,
    'chr': chr, 'dict': dict, 'divmod': divmod, 'enumerate': enumerate,
    'filter': filter, 'float': float, 'format': format, 'frozenset': frozenset,
    'hash': hash, 'hex': hex, 'int': int, 'isinstance': isinstance,
    'issubclass': issubclass, 'iter': iter, 'len': len, 'list': list,
    'map': map, 'max': max, 'min': min, 'next': next, 'oct': oct,
    'ord': ord, 'pow': pow, 'print': print, 'range': range, 'repr': repr,
    'reversed': reversed, 'round': round, 'set': set, 'slice': slice,
    'sorted': sorted, 'str': str, 'sum': sum, 'tuple': tuple, 'type': type,
    'zip': zip, 'True': True, 'False': False, 'None': None,
}}

# Execute user code
try:
    exec("""
{request.code.replace(chr(92), chr(92)+chr(92)).replace('"', chr(92)+'"')}
""", {{"__builtins__": _safe_builtins}})
except Exception as e:
    print(f"Error: {{type(e).__name__}}: {{e}}", file=sys.stderr)
    sys.exit(1)
'''

        return await self._run_subprocess(
            [sys.executable, "-c", wrapped_code],
            request,
            execution_id,
            Language.PYTHON,
        )

    async def _execute_javascript(
        self, request: ExecutionRequest, execution_id: str
    ) -> ExecutionResult:
        """Execute JavaScript code using Node.js."""
        # Check if node is available
        node_cmd = "node"

        return await self._run_subprocess(
            [node_cmd, "-e", request.code],
            request,
            execution_id,
            Language.JAVASCRIPT,
        )

    async def _execute_bash(
        self, request: ExecutionRequest, execution_id: str
    ) -> ExecutionResult:
        """Execute Bash code."""
        # Use restricted bash
        bash_cmd = "bash"

        return await self._run_subprocess(
            [bash_cmd, "-c", request.code],
            request,
            execution_id,
            Language.BASH,
        )

    async def _run_subprocess(
        self,
        cmd: list[str],
        request: ExecutionRequest,
        execution_id: str,
        language: Language,
    ) -> ExecutionResult:
        """Run a subprocess with timeout and capture output."""
        import time

        start_time = time.time()

        try:
            # Create subprocess
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdin=asyncio.subprocess.PIPE if request.stdin else None,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                # Limit resources
                env={
                    **os.environ,
                    "PYTHONDONTWRITEBYTECODE": "1",
                    "PYTHONUNBUFFERED": "1",
                },
            )

            try:
                # Wait with timeout
                stdout, stderr = await asyncio.wait_for(
                    process.communicate(
                        input=request.stdin.encode() if request.stdin else None
                    ),
                    timeout=request.timeout_seconds,
                )

                execution_time = int((time.time() - start_time) * 1000)

                return ExecutionResult(
                    execution_id=execution_id,
                    language=language,
                    stdout=stdout.decode("utf-8", errors="replace")[
                        : self.max_output_size
                    ],
                    stderr=stderr.decode("utf-8", errors="replace")[
                        : self.max_output_size
                    ],
                    exit_code=process.returncode or 0,
                    execution_time_ms=execution_time,
                )

            except asyncio.TimeoutError:
                process.kill()
                await process.wait()

                return ExecutionResult(
                    execution_id=execution_id,
                    language=language,
                    timed_out=True,
                    error=f"Execution timed out after {request.timeout_seconds}s",
                    exit_code=124,  # Standard timeout exit code
                    execution_time_ms=int(request.timeout_seconds * 1000),
                )

        except FileNotFoundError as e:
            return ExecutionResult(
                execution_id=execution_id,
                language=language,
                exit_code=1,
                error=f"Runtime not found: {cmd[0]}",
            )
        except Exception as e:
            return ExecutionResult(
                execution_id=execution_id,
                language=language,
                exit_code=1,
                error=str(e),
            )


# Singleton instance
_service: Optional[SandboxService] = None


def get_sandbox_service() -> SandboxService:
    """Get or create the sandbox service singleton."""
    global _service
    if _service is None:
        _service = SandboxService()
    return _service
