"""Base utilities for lesson scripts and tests.

Provides consistent path setup for all lesson code, eliminating boilerplate
sys.path manipulation that's repeated across 35+ files.

Usage:
    >>> from lessons.lesson_base import setup_lesson_environment
    >>> project_root = setup_lesson_environment()
    >>> # Now you can import from tools.services, youtube_agent, etc.

    >>> # For scripts needing multiple lessons:
    >>> setup_lesson_environment(lessons=["lesson-001", "lesson-002"])
    >>> from youtube_agent.agent import create_agent
    >>> from webpage_agent.agent import create_webpage_agent
"""

import sys
from pathlib import Path
from typing import List, Optional


def setup_lesson_environment(
    lessons: Optional[List[str]] = None,
    load_env: bool = True
) -> Path:
    """Setup paths and environment for lesson scripts and tests.

    Configures sys.path for proper imports across lessons and tools.
    This eliminates 3-8 lines of boilerplate from each test/script file.

    Args:
        lessons: Optional list of lesson directories to add to path
                (e.g., ["lesson-001", "lesson-002"]).
                Enables importing agents from other lessons.
        load_env: If True, loads .env file from project root.
                 Set to False if script doesn't need API keys.

    Returns:
        Path to project root directory

    Example (single lesson test):
        >>> from lessons.lesson_base import setup_lesson_environment
        >>> setup_lesson_environment()
        >>> # Can now import from tools.services

    Example (multi-lesson orchestrator):
        >>> setup_lesson_environment(lessons=["lesson-001", "lesson-002"])
        >>> from youtube_agent.agent import create_agent
        >>> from webpage_agent.agent import create_webpage_agent

    Example (no env needed):
        >>> setup_lesson_environment(load_env=False)
        >>> # Script that doesn't use API keys
    """
    # Calculate project root (lessons/lesson_base.py -> lessons -> project root)
    lesson_base_path = Path(__file__).resolve()
    lessons_dir = lesson_base_path.parent
    project_root = lessons_dir.parent

    # Add project root to path (for tools.* imports)
    if str(project_root) not in sys.path:
        sys.path.insert(0, str(project_root))

    # Add lessons directory to path (for cross-lesson imports)
    if str(lessons_dir) not in sys.path:
        sys.path.insert(0, str(lessons_dir))

    # Add specific lesson directories if requested
    if lessons:
        for lesson in lessons:
            lesson_path = lessons_dir / lesson
            if lesson_path.exists() and str(lesson_path) not in sys.path:
                sys.path.insert(0, str(lesson_path))

    # Load environment variables from .env
    if load_env:
        from compose.lib.env_loader import load_root_env
        load_root_env()

    return project_root
