"""YouTube transcript chunking service.

Implements time + token hybrid chunking for YouTube transcripts:
1. Split on natural pause boundaries (8-10 sec gaps)
2. Merge small chunks until target token count
3. Split large chunks at sentence boundaries
4. Track start/end timestamps for each chunk

This enables timestamp-level search ("find where they discussed X").
"""

import re
from typing import Optional

from .models import TranscriptChunk, ChunkingConfig, ChunkingResult


class YouTubeChunker:
    """Chunks YouTube transcripts using time + token hybrid strategy.

    Example:
        >>> chunker = YouTubeChunker()
        >>> result = chunker.chunk_transcript(timed_segments, video_id="abc123")
        >>> for chunk in result.chunks:
        ...     print(f"{chunk.timestamp_range}: {chunk.text[:50]}...")
    """

    def __init__(self, config: Optional[ChunkingConfig] = None):
        """Initialize chunker with configuration.

        Args:
            config: Chunking configuration (uses defaults if None)
        """
        self.config = config or ChunkingConfig()

    def chunk_transcript(
        self,
        timed_segments: list[dict],
        video_id: str = "",
    ) -> ChunkingResult:
        """Chunk a timed transcript into semantically meaningful pieces.

        Args:
            timed_segments: List of {"text", "start", "duration"} dicts
            video_id: YouTube video ID for metadata

        Returns:
            ChunkingResult with list of TranscriptChunks
        """
        if not timed_segments:
            return ChunkingResult(video_id=video_id)

        # Build set of pause indices for quick lookup
        pause_indices = set(self._find_pause_boundaries(timed_segments))

        # Stream through segments, creating chunks based on token count
        # Use pause boundaries as preferred split points
        chunks = self._stream_chunks(timed_segments, pause_indices, video_id)

        # Calculate total duration
        total_duration = 0.0
        if timed_segments:
            last_seg = timed_segments[-1]
            total_duration = last_seg["start"] + last_seg.get("duration", 0)

        return ChunkingResult(
            chunks=chunks,
            video_id=video_id,
            total_duration=total_duration,
        )

    def _stream_chunks(
        self,
        segments: list[dict],
        pause_indices: set[int],
        video_id: str,
    ) -> list[TranscriptChunk]:
        """Stream through segments creating chunks based on token count.

        Prefers to split at pause boundaries when possible, but will
        split at sentence boundaries when token count exceeds target.
        """
        chunks = []
        current_segments: list[dict] = []
        chunk_index = 0

        for i, seg in enumerate(segments):
            current_segments.append(seg)
            current_text = " ".join(s["text"] for s in current_segments)
            current_tokens = self._estimate_tokens(current_text)

            # Check if we should create a chunk
            should_split = False
            at_pause = i in pause_indices

            if current_tokens >= self.config.target_tokens:
                # We have enough tokens
                if at_pause:
                    # Perfect - split at natural pause
                    should_split = True
                elif current_tokens >= self.config.max_tokens:
                    # Too large - force split
                    should_split = True
            elif at_pause and current_tokens >= self.config.min_tokens:
                # At a pause with reasonable size - split here
                should_split = True

            if should_split:
                chunk = self._create_chunk(current_segments, video_id, chunk_index)
                chunks.append(chunk)
                chunk_index += 1
                current_segments = []

        # Handle remaining segments
        if current_segments:
            current_text = " ".join(s["text"] for s in current_segments)
            current_tokens = self._estimate_tokens(current_text)

            if chunks and current_tokens < self.config.min_tokens:
                # Too small - merge with previous chunk
                last_chunk = chunks[-1]
                merged_text = last_chunk.text + " " + current_text
                chunks[-1] = TranscriptChunk(
                    text=merged_text,
                    start_time=last_chunk.start_time,
                    end_time=current_segments[-1]["start"]
                    + current_segments[-1].get("duration", 0),
                    chunk_index=last_chunk.chunk_index,
                    video_id=video_id,
                    token_count=self._estimate_tokens(merged_text),
                )
            else:
                # Create final chunk
                chunk = self._create_chunk(current_segments, video_id, chunk_index)
                chunks.append(chunk)

        return chunks

    def _find_pause_boundaries(self, segments: list[dict]) -> list[int]:
        """Find indices where natural pauses occur.

        A pause is detected when the gap between segments exceeds threshold.

        Returns:
            List of segment indices where pauses occur (split AFTER this index)
        """
        pause_indices = []

        for i in range(len(segments) - 1):
            current = segments[i]
            next_seg = segments[i + 1]

            # Calculate gap between segments
            current_end = current["start"] + current.get("duration", 0)
            gap = next_seg["start"] - current_end

            if gap >= self.config.pause_threshold:
                pause_indices.append(i)

        return pause_indices

    def _create_chunk(
        self,
        segments: list[dict],
        video_id: str,
        chunk_index: int,
    ) -> TranscriptChunk:
        """Create a TranscriptChunk from a list of segments."""
        text = " ".join(seg["text"] for seg in segments)
        start_time = segments[0]["start"]
        end_time = segments[-1]["start"] + segments[-1].get("duration", 0)

        return TranscriptChunk(
            text=text,
            start_time=start_time,
            end_time=end_time,
            chunk_index=chunk_index,
            video_id=video_id,
            token_count=self._estimate_tokens(text),
        )

    def _estimate_tokens(self, text: str) -> int:
        """Estimate token count from text length.

        Uses a simple character-based estimation.
        For more accuracy, could use tiktoken or similar.
        """
        return int(len(text) / self.config.chars_per_token)

    def _find_sentence_boundary(self, text: str) -> int:
        """Find the best sentence boundary for splitting.

        Looks for sentence-ending punctuation near the target split point.
        Returns character index to split at (end of sentence).
        """
        target = len(text) // 2  # Aim for middle

        # Find all sentence boundaries
        boundaries = []
        for match in re.finditer(r"[.!?]\s+", text):
            boundaries.append(match.end())

        if not boundaries:
            return -1

        # Find closest boundary to target
        best = min(boundaries, key=lambda x: abs(x - target))
        return best


def chunk_youtube_transcript(
    timed_segments: list[dict],
    video_id: str = "",
    config: Optional[ChunkingConfig] = None,
) -> ChunkingResult:
    """Convenience function to chunk a transcript.

    Args:
        timed_segments: List of {"text", "start", "duration"} dicts
        video_id: YouTube video ID
        config: Optional chunking configuration

    Returns:
        ChunkingResult with chunks
    """
    chunker = YouTubeChunker(config)
    return chunker.chunk_transcript(timed_segments, video_id)
