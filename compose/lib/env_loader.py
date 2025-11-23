"""Dotenv utilities for loading environment from git root.

This module provides backward-compatible functions for loading .env files.
For new code, prefer using config_manager directly:

    from compose.lib.config_manager import config
    value = config.get("ANTHROPIC_API_KEY")
"""

from pathlib import Path
from typing import Any, Optional

from compose.lib.config_manager import config, get_config, get_config_async


def find_git_root(start_path: Optional[Path] = None) -> Path:
    """Walk up directory tree to find .git/ folder.

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
    """Load .env from git root directory.

    Note: This is now handled automatically by config_manager on import.
    This function exists for backward compatibility.
    """
    # config_manager loads .env on initialization
    # Just ensure it's been accessed
    _ = config


def get(key: str, default: Any = None) -> Any:
    """Get a configuration value.

    Args:
        key: Configuration key
        default: Default value if not found

    Returns:
        Configuration value
    """
    return get_config(key, default)


async def get_async(key: str, default: Any = None) -> Any:
    """Get a configuration value with async DB lookup.

    Args:
        key: Configuration key
        default: Default value if not found

    Returns:
        Configuration value
    """
    return await get_config_async(key, default)


# Re-export for convenience
__all__ = [
    "find_git_root",
    "load_root_env",
    "get",
    "get_async",
    "config",
    "get_config",
    "get_config_async",
]
