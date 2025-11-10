"""Base utilities for production scripts.

This module provides common setup functions for all scripts in tools/scripts/
to eliminate boilerplate and ensure consistent configuration.

Usage:
    >>> from tools.scripts.script_base import setup_script_environment
    >>> project_root = setup_script_environment(needs_agent=True)
    >>> # Now your script can import from tools.services, etc.
"""

import sys
from pathlib import Path


def setup_script_environment(
    needs_agent: bool = False,
    load_env: bool = True
) -> Path:
    """Setup paths and environment for production scripts.

    Configures sys.path for proper imports and optionally loads environment variables.
    This eliminates 7-10 lines of boilerplate from each script.

    Args:
        needs_agent: If True, adds lessons/lesson-001 to path for agent imports.
                    Required for scripts that use youtube_agent or webpage_agent.
        load_env: If True, loads .env file from project root using env_loader.
                 Set to False if script doesn't need API keys.

    Returns:
        Path to project root directory

    Example (minimal script):
        >>> from tools.scripts.script_base import setup_script_environment
        >>> setup_script_environment()  # That's it!
        >>> from tools.services.cache import create_qdrant_cache
        >>> cache = create_qdrant_cache()

    Example (script needing agents):
        >>> from tools.scripts.script_base import setup_script_environment
        >>> setup_script_environment(needs_agent=True)
        >>> from youtube_agent.agent import create_agent
        >>> from tools.services.youtube import get_transcript

    Example (no env needed):
        >>> setup_script_environment(load_env=False)
        >>> # Script that doesn't use API keys
    """
    # Calculate project root (tools/scripts -> tools -> project root)
    script_path = Path(__file__).resolve()
    project_root = script_path.parent.parent.parent

    # Add project root to path (for tools.* imports)
    if str(project_root) not in sys.path:
        sys.path.insert(0, str(project_root))

    # Add lesson-001 to path (for agent imports)
    if needs_agent:
        lesson_path = project_root / "lessons" / "lesson-001"
        if str(lesson_path) not in sys.path:
            sys.path.insert(0, str(lesson_path))

    # Load environment variables from .env
    if load_env:
        from tools.env_loader import load_root_env
        load_root_env()

    return project_root
