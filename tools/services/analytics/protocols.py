"""Protocols for analytics service (dependency injection interface)."""

from typing import Protocol, Optional
from .models import (
    URLClassification,
    LearnedPattern,
    PatternStats,
    DomainReevaluation,
)


class PatternTracker(Protocol):
    """Protocol for URL pattern learning and analytics service.

    This protocol defines the interface for tracking URL classifications,
    learning patterns, and managing re-evaluation of low-confidence URLs.
    """

    def record_classification(
        self,
        url: str,
        video_id: str,
        classification: str,
        confidence: float,
        method: str,
        reason: Optional[str] = None,
        pattern_suggested: Optional[str] = None,
    ) -> None:
        """Record a URL classification.

        Args:
            url: Full URL
            video_id: YouTube video ID
            classification: 'content' or 'marketing'
            confidence: 0.0-1.0
            method: 'heuristic', 'llm', or 'learned_pattern'
            reason: Explanation for classification
            pattern_suggested: Pattern suggested by LLM (if any)
        """
        ...

    def add_learned_pattern(
        self,
        pattern: str,
        pattern_type: str,
        classification: str,
        confidence: float,
    ) -> None:
        """Add a learned pattern to the database.

        Args:
            pattern: Pattern string (e.g., "gumroad.com", "?coupon=")
            pattern_type: 'domain', 'url_pattern', or 'path'
            classification: 'content' or 'marketing'
            confidence: Original LLM confidence that suggested this pattern
        """
        ...

    def check_learned_patterns(
        self, url: str
    ) -> Optional[tuple[str, str, float]]:
        """Check if URL matches any active learned patterns.

        Args:
            url: URL to check

        Returns:
            Tuple of (classification, reason, confidence) if match found, None otherwise
        """
        ...

    def get_pattern_stats(self, pattern: str) -> Optional[PatternStats]:
        """Get statistics for a specific pattern.

        Args:
            pattern: Pattern to look up

        Returns:
            PatternStats if found, None otherwise
        """
        ...

    def get_low_confidence_urls(
        self, threshold: float = 0.7
    ) -> list[dict]:
        """Get all URLs classified with confidence below threshold.

        Args:
            threshold: Confidence threshold (default 0.7)

        Returns:
            List of dicts with url, video_id, classification, confidence
        """
        ...

    def get_domains_for_batch_reeval(
        self, min_count: int = 3
    ) -> list[DomainReevaluation]:
        """Get domains that have min_count+ low-confidence URLs for batch re-evaluation.

        Args:
            min_count: Minimum number of URLs from domain (default 3)

        Returns:
            List of DomainReevaluation objects
        """
        ...

    def mark_reevaluated(
        self,
        url: str,
        new_classification: str,
        new_confidence: float,
    ) -> None:
        """Mark a URL as re-evaluated with new classification.

        Args:
            url: URL that was re-evaluated
            new_classification: Updated classification
            new_confidence: Updated confidence
        """
        ...

    def get_pattern_effectiveness_report(self) -> dict:
        """Get report on pattern effectiveness.

        Returns:
            Dict with:
                - total_patterns: int
                - active_patterns: int
                - inactive_patterns: int
                - top_patterns: list[PatternStats] (top 10 by times_applied)
                - low_performing_patterns: list[PatternStats] (precision < threshold)
                - pending_reevaluation_count: int
        """
        ...

    def update_pattern_stats(
        self,
        pattern: str,
        correct: bool,
    ) -> None:
        """Update pattern statistics after verification.

        Args:
            pattern: Pattern that was applied
            correct: Whether the classification was correct
        """
        ...

    def close(self) -> None:
        """Close database connection."""
        ...
