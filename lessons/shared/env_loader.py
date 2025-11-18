"""Dotenv utilities for loading environment from git root."""

from pathlib import Path
from typing import Optional

from dotenv import load_dotenv


def find_git_root(start_path: Optional[Path] = None) -> Path:
    """
    Walk up directory tree to find .git/ folder.

    Args:
        start_path: Starting directory (defaults to current file's directory)

    Returns:
        Path to directory containing .git/ folder

    Raises:
        FileNotFoundError: If no .git/ directory found in any parent
    """
    current = start_path or Path.cwd()
    current = current.resolve()

    while current != current.parent:
        if (current / ".git").exists():
            return current
        current = current.parent

    raise FileNotFoundError("No .git directory found in any parent directory")


def load_root_env() -> None:
    """Load .env from git root directory."""
    git_root = find_git_root()
    env_path = git_root / ".env"
    load_dotenv(dotenv_path=env_path)
