"""Factory functions for creating analytics service instances."""

from pathlib import Path
from typing import Optional

from .config import AnalyticsConfig, get_default_config
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
