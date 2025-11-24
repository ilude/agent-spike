"""SurrealDB implementation of AsyncPatternTracker protocol."""

from typing import Optional
from datetime import datetime

from .config import AnalyticsConfig
from .models import PatternStats, DomainReevaluation, LearnedPatternRecord
from .pattern_matcher import extract_domain, find_matching_pattern
from . import repository


class SurrealDBPatternTracker:
    """SurrealDB implementation of AsyncPatternTracker protocol.

    Provides async interface for tracking URL classifications, learning patterns,
    and managing re-evaluation of low-confidence URLs using SurrealDB.

    Example:
        >>> tracker = SurrealDBPatternTracker()
        >>> await tracker.init_schema()
        >>> await tracker.record_classification(
        ...     url="https://github.com/user/repo",
        ...     video_id="abc123",
        ...     classification="content",
        ...     confidence=0.95,
        ...     method="llm"
        ... )
    """

    def __init__(self, config: Optional[AnalyticsConfig] = None):
        """Initialize SurrealDB pattern tracker.

        Args:
            config: Analytics configuration (uses defaults if not provided)
        """
        if config is None:
            from .config import get_default_config
            config = get_default_config()

        self.config = config

    async def init_schema(self) -> None:
        """Initialize SurrealDB schema (creates tables if not exist)."""
        await repository.init_analytics_schema()

    async def record_classification(
        self,
        url: str,
        video_id: str,
        classification: str,
        confidence: float,
        method: str,
        reason: Optional[str] = None,
        pattern_suggested: Optional[str] = None,
    ) -> None:
        """Record a URL classification."""
        domain = extract_domain(url)

        # Record classification
        await repository.record_classification(
            url=url,
            video_id=video_id,
            domain=domain,
            classification=classification,
            confidence=confidence,
            method=method,
            reason=reason,
            pattern_suggested=pattern_suggested,
        )

        # If low confidence, add to pending re-evaluation
        if confidence < self.config.low_confidence_threshold:
            await repository.add_or_update_pending_reevaluation(
                url=url,
                domain=domain,
                video_id=video_id,
                classification=classification,
                confidence=confidence,
            )

    async def add_learned_pattern(
        self,
        pattern: str,
        pattern_type: str,
        classification: str,
        confidence: float,
    ) -> None:
        """Add a learned pattern to the database."""
        await repository.add_learned_pattern(
            pattern=pattern,
            pattern_type=pattern_type,
            classification=classification,
            suggested_confidence=confidence,
        )

    async def check_learned_patterns(
        self, url: str
    ) -> Optional[tuple[str, str, float]]:
        """Check if URL matches any active learned patterns."""
        if not self.config.use_learned_patterns:
            return None

        # Get all active patterns
        patterns_data = await repository.get_active_patterns()

        # Convert to LearnedPatternRecord models
        patterns = [
            LearnedPatternRecord(
                pattern=p["pattern"],
                pattern_type=p["pattern_type"],
                classification=p["classification"],
                suggested_confidence=p.get("suggested_confidence", 0.9),
                times_applied=p.get("times_applied", 0),
                correct_count=p.get("correct_count", 0),
                precision=p.get("precision", 1.0),
                status=p.get("status", "active"),
                added_at=p.get("added_at", datetime.now()),
                last_used_at=p.get("last_used_at"),
            )
            for p in patterns_data
        ]

        # Find matching pattern
        matched = find_matching_pattern(url, patterns)

        if matched:
            # Update usage stats
            await repository.update_pattern_usage(matched.pattern)

            reason = f"Matched learned pattern: {matched.pattern} ({matched.pattern_type})"
            return (matched.classification, reason, matched.suggested_confidence)

        return None

    async def get_pattern_stats(self, pattern: str) -> Optional[PatternStats]:
        """Get statistics for a specific pattern."""
        result = await repository.get_pattern_stats(pattern)

        if not result:
            return None

        return PatternStats(
            pattern=result["pattern"],
            pattern_type=result["pattern_type"],
            classification=result["classification"],
            times_applied=result.get("times_applied", 0),
            correct_count=result.get("correct_count", 0),
            precision=result.get("precision", 1.0),
            status=result.get("status", "active"),
            added_at=result.get("added_at", datetime.now()),
            last_used_at=result.get("last_used_at"),
        )

    async def get_low_confidence_urls(
        self, threshold: float = 0.7
    ) -> list[dict]:
        """Get all URLs classified with confidence below threshold."""
        records = await repository.get_low_confidence_classifications(threshold)

        return [
            {
                "url": r.url,
                "video_id": r.video_id,
                "classification": r.classification,
                "confidence": r.confidence,
                "reason": r.reason,
            }
            for r in records
        ]

    async def get_domains_for_batch_reeval(
        self, min_count: int = 3
    ) -> list[DomainReevaluation]:
        """Get domains that have min_count+ low-confidence URLs for batch re-evaluation."""
        return await repository.get_domains_for_batch_reeval(min_count)

    async def mark_reevaluated(
        self,
        url: str,
        new_classification: str,
        new_confidence: float,
    ) -> None:
        """Mark a URL as re-evaluated with new classification."""
        await repository.mark_reevaluated(url)

    async def get_pattern_effectiveness_report(self) -> dict:
        """Get report on pattern effectiveness."""
        return await repository.get_pattern_effectiveness_report()

    async def update_pattern_stats(
        self,
        pattern: str,
        correct: bool,
    ) -> None:
        """Update pattern statistics after verification."""
        await repository.update_pattern_precision(pattern, correct)

    async def close(self) -> None:
        """Close database connection (no-op for SurrealDB singleton)."""
        pass
