"""Code execution sandbox API router."""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from compose.services.sandbox import (
    ExecutionRequest,
    ExecutionResult,
    Language,
    get_sandbox_service,
)

router = APIRouter(prefix="/sandbox")


class ExecuteRequest(BaseModel):
    """API request for code execution."""

    code: str = Field(..., min_length=1, max_length=10000)
    language: Language = Language.PYTHON
    timeout: float = Field(default=10.0, ge=1.0, le=30.0)
    stdin: str = ""


class SupportedLanguagesResponse(BaseModel):
    """Response listing supported languages."""

    languages: list[dict[str, str]]


@router.get("/languages", response_model=SupportedLanguagesResponse)
async def list_languages():
    """List supported programming languages."""
    return SupportedLanguagesResponse(
        languages=[
            {"id": "python", "name": "Python", "extension": ".py"},
            {"id": "javascript", "name": "JavaScript", "extension": ".js"},
            {"id": "bash", "name": "Bash", "extension": ".sh"},
        ]
    )


@router.post("/execute", response_model=ExecutionResult)
async def execute_code(request: ExecuteRequest):
    """Execute code in the sandbox.

    Runs the provided code in a sandboxed environment with:
    - Timeout enforcement (1-30 seconds)
    - Dangerous code pattern blocking
    - Output size limits
    - No file system or network access

    Supported languages: Python, JavaScript, Bash
    """
    service = get_sandbox_service()

    execution_request = ExecutionRequest(
        code=request.code,
        language=request.language,
        timeout_seconds=request.timeout,
        stdin=request.stdin,
    )

    result = await service.execute(execution_request)

    return result


@router.post("/validate")
async def validate_code(request: ExecuteRequest):
    """Validate code without executing it.

    Checks for dangerous patterns that would be blocked during execution.
    Use this to preview validation before running code.
    """
    service = get_sandbox_service()
    is_valid, error = service.validate_code(request.code, request.language)

    return {
        "valid": is_valid,
        "error": error,
        "language": request.language,
    }
