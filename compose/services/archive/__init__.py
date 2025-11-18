"""Archive service for storing expensive-to-fetch content.

Composition-based design with protocol-first interfaces.

Example usage:
    >>> from compose.services.archive import create_local_archive_writer
    >>>
    >>> # Use defaults (projects/data/archive)
    >>> archive = create_local_archive_writer()
    >>> archive.archive_youtube_video(video_id, url, transcript)
    >>>
    >>> # Custom configuration
    >>> from compose.services.archive import ArchiveConfig, LocalArchiveWriter
    >>> config = ArchiveConfig(base_dir=Path("/custom/path"))
    >>> archive = LocalArchiveWriter(config)
"""

from .models import YouTubeArchive, LLMOutput, ProcessingRecord, ImportMetadata, ChannelContext
from .protocols import ArchiveWriter, ArchiveReader
from .config import ArchiveConfig
from .local_writer import LocalArchiveWriter, create_local_archive_writer
from .local_reader import LocalArchiveReader, create_local_archive_reader
from .manager import ArchiveManager, create_archive_manager

__all__ = [
    # Models
    "YouTubeArchive",
    "LLMOutput",
    "ProcessingRecord",
    "ImportMetadata",
    "ChannelContext",
    # Protocols
    "ArchiveWriter",
    "ArchiveReader",
    # Configuration
    "ArchiveConfig",
    # Implementations
    "LocalArchiveWriter",
    "LocalArchiveReader",
    "ArchiveManager",
    # Factories
    "create_local_archive_writer",
    "create_local_archive_reader",
    "create_archive_manager",
]
