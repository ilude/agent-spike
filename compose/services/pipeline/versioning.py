"""Git-based versioning for pipeline steps.

Computes version hashes from:
1. Git blob hash of the source file (if in git repo)
2. Hash of function source code (fallback)

This ensures version changes automatically when code changes,
eliminating the need for manual version bumping.
"""

import hashlib
import inspect
import subprocess
from functools import lru_cache
from pathlib import Path
from typing import Callable, Optional


@lru_cache(maxsize=128)
def get_git_blob_hash(file_path: str) -> Optional[str]:
    """Get git blob hash for a file.

    Uses `git hash-object` to get the content hash that git uses.
    This changes when the file content changes.

    Args:
        file_path: Path to source file

    Returns:
        Git blob hash (40 char hex), or None if not in git repo
    """
    try:
        result = subprocess.run(
            ["git", "hash-object", file_path],
            capture_output=True,
            text=True,
            timeout=5,
        )
        if result.returncode == 0:
            return result.stdout.strip()[:12]  # First 12 chars like short SHA
    except (subprocess.TimeoutExpired, FileNotFoundError):
        pass
    return None


def get_source_hash(func: Callable) -> str:
    """Get hash of function source code.

    Fallback for when git hash isn't available.

    Args:
        func: Function to hash

    Returns:
        SHA256 hash of source code (first 12 chars)
    """
    try:
        source = inspect.getsource(func)
        return hashlib.sha256(source.encode()).hexdigest()[:12]
    except (OSError, TypeError):
        # Can't get source (e.g., built-in function)
        return hashlib.sha256(func.__qualname__.encode()).hexdigest()[:12]


def get_version_hash(func: Callable) -> str:
    """Get version hash for a pipeline step function.

    Strategy:
    1. Try to get git blob hash of the source file
    2. Fall back to source code hash

    The version hash changes when the function code changes,
    triggering reprocessing of videos with stale versions.

    Args:
        func: Pipeline step function

    Returns:
        Version hash string (12 chars)
    """
    try:
        source_file = inspect.getfile(func)
        git_hash = get_git_blob_hash(source_file)
        if git_hash:
            return git_hash
    except (TypeError, OSError):
        pass

    return get_source_hash(func)


def get_source_file(func: Callable) -> Optional[str]:
    """Get the source file path for a function.

    Args:
        func: Function to inspect

    Returns:
        Source file path, or None if not available
    """
    try:
        return inspect.getfile(func)
    except (TypeError, OSError):
        return None


def invalidate_version_cache() -> None:
    """Clear the version hash cache.

    Call this when you want to force re-computation of hashes,
    e.g., after hot-reloading code.
    """
    get_git_blob_hash.cache_clear()
