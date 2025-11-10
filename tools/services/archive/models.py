"""Pydantic models for archive data structures."""

from datetime import datetime
from typing import Optional, Literal
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


class DerivedOutput(BaseModel):
    """Record of derived/computed output from transformations.

    Unlike LLM outputs, derived outputs are computed deterministically from
    existing data (transformations, normalizations, etc.). They can be
    regenerated at any time and are version-tracked for staleness detection.
    """

    output_type: str  # e.g., "normalized_metadata_v1", "qdrant_metadata"
    output_value: str  # JSON-serialized output
    generated_at: datetime
    transformer_version: str  # Version of transformer that produced this
    transform_manifest: dict  # Full manifest of versions used (for staleness detection)
    source_outputs: list[str] = Field(default_factory=list)  # Source output_types used (e.g., ["tags"])


class ChannelContext(BaseModel):
    """Channel information for bulk imports."""

    channel_id: Optional[str] = None
    channel_name: Optional[str] = None
    is_bulk_import: bool = False


class ImportMetadata(BaseModel):
    """Metadata about how this video was imported.

    Tracks import source and recommendation weight for future recommendation engine.
    See .claude/IMPORT_METADATA.md for full documentation.
    """

    source_type: Literal["single_import", "repl_import", "bulk_channel", "bulk_multi_channel"]
    imported_at: datetime
    import_method: Literal["cli", "repl", "scheduled"]
    channel_context: ChannelContext = Field(default_factory=ChannelContext)
    recommendation_weight: float  # 1.0 for single/repl, 0.5 for bulk_channel, 0.2 for bulk_multi_channel


class YouTubeArchive(BaseModel):
    """Immutable archive of YouTube video data.

    This model captures everything that costs time or money to fetch:
    - Raw transcript (rate-limited API call)
    - YouTube metadata (API call or scraping)
    - LLM-generated outputs (costs money)
    - Processing history (what we've done with this data)
    - Import metadata (for recommendation weighting)
    """

    # Identity
    video_id: str
    url: str
    fetched_at: datetime
    source: str = "youtube-transcript-api"

    # Import tracking (for recommendations)
    import_metadata: Optional[ImportMetadata] = None

    # Raw data (what cost time/money to fetch)
    raw_transcript: str
    youtube_metadata: dict = Field(default_factory=dict)  # title, upload_date, channel, etc.

    # LLM-generated outputs
    llm_outputs: list[LLMOutput] = Field(default_factory=list)

    # Derived/computed outputs (transformations, normalizations)
    derived_outputs: list[DerivedOutput] = Field(default_factory=list)

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

    def add_derived_output(
        self,
        output_type: str,
        output_value: str,
        transformer_version: str,
        transform_manifest: dict,
        source_outputs: Optional[list[str]] = None,
    ) -> None:
        """Add a derived output record.

        Args:
            output_type: Type of derived output (e.g., "normalized_metadata_v1")
            output_value: JSON-serialized output
            transformer_version: Version of transformer used
            transform_manifest: Full version manifest for staleness detection
            source_outputs: List of source output types used (e.g., ["tags"])
        """
        self.derived_outputs.append(
            DerivedOutput(
                output_type=output_type,
                output_value=output_value,
                generated_at=datetime.now(),
                transformer_version=transformer_version,
                transform_manifest=transform_manifest,
                source_outputs=source_outputs or [],
            )
        )

    def get_latest_output(self, output_type: str) -> Optional[LLMOutput]:
        """Get the most recent LLM output of a specific type."""
        matching = [o for o in self.llm_outputs if o.output_type == output_type]
        if not matching:
            return None
        return max(matching, key=lambda o: o.generated_at)

    def get_latest_derived_output(self, output_type: str) -> Optional[DerivedOutput]:
        """Get the most recent derived output of a specific type."""
        matching = [o for o in self.derived_outputs if o.output_type == output_type]
        if not matching:
            return None
        return max(matching, key=lambda o: o.generated_at)

    def total_llm_cost(self) -> float:
        """Calculate total LLM cost for this archive."""
        return sum(o.cost_usd or 0.0 for o in self.llm_outputs)
