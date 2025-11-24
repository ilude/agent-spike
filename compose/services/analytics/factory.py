"""Factory functions for creating analytics service instances."""

from pathlib import Path
from typing import Optional, Union

from .config import AnalyticsConfig, get_default_config, PatternTrackerBackend
from .pattern_tracker import SQLitePatternTracker


def create_pattern_tracker(
    db_path: Optional[Path] = None,
    config: Optional[AnalyticsConfig] = None,
) -> SQLitePatternTracker:
    """Create a pattern tracker with sensible defaults.

    Args:
        db_path: Optional custom database path (overrides config)
        config: Optional custom configuration

    Returns:
        Configured SQLitePatternTracker instance

    Example:
        >>> # Use defaults (projects/data/analytics/url_patterns.db)
        >>> tracker = create_pattern_tracker()
        >>>
        >>> # Custom database path
        >>> tracker = create_pattern_tracker(db_path=Path("/custom/path.db"))
        >>>
        >>> # Custom configuration
        >>> config = AnalyticsConfig(pattern_suggestion_threshold=0.8)
        >>> tracker = create_pattern_tracker(config=config)
    """
    if config is None:
        config = get_default_config()

    # Override db_path if provided
    if db_path is not None:
        config.db_path = db_path

    return SQLitePatternTracker(config=config)


async def create_async_pattern_tracker(
    config: Optional[AnalyticsConfig] = None,
):
    """Create an async pattern tracker based on configuration.

    Selects backend based on config.backend:
    - PatternTrackerBackend.SQLITE: SQLite (sync API, not async)
    - PatternTrackerBackend.SURREALDB: SurrealDB (async native)

    Args:
        config: Optional custom configuration (reads PATTERN_TRACKER_BACKEND env var)

    Returns:
        Configured async pattern tracker (SurrealDBPatternTracker)

    Example:
        >>> # Use defaults (checks PATTERN_TRACKER_BACKEND env var, defaults to sqlite)
        >>> tracker = await create_async_pattern_tracker()
        >>>
        >>> # Force SurrealDB backend
        >>> from .config import PatternTrackerBackend
        >>> config = AnalyticsConfig(backend=PatternTrackerBackend.SURREALDB)
        >>> tracker = await create_async_pattern_tracker(config=config)
    """
    if config is None:
        config = get_default_config()

    if config.backend == PatternTrackerBackend.SURREALDB:
        from .surrealdb_tracker import SurrealDBPatternTracker

        tracker = SurrealDBPatternTracker(config)
        await tracker.init_schema()
        return tracker
    else:
        # SQLite backend (default) - note: not truly async, but wrapped
        raise NotImplementedError(
            "Async SQLite tracker not implemented yet. "
            "Use create_pattern_tracker() for sync SQLite or set "
            "PATTERN_TRACKER_BACKEND=surrealdb for async SurrealDB."
        )
