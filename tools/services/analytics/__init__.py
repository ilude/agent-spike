"""Analytics service for URL pattern learning and classification tracking.

This service provides:
- URL classification tracking with confidence scores
- Pattern learning from high-confidence LLM classifications
- Batch re-evaluation of low-confidence URLs
- Pattern effectiveness tracking (precision/recall)
- SQLite-based storage for statistical analysis

Example usage:
    >>> from tools.services.analytics import create_pattern_tracker
    >>>
    >>> # Create pattern tracker
    >>> tracker = create_pattern_tracker()
    >>>
    >>> # Record a classification
    >>> tracker.record_classification(
    ...     url="https://github.com/user/repo",
    ...     video_id="abc123",
    ...     classification="content",
    ...     confidence=0.95,
    ...     method="llm"
    ... )
    >>>
    >>> # Add a learned pattern
    >>> tracker.add_learned_pattern(
    ...     pattern="gumroad.com",
    ...     pattern_type="domain",
    ...     classification="marketing",
    ...     confidence=0.95
    ... )
    >>>
    >>> # Check if URL matches learned patterns
    >>> result = tracker.check_learned_patterns("https://gumroad.com/product")
    >>> # Returns: ("marketing", "Matched learned pattern: gumroad.com", 0.95)
"""

from .models import (
    URLClassification,
    LearnedPattern,
    PendingReevaluation,
    PatternStats,
    DomainReevaluation,
)
from .protocols import PatternTracker
from .config import AnalyticsConfig, get_default_config
from .pattern_tracker import SQLitePatternTracker
from .factory import create_pattern_tracker

__all__ = [
    # Models
    "URLClassification",
    "LearnedPattern",
    "PendingReevaluation",
    "PatternStats",
    "DomainReevaluation",
    # Protocols
    "PatternTracker",
    # Configuration
    "AnalyticsConfig",
    "get_default_config",
    # Implementations
    "SQLitePatternTracker",
    # Factories
    "create_pattern_tracker",
]
