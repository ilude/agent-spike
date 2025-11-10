"""Archive service for storing expensive-to-fetch content.

This module provides archiving for any content that costs time or money to fetch:
- External API calls (YouTube transcripts, web scraping, etc.)
- LLM outputs (tags, summaries, classifications)
- Rate-limited operations
- Data that might need reprocessing

Archives are immutable - write once, never modify. This enables:
- Experimentation without re-fetching
- Protection against rate limits
- LLM cost tracking
- Migration between storage systems
"""

from .models import (
    YouTubeArchive,
    LLMOutput,
    ProcessingRecord,
)
from .archive_writer import (
    ArchiveWriter,
    LocalArchiveWriter,
)
from .archive_reader import (
    ArchiveReader,
    LocalArchiveReader,
)

__all__ = [
    "YouTubeArchive",
    "LLMOutput",
    "ProcessingRecord",
    "ArchiveWriter",
    "LocalArchiveWriter",
    "ArchiveReader",
    "LocalArchiveReader",
]
