"""Data models for transcript chunking.

These models define the structure of chunks created from YouTube transcripts
for embedding and semantic search.
"""

from dataclasses import dataclass, field
from typing import Optional


@dataclass
class TranscriptChunk:
    """A chunk of transcript text with timing metadata.

    Attributes:
        text: The chunk text content
        start_time: Start time in seconds from video beginning
        end_time: End time in seconds from video beginning
        chunk_index: Index of this chunk within the video (0-based)
        video_id: YouTube video ID this chunk belongs to
        token_count: Approximate token count (for embedding limits)
    """

    text: str
    start_time: float
    end_time: float
    chunk_index: int
    video_id: str = ""
    token_count: int = 0

    @property
    def duration(self) -> float:
        """Duration of this chunk in seconds."""
        return self.end_time - self.start_time

    @property
    def timestamp_range(self) -> str:
        """Human-readable timestamp range (e.g., '1:30-2:45')."""
        return f"{_format_timestamp(self.start_time)}-{_format_timestamp(self.end_time)}"

    def to_dict(self) -> dict:
        """Convert to dictionary for serialization."""
        return {
            "text": self.text,
            "start_time": self.start_time,
            "end_time": self.end_time,
            "chunk_index": self.chunk_index,
            "video_id": self.video_id,
            "token_count": self.token_count,
            "duration": self.duration,
            "timestamp_range": self.timestamp_range,
        }


@dataclass
class ChunkingConfig:
    """Configuration for the chunking algorithm.

    Attributes:
        target_tokens: Target token count per chunk (default: 2500)
        max_tokens: Maximum token count before forced split (default: 3000)
        min_tokens: Minimum tokens before merging with next (default: 500)
        pause_threshold: Seconds of pause to trigger split (default: 8.0)
        chars_per_token: Approximate characters per token (default: 4)
    """

    target_tokens: int = 2500
    max_tokens: int = 3000
    min_tokens: int = 500
    pause_threshold: float = 8.0
    chars_per_token: float = 4.0  # Rough estimate for English text


@dataclass
class ChunkingResult:
    """Result of chunking a transcript.

    Attributes:
        chunks: List of transcript chunks
        video_id: YouTube video ID
        total_duration: Total video duration in seconds
        chunk_count: Number of chunks created
        avg_chunk_tokens: Average tokens per chunk
    """

    chunks: list[TranscriptChunk] = field(default_factory=list)
    video_id: str = ""
    total_duration: float = 0.0

    @property
    def chunk_count(self) -> int:
        """Number of chunks."""
        return len(self.chunks)

    @property
    def avg_chunk_tokens(self) -> float:
        """Average token count per chunk."""
        if not self.chunks:
            return 0.0
        return sum(c.token_count for c in self.chunks) / len(self.chunks)

    def to_dict(self) -> dict:
        """Convert to dictionary for serialization."""
        return {
            "video_id": self.video_id,
            "total_duration": self.total_duration,
            "chunk_count": self.chunk_count,
            "avg_chunk_tokens": self.avg_chunk_tokens,
            "chunks": [c.to_dict() for c in self.chunks],
        }


def _format_timestamp(seconds: float) -> str:
    """Format seconds as MM:SS or H:MM:SS."""
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    secs = int(seconds % 60)

    if hours > 0:
        return f"{hours}:{minutes:02d}:{secs:02d}"
    return f"{minutes}:{secs:02d}"
