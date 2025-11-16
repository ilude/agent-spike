"""Configuration for analytics service."""

from pathlib import Path
from dataclasses import dataclass, field


@dataclass
class AnalyticsConfig:
    """Configuration for pattern tracker analytics."""

    # Database path
    db_path: Path = field(
        default_factory=lambda: Path("projects/data/analytics/url_patterns.db")
    )

    # Pattern learning thresholds
    pattern_suggestion_threshold: float = 0.7  # Confidence needed to suggest pattern
    low_confidence_threshold: float = 0.7  # Below this, URL goes to pending re-eval
    pattern_precision_threshold: float = 0.7  # Below this, pattern becomes inactive

    # Re-evaluation settings
    min_domain_occurrences: int = 3  # Domain must appear 3+ times for batch re-eval
    reevaluation_batch_size: int = 10  # Max URLs to re-evaluate per batch

    # Pattern application
    use_learned_patterns: bool = True  # Enable/disable learned pattern checking


def get_default_config() -> AnalyticsConfig:
    """Get default analytics configuration.

    Returns:
        AnalyticsConfig with sensible defaults

    Example:
        >>> config = get_default_config()
        >>> config.pattern_suggestion_threshold
        0.7
    """
    return AnalyticsConfig()
