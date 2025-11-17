"""Configuration for archive service."""

from dataclasses import dataclass
from pathlib import Path
from typing import Optional


@dataclass
class ArchiveConfig:
    """Configuration for local filesystem archive.

    Attributes:
        base_dir: Base directory for archives (e.g., projects/data/archive)
        organize_by_month: Whether to organize files by YYYY-MM directories
        compression: Optional compression format ("gzip", "bz2", None)
    """

    base_dir: Path
    organize_by_month: bool = True
    compression: Optional[str] = None  # Future: "gzip", "bz2"

    def __post_init__(self):
        """Validate configuration."""
        if self.compression and self.compression not in ("gzip", "bz2"):
            raise ValueError(f"Invalid compression: {self.compression}. Must be 'gzip', 'bz2', or None")
