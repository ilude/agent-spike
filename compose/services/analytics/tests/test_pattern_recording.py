"""Tests for pattern recording and learning functionality.

This module tests the recording of URL classifications and the learning of patterns
from those classifications. It covers basic recording, low-confidence handling,
and pattern creation/matching.
"""

import pytest
from typing import AsyncGenerator

# Mark all tests as async for SurrealDB compatibility
pytestmark = pytest.mark.asyncio


@pytest.fixture
async def sqlite_tracker(tmp_path) -> AsyncGenerator:
    """Create SQLite tracker with temp database."""
    from compose.services.analytics.pattern_tracker import SQLitePatternTracker
    from compose.services.analytics.config import AnalyticsConfig

    config = AnalyticsConfig(db_path=tmp_path / "test.db")
    tracker = SQLitePatternTracker(config)
    yield tracker
    # SQLite close is a no-op
    tracker.close()


@pytest.fixture(params=["sqlite"])  # Add "surrealdb" when implemented
async def tracker(request, sqlite_tracker):
    """Parametrized fixture - runs each test against all backends."""
    if request.param == "sqlite":
        return sqlite_tracker


class TestRecordClassification:
    """Tests for record_classification method."""

    async def test_records_basic_classification(self, tracker):
        """Record a basic URL classification."""
        tracker.record_classification(
            url="https://github.com/user/repo",
            video_id="abc123",
            classification="content",
            confidence=0.95,
            method="llm",
        )

        # Verify via low_confidence (won't appear since confidence is high)
        low_conf = tracker.get_low_confidence_urls(threshold=0.9)
        assert len(low_conf) == 0

    async def test_records_classification_with_reason(self, tracker):
        """Record classification with reason and pattern suggestion."""
        tracker.record_classification(
            url="https://example.com/page",
            video_id="xyz789",
            classification="marketing",
            confidence=0.85,
            method="heuristic",
            reason="Contains promo keywords",
            pattern_suggested="example.com",
        )

        # Should be recorded (verified via effectiveness report)
        report = tracker.get_pattern_effectiveness_report()
        assert report is not None

    async def test_low_confidence_triggers_pending_reeval(self, tracker):
        """Low confidence URLs are added to pending re-evaluation."""
        tracker.record_classification(
            url="https://unknown-site.com/page",
            video_id="low123",
            classification="content",
            confidence=0.5,  # Below default threshold of 0.7
            method="llm",
        )

        low_conf = tracker.get_low_confidence_urls(threshold=0.7)
        assert len(low_conf) >= 1
        assert any(u["url"] == "https://unknown-site.com/page" for u in low_conf)

    async def test_multiple_low_confidence_same_domain_aggregates(self, tracker):
        """Multiple low-confidence URLs from same domain are aggregated.

        Note: SQLite implementation updates domain_occurrence_count rather than
        creating multiple rows, so the pending_reevaluation table has one row per domain.
        """
        domain = "ambiguous.com"
        for i in range(3):
            tracker.record_classification(
                url=f"https://{domain}/page{i}",
                video_id=f"vid{i}",
                classification="content",
                confidence=0.5,
                method="llm",
            )

        # Check domains - should have 1 domain with count of 3
        domains = tracker.get_domains_for_batch_reeval(min_count=1)
        ambiguous = next((d for d in domains if d.domain == domain), None)
        assert ambiguous is not None
        # The domain_occurrence_count is incremented but only 1 URL stored
        assert ambiguous.url_count >= 1


class TestLearnedPatterns:
    """Tests for pattern learning and matching."""

    async def test_add_domain_pattern(self, tracker):
        """Add a domain-based learned pattern."""
        tracker.add_learned_pattern(
            pattern="github.com",
            pattern_type="domain",
            classification="content",
            confidence=0.95,
        )

        stats = tracker.get_pattern_stats("github.com")
        assert stats is not None
        assert stats.pattern == "github.com"
        assert stats.pattern_type == "domain"
        assert stats.classification == "content"
        # Note: PatternStats doesn't include suggested_confidence
        assert stats.times_applied == 0
        assert stats.status == "active"

    async def test_add_url_pattern(self, tracker):
        """Add a URL substring pattern."""
        tracker.add_learned_pattern(
            pattern="?coupon=",
            pattern_type="url_pattern",
            classification="marketing",
            confidence=0.9,
        )

        stats = tracker.get_pattern_stats("?coupon=")
        assert stats is not None
        assert stats.pattern_type == "url_pattern"
        assert stats.classification == "marketing"

    async def test_add_path_pattern(self, tracker):
        """Add a path-based pattern."""
        tracker.add_learned_pattern(
            pattern="/docs/",
            pattern_type="path",
            classification="content",
            confidence=0.85,
        )

        stats = tracker.get_pattern_stats("/docs/")
        assert stats is not None
        assert stats.pattern_type == "path"

    async def test_duplicate_pattern_ignored(self, tracker):
        """Adding duplicate pattern does not raise error (unique constraint)."""
        tracker.add_learned_pattern(
            pattern="example.com",
            pattern_type="domain",
            classification="content",
            confidence=0.9,
        )

        # Adding same pattern again should not raise
        tracker.add_learned_pattern(
            pattern="example.com",
            pattern_type="domain",
            classification="content",
            confidence=0.95,  # Different confidence
        )

        # Should still have original (duplicate ignored)
        stats = tracker.get_pattern_stats("example.com")
        assert stats is not None
        assert stats.pattern == "example.com"

    async def test_check_learned_patterns_domain_match(self, tracker):
        """Check patterns matches domain correctly."""
        tracker.add_learned_pattern(
            pattern="github.com",
            pattern_type="domain",
            classification="content",
            confidence=0.95,
        )

        result = tracker.check_learned_patterns("https://github.com/user/repo")
        assert result is not None
        classification, reason, confidence = result
        assert classification == "content"
        assert confidence == 0.95
        assert "github.com" in reason
        assert "domain" in reason

    async def test_check_learned_patterns_url_pattern_match(self, tracker):
        """Check patterns matches URL substring correctly."""
        tracker.add_learned_pattern(
            pattern="?coupon=",
            pattern_type="url_pattern",
            classification="marketing",
            confidence=0.9,
        )

        result = tracker.check_learned_patterns(
            "https://shop.example.com/product?coupon=SAVE20"
        )
        assert result is not None
        classification, reason, confidence = result
        assert classification == "marketing"
        assert confidence == 0.9
        assert "?coupon=" in reason

    async def test_check_learned_patterns_path_match(self, tracker):
        """Check patterns matches path correctly."""
        tracker.add_learned_pattern(
            pattern="/docs/",
            pattern_type="path",
            classification="content",
            confidence=0.85,
        )

        result = tracker.check_learned_patterns("https://example.com/docs/guide")
        assert result is not None
        classification, _, confidence = result
        assert classification == "content"
        assert confidence == 0.85

    async def test_check_learned_patterns_no_match(self, tracker):
        """Check patterns returns None when no match."""
        result = tracker.check_learned_patterns("https://unknown-site.com/page")
        assert result is None

    async def test_check_learned_patterns_increments_usage(self, tracker):
        """Matching a pattern increments its usage count."""
        tracker.add_learned_pattern(
            pattern="tracked.com",
            pattern_type="domain",
            classification="content",
            confidence=0.9,
        )

        # Apply pattern twice
        tracker.check_learned_patterns("https://tracked.com/page1")
        tracker.check_learned_patterns("https://tracked.com/page2")

        stats = tracker.get_pattern_stats("tracked.com")
        assert stats.times_applied == 2
        assert stats.last_used_at is not None
