"""Chunking service for transcript segmentation.

This module provides chunking capabilities for YouTube transcripts,
enabling timestamp-level semantic search and embedding.

Example:
    >>> from compose.services.chunking import chunk_youtube_transcript
    >>> from compose.services.youtube import get_timed_transcript
    >>>
    >>> segments, error = get_timed_transcript(url)
    >>> result = chunk_youtube_transcript(segments, video_id="abc123")
    >>> for chunk in result.chunks:
    ...     print(f"{chunk.timestamp_range}: {chunk.text[:50]}...")
"""

from .models import TranscriptChunk, ChunkingConfig, ChunkingResult
from .youtube_chunker import YouTubeChunker, chunk_youtube_transcript

__all__ = [
    "TranscriptChunk",
    "ChunkingConfig",
    "ChunkingResult",
    "YouTubeChunker",
    "chunk_youtube_transcript",
]
