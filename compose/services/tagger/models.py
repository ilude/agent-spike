"""Data models for tag normalization."""

from typing import Dict, List, Optional
from pydantic import BaseModel


class StructuredMetadata(BaseModel):
    """Structured metadata output from Phase 1 (raw extraction)."""

    title: str
    summary: str
    subject_matter: List[str]
    entities: Dict[str, List[str]]
    techniques_or_concepts: List[str]
    tools_or_materials: List[str]
    content_style: Optional[str] = None
    difficulty: Optional[str] = None
    key_points: List[str] = []
    references: List[str] = []


class NormalizedMetadata(BaseModel):
    """Normalized metadata output from Phase 2 (with vocabulary)."""

    title: str
    summary: Optional[str] = ""
    subject_matter: List[str] = []
    entities: Optional[Dict[str, List[str]]] = {}
    techniques_or_concepts: List[str] = []
    tools_or_materials: List[str] = []
    content_style: Optional[str] = None
    difficulty: Optional[str] = None
    key_points: List[str] = []
    references: List[str] = []
