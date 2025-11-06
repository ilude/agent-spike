"""Data models for batch processing with OpenAI."""

from typing import Any, Optional, Literal
from pydantic import BaseModel, Field


class BatchRequestBody(BaseModel):
    """Body of a batch request for OpenAI Chat Completions."""

    model: str = Field(default="gpt-4o-mini", description="OpenAI model to use")
    messages: list[dict[str, str]] = Field(..., description="Chat messages")
    temperature: float = Field(default=0.7, description="Sampling temperature")
    max_tokens: int = Field(default=500, description="Maximum tokens in response")
    response_format: Optional[dict] = Field(None, description="Response format (e.g., JSON)")


class BatchRequest(BaseModel):
    """Single request in a batch JSONL file."""

    custom_id: str = Field(..., description="Unique identifier for this request")
    method: Literal["POST"] = Field(default="POST", description="HTTP method")
    url: str = Field(default="/v1/chat/completions", description="API endpoint")
    body: BatchRequestBody = Field(..., description="Request body")

    class Config:
        """Pydantic configuration."""
        json_schema_extra = {
            "example": {
                "custom_id": "youtube:abc123",
                "method": "POST",
                "url": "/v1/chat/completions",
                "body": {
                    "model": "gpt-4o-mini",
                    "messages": [
                        {"role": "system", "content": "You are a tagging assistant..."},
                        {"role": "user", "content": "Transcript here..."}
                    ]
                }
            }
        }


class BatchResponse(BaseModel):
    """Response body from batch API."""

    status_code: int = Field(..., description="HTTP status code")
    request_id: Optional[str] = Field(None, description="Request ID from OpenAI")
    body: dict[str, Any] = Field(..., description="Response body (varies by status)")


class BatchResult(BaseModel):
    """Single result from batch output JSONL file."""

    id: str = Field(..., description="Batch request ID (OpenAI generated)")
    custom_id: str = Field(..., description="User-provided custom ID")
    response: BatchResponse = Field(..., description="API response")
    error: Optional[dict] = Field(None, description="Error information if request failed")


class TaggingOutput(BaseModel):
    """Expected output structure from tagging prompts."""

    tags: list[str] = Field(..., min_length=3, max_length=7, description="Content tags")
    summary: str = Field(..., max_length=150, description="One-sentence summary")


class AdvancedTaggingOutput(BaseModel):
    """Extended tagging output with additional metadata."""

    tags: list[str] = Field(..., min_length=3, max_length=7)
    summary: str = Field(..., max_length=150)
    difficulty: Literal["beginner", "intermediate", "advanced"]
    topics: list[str] = Field(..., min_length=2, max_length=4)


class BatchStats(BaseModel):
    """Statistics for a batch job."""

    total: int = Field(..., description="Total requests in batch")
    completed: int = Field(default=0, description="Completed requests")
    failed: int = Field(default=0, description="Failed requests")
    processing: int = Field(default=0, description="Requests in progress")
    queued: int = Field(default=0, description="Queued requests")


class BatchJobInfo(BaseModel):
    """Information about a batch job."""

    id: str = Field(..., description="Batch job ID")
    status: Literal[
        "validating",
        "failed",
        "in_progress",
        "finalizing",
        "completed",
        "expired",
        "cancelling",
        "cancelled"
    ] = Field(..., description="Current batch status")
    input_file_id: str = Field(..., description="Input file ID")
    output_file_id: Optional[str] = Field(None, description="Output file ID (if completed)")
    error_file_id: Optional[str] = Field(None, description="Error file ID (if errors occurred)")
    created_at: int = Field(..., description="Unix timestamp of creation")
    in_progress_at: Optional[int] = Field(None, description="Unix timestamp when processing started")
    completed_at: Optional[int] = Field(None, description="Unix timestamp when completed")
    expires_at: Optional[int] = Field(None, description="Unix timestamp when expires")
    request_counts: Optional[BatchStats] = Field(None, description="Request statistics")
    metadata: Optional[dict] = Field(None, description="User-provided metadata")
