"""Pydantic models for URL pattern analytics."""

from datetime import datetime
from typing import Optional, Literal
from pydantic import BaseModel, Field


class URLClassification(BaseModel):
    """Record of a URL classification."""

    url: str
    domain: str
    video_id: str
    classification: Literal["content", "marketing"]
    confidence: float = Field(ge=0.0, le=1.0)
    method: Literal["heuristic", "llm", "learned_pattern"]
    reason: Optional[str] = None
    pattern_suggested: Optional[str] = None
    classified_at: datetime = Field(default_factory=datetime.now)


class LearnedPattern(BaseModel):
    """A learned pattern for URL classification."""

    pattern: str
    pattern_type: Literal["domain", "url_pattern", "path"]
    classification: Literal["content", "marketing"]
    suggested_confidence: float = Field(ge=0.0, le=1.0)
    times_applied: int = 0
    correct_count: int = 0
    precision: float = Field(default=1.0, ge=0.0, le=1.0)
    status: Literal["active", "inactive", "pending_review"] = "active"
    added_at: datetime = Field(default_factory=datetime.now)
    last_used_at: Optional[datetime] = None


class PendingReevaluation(BaseModel):
    """URL pending re-evaluation due to low confidence."""

    url: str
    domain: str
    video_id: str
    classification: Literal["content", "marketing"]
    confidence: float = Field(ge=0.0, le=1.0)
    domain_occurrence_count: int = 1
    first_seen: datetime = Field(default_factory=datetime.now)
    last_seen: datetime = Field(default_factory=datetime.now)
    reevaluated: bool = False


class PatternStats(BaseModel):
    """Statistics for a learned pattern."""

    pattern: str
    pattern_type: str
    classification: str
    times_applied: int
    correct_count: int
    precision: float
    status: str
    added_at: datetime
    last_used_at: Optional[datetime]


class DomainReevaluation(BaseModel):
    """Domain ready for batch re-evaluation."""

    domain: str
    url_count: int
    urls: list[str]
    video_ids: list[str]
    avg_confidence: float
    classifications: dict[str, int]  # {"content": 2, "marketing": 1}


# SurrealDB Record Models
# These include 'id' field for SurrealDB record IDs

class URLClassificationRecord(BaseModel):
    """SurrealDB record for URL classification."""

    id: Optional[str] = None  # SurrealDB record ID
    url: str
    domain: str
    video_id: str
    classification: Literal["content", "marketing"]
    confidence: float = Field(ge=0.0, le=1.0)
    method: Literal["heuristic", "llm", "learned_pattern"]
    reason: Optional[str] = None
    pattern_suggested: Optional[str] = None
    classified_at: datetime = Field(default_factory=datetime.now)


class LearnedPatternRecord(BaseModel):
    """SurrealDB record for learned pattern."""

    id: Optional[str] = None  # SurrealDB record ID
    pattern: str  # Unique
    pattern_type: Literal["domain", "url_pattern", "path"]
    classification: Literal["content", "marketing"]
    suggested_confidence: float = Field(ge=0.0, le=1.0)
    times_applied: int = 0
    correct_count: int = 0
    precision: float = Field(default=1.0, ge=0.0, le=1.0)
    status: Literal["active", "inactive", "pending_review"] = "active"
    added_at: datetime = Field(default_factory=datetime.now)
    last_used_at: Optional[datetime] = None


class PendingReevaluationRecord(BaseModel):
    """SurrealDB record for pending re-evaluation."""

    id: Optional[str] = None  # SurrealDB record ID
    url: str
    domain: str
    video_id: str
    classification: Literal["content", "marketing"]
    confidence: float = Field(ge=0.0, le=1.0)
    domain_occurrence_count: int = 1
    first_seen: datetime = Field(default_factory=datetime.now)
    last_seen: datetime = Field(default_factory=datetime.now)
    reevaluated: bool = False
