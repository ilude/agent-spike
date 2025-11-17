"""Protocol definitions for archive service.

Protocols define interfaces without implementation, enabling:
- Easy mocking for tests
- Swappable implementations (local, S3, etc.)
- Clear contracts between services
"""

from typing import Protocol, Optional, Iterator
from pathlib import Path
from .models import YouTubeArchive


class ArchiveWriter(Protocol):
    """Protocol for archiving expensive-to-fetch content.

    Implementations must provide methods to:
    - Archive content that costs time/money to fetch
    - Add LLM outputs with cost tracking
    - Add processing records for reprocessing workflows
    - Check existence to avoid duplicate fetches
    """

    def archive_youtube_video(
        self,
        video_id: str,
        url: str,
        transcript: str,
        metadata: Optional[dict] = None,
    ) -> Path:
        """Archive YouTube video data.

        Args:
            video_id: YouTube video ID
            url: Full YouTube URL
            transcript: Raw transcript text
            metadata: Optional YouTube metadata (title, upload_date, etc.)

        Returns:
            Path to archive file
        """
        ...

    def add_llm_output(
        self,
        video_id: str,
        output_type: str,
        output_value: str,
        model: str,
        cost_usd: Optional[float] = None,
        prompt_tokens: Optional[int] = None,
        completion_tokens: Optional[int] = None,
    ) -> Path:
        """Add LLM output to existing archive.

        Args:
            video_id: YouTube video ID
            output_type: Type of output (e.g., "tags", "summary")
            output_value: The generated output
            model: Model used (e.g., "claude-3-5-haiku-20241022")
            cost_usd: Optional cost in USD
            prompt_tokens: Optional prompt token count
            completion_tokens: Optional completion token count

        Returns:
            Path to updated archive file
        """
        ...

    def add_processing_record(
        self,
        video_id: str,
        version: str,
        collection_name: Optional[str] = None,
        notes: Optional[str] = None,
    ) -> Path:
        """Add processing record to existing archive.

        Args:
            video_id: YouTube video ID
            version: Processing version (e.g., "v1_full_embed", "v2_chunked")
            collection_name: Optional cache collection name
            notes: Optional notes about processing

        Returns:
            Path to updated archive file
        """
        ...

    def exists(self, video_id: str) -> bool:
        """Check if video already archived.

        Args:
            video_id: YouTube video ID

        Returns:
            True if archive exists, False otherwise
        """
        ...

    def get(self, video_id: str) -> Optional[YouTubeArchive]:
        """Retrieve archived video data.

        Args:
            video_id: YouTube video ID

        Returns:
            YouTubeArchive if found, None otherwise
        """
        ...


class ArchiveReader(Protocol):
    """Protocol for reading archived content.

    Used for reprocessing workflows where you need to:
    - Iterate through all archived content
    - Filter by date range
    - Calculate aggregate statistics
    """

    def iter_youtube_videos(
        self,
        start_month: Optional[str] = None,
        end_month: Optional[str] = None,
    ) -> Iterator[YouTubeArchive]:
        """Iterate through all archived YouTube videos.

        Args:
            start_month: Optional start month (e.g., "2024-10")
            end_month: Optional end month (e.g., "2024-11")

        Yields:
            YouTubeArchive objects
        """
        ...

    def get(self, video_id: str) -> Optional[YouTubeArchive]:
        """Retrieve specific archived video.

        Args:
            video_id: YouTube video ID

        Returns:
            YouTubeArchive if found, None otherwise
        """
        ...

    def count(self) -> int:
        """Count total number of archived videos.

        Returns:
            Total count
        """
        ...

    def get_total_llm_cost(self) -> float:
        """Calculate total LLM cost across all archives.

        Returns:
            Total cost in USD
        """
        ...
