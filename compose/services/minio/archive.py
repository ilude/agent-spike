"""Archive storage operations using MinIO."""

from datetime import datetime
from typing import Optional

from .client import MinIOClient


class ArchiveStorage:
    """Manages archive storage operations in MinIO."""

    def __init__(self, client: MinIOClient):
        """Initialize archive storage.

        Args:
            client: MinIOClient instance for object storage operations.
        """
        self.client = client

    def store_archive(
        self, video_id: str, archive_data: dict, month: Optional[str] = None
    ) -> str:
        """Store YouTube archive data in MinIO.

        Args:
            video_id: YouTube video ID.
            archive_data: Archive data dictionary (typically YouTubeArchive.model_dump()).
            month: Optional month in YYYY-MM format. Defaults to current month.

        Returns:
            The path where archive was stored.
        """
        if month is None:
            month = datetime.now().strftime("%Y-%m")
        path = f"archives/youtube/{month}/{video_id}.json"
        return self.client.put_json(path, archive_data)

    def get_archive(self, video_id: str, month: str) -> dict:
        """Retrieve YouTube archive data from MinIO.

        Args:
            video_id: YouTube video ID.
            month: Month in YYYY-MM format.

        Returns:
            Archive data dictionary.
        """
        path = f"archives/youtube/{month}/{video_id}.json"
        return self.client.get_json(path)

    def store_transcript(self, video_id: str, transcript: str) -> str:
        """Store transcript in MinIO.

        Args:
            video_id: YouTube video ID.
            transcript: Transcript text.

        Returns:
            The path where transcript was stored.
        """
        path = f"transcripts/{video_id}.txt"
        return self.client.put_text(path, transcript)

    def get_transcript(self, video_id: str) -> str:
        """Retrieve transcript from MinIO.

        Args:
            video_id: YouTube video ID.

        Returns:
            Transcript text.
        """
        return self.client.get_text(f"transcripts/{video_id}.txt")

    def store_llm_output(
        self, video_id: str, output_type: str, data: dict
    ) -> str:
        """Store LLM output in MinIO.

        Args:
            video_id: YouTube video ID.
            output_type: Type of output (e.g., "tags", "summary").
            data: Output data dictionary.

        Returns:
            The path where output was stored.
        """
        path = f"llm_outputs/{video_id}/{output_type}.json"
        return self.client.put_json(path, data)

    def get_llm_output(self, video_id: str, output_type: str) -> dict:
        """Retrieve LLM output from MinIO.

        Args:
            video_id: YouTube video ID.
            output_type: Type of output (e.g., "tags", "summary").

        Returns:
            Output data dictionary.
        """
        path = f"llm_outputs/{video_id}/{output_type}.json"
        return self.client.get_json(path)
