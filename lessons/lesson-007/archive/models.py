"""Pydantic models for archive data structures."""

from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field


class ProcessingRecord(BaseModel):
    """Record of how archived data was processed."""

    version: str  # e.g., "v1_full_embed", "v2_chunked"
    processed_at: datetime
    collection_name: Optional[str] = None  # Qdrant collection name
    notes: Optional[str] = None


class LLMOutput(BaseModel):
    """Record of LLM-generated output (tags, summaries, etc.)."""

    output_type: str  # e.g., "tags", "summary", "classification"
    output_value: str
    generated_at: datetime
    model: str  # e.g., "claude-3-5-haiku-20241022"
    cost_usd: Optional[float] = None
    prompt_tokens: Optional[int] = None
    completion_tokens: Optional[int] = None


class YouTubeArchive(BaseModel):
    """Immutable archive of YouTube video data.

    This model captures everything that costs time or money to fetch:
    - Raw transcript (rate-limited API call)
    - YouTube metadata (API call or scraping)
    - LLM-generated outputs (costs money)
    - Processing history (what we've done with this data)
    """

    # Identity
    video_id: str
    url: str
    fetched_at: datetime
    source: str = "youtube-transcript-api"

    # Raw data (what cost time/money to fetch)
    raw_transcript: str
    youtube_metadata: dict = Field(default_factory=dict)  # title, upload_date, channel, etc.

    # LLM-generated outputs
    llm_outputs: list[LLMOutput] = Field(default_factory=list)

    # Processing history
    processing_history: list[ProcessingRecord] = Field(default_factory=list)

    def add_llm_output(
        self,
        output_type: str,
        output_value: str,
        model: str,
        cost_usd: Optional[float] = None,
        prompt_tokens: Optional[int] = None,
        completion_tokens: Optional[int] = None,
    ) -> None:
        """Add an LLM output record."""
        self.llm_outputs.append(
            LLMOutput(
                output_type=output_type,
                output_value=output_value,
                generated_at=datetime.now(),
                model=model,
                cost_usd=cost_usd,
                prompt_tokens=prompt_tokens,
                completion_tokens=completion_tokens,
            )
        )

    def add_processing_record(
        self,
        version: str,
        collection_name: Optional[str] = None,
        notes: Optional[str] = None,
    ) -> None:
        """Add a processing history record."""
        self.processing_history.append(
            ProcessingRecord(
                version=version,
                processed_at=datetime.now(),
                collection_name=collection_name,
                notes=notes,
            )
        )

    def get_latest_output(self, output_type: str) -> Optional[LLMOutput]:
        """Get the most recent LLM output of a specific type."""
        matching = [o for o in self.llm_outputs if o.output_type == output_type]
        if not matching:
            return None
        return max(matching, key=lambda o: o.generated_at)

    def total_llm_cost(self) -> float:
        """Calculate total LLM cost for this archive."""
        return sum(o.cost_usd or 0.0 for o in self.llm_outputs)
