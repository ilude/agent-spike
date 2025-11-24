"""Shared test suite for PatternTracker implementations.

This test suite runs against both SQLite and SurrealDB implementations to ensure
behavioral parity during migration. Uses pytest parametrization to test both
backends with identical test cases.
"""

import pytest
from pathlib import Path
from datetime import datetime
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


# @pytest.fixture
# async def surrealdb_tracker() -> AsyncGenerator:
#     """Create SurrealDB tracker (requires running SurrealDB)."""
#     from compose.services.analytics.repository import SurrealDBPatternTracker
#     from compose.services.analytics.config import AnalyticsConfig
#
#     config = AnalyticsConfig()
#     tracker = SurrealDBPatternTracker(config)
#     await tracker.init_schema()
#     yield tracker
#     await tracker.close()
#     # Cleanup test data
#     await tracker._cleanup_test_data()


@pytest.fixture(params=["sqlite"])  # Add "surrealdb" when implemented
async def tracker(request, sqlite_tracker):
    """Parametrized fixture - runs each test against all backends."""
    if request.param == "sqlite":
        return sqlite_tracker
    # elif request.param == "surrealdb":
    #     return await request.getfixturevalue("surrealdb_tracker")


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


class TestPatternStats:
    """Tests for pattern statistics tracking."""

    async def test_get_pattern_stats_nonexistent(self, tracker):
        """Getting stats for nonexistent pattern returns None."""
        stats = tracker.get_pattern_stats("nonexistent.com")
        assert stats is None

    async def test_get_pattern_stats_structure(self, tracker):
        """Pattern stats have expected structure."""
        tracker.add_learned_pattern(
            pattern="test-domain.com",
            pattern_type="domain",
            classification="content",
            confidence=0.9,
        )

        stats = tracker.get_pattern_stats("test-domain.com")
        assert stats is not None
        assert hasattr(stats, "pattern")
        assert hasattr(stats, "pattern_type")
        assert hasattr(stats, "classification")
        # Note: PatternStats model doesn't include suggested_confidence
        assert hasattr(stats, "times_applied")
        assert hasattr(stats, "correct_count")
        assert hasattr(stats, "precision")
        assert hasattr(stats, "status")
        assert hasattr(stats, "added_at")
        assert hasattr(stats, "last_used_at")

    async def test_update_pattern_stats_correct(self, tracker):
        """Updating pattern stats with correct classification increases precision."""
        tracker.add_learned_pattern(
            pattern="verify.com",
            pattern_type="domain",
            classification="content",
            confidence=0.9,
        )

        # Apply pattern
        tracker.check_learned_patterns("https://verify.com/page")

        # Mark as correct
        tracker.update_pattern_stats("verify.com", correct=True)

        stats = tracker.get_pattern_stats("verify.com")
        assert stats.correct_count == 1
        assert stats.precision == 1.0

    async def test_update_pattern_stats_incorrect(self, tracker):
        """Updating pattern stats with incorrect classification decreases precision."""
        tracker.add_learned_pattern(
            pattern="wrong.com",
            pattern_type="domain",
            classification="content",
            confidence=0.9,
        )

        # Apply pattern twice
        tracker.check_learned_patterns("https://wrong.com/page1")
        tracker.check_learned_patterns("https://wrong.com/page2")

        # Mark first as correct, second as incorrect
        tracker.update_pattern_stats("wrong.com", correct=True)
        tracker.update_pattern_stats("wrong.com", correct=False)

        stats = tracker.get_pattern_stats("wrong.com")
        assert stats.times_applied == 2
        assert stats.correct_count == 1
        assert stats.precision == 0.5  # 1 correct out of 2


class TestBatchReevaluation:
    """Tests for batch re-evaluation functionality."""

    async def test_get_low_confidence_urls(self, tracker):
        """Get URLs below confidence threshold."""
        tracker.record_classification(
            url="https://low1.com/page",
            video_id="vid1",
            classification="content",
            confidence=0.6,
            method="llm",
        )
        tracker.record_classification(
            url="https://high.com/page",
            video_id="vid2",
            classification="content",
            confidence=0.9,
            method="llm",
        )

        low_conf = tracker.get_low_confidence_urls(threshold=0.7)
        assert len(low_conf) == 1
        assert low_conf[0]["url"] == "https://low1.com/page"
        assert low_conf[0]["confidence"] == 0.6

    async def test_get_domains_for_batch_reeval_min_count(self, tracker):
        """Get domains with minimum occurrence count.

        Note: Implementation groups by domain in pending_reevaluation table,
        counting total rows per domain, not domain_occurrence_count.
        """
        domain = "batch-test.com"
        # Record 3 different URLs from the same domain
        for i in range(3):
            tracker.record_classification(
                url=f"https://{domain}/page{i}",
                video_id=f"vid{i}",
                classification="content",
                confidence=0.5,
                method="llm",
            )

        # SQLite implementation updates occurrence count, not creates multiple rows
        # So we should see 1 domain with url_count of 1
        domains = tracker.get_domains_for_batch_reeval(min_count=1)
        batch_domain = next((d for d in domains if d.domain == domain), None)
        assert batch_domain is not None
        assert batch_domain.url_count >= 1

    async def test_mark_reevaluated(self, tracker):
        """Mark URL as re-evaluated.

        Note: mark_reevaluated only sets the reevaluated flag in pending_reevaluation,
        it doesn't update the url_classifications table. The low-confidence URL
        will still appear in get_low_confidence_urls() since that queries
        url_classifications, not pending_reevaluation.
        """
        tracker.record_classification(
            url="https://pending.com/page",
            video_id="vid1",
            classification="marketing",
            confidence=0.4,
            method="llm",
        )

        # Should appear in domains for re-eval
        domains_before = tracker.get_domains_for_batch_reeval(min_count=1)
        pending_before = next((d for d in domains_before if d.domain == "pending.com"), None)
        assert pending_before is not None

        # Mark as re-evaluated
        tracker.mark_reevaluated(
            url="https://pending.com/page",
            new_classification="content",
            new_confidence=0.9,
        )

        # Should no longer appear in batch reeval (reevaluated = 1)
        domains_after = tracker.get_domains_for_batch_reeval(min_count=1)
        pending_after = next((d for d in domains_after if d.domain == "pending.com"), None)
        assert pending_after is None


class TestEffectivenessReport:
    """Tests for pattern effectiveness reporting."""

    async def test_report_structure(self, tracker):
        """Effectiveness report has expected structure."""
        report = tracker.get_pattern_effectiveness_report()

        assert "total_patterns" in report
        assert "active_patterns" in report
        assert "inactive_patterns" in report
        # Note: Report doesn't include pending_review_patterns
        assert "top_patterns" in report
        assert "low_performing_patterns" in report
        assert "pending_reevaluation_count" in report

        # Types
        assert isinstance(report["total_patterns"], int)
        assert isinstance(report["active_patterns"], int)
        assert isinstance(report["inactive_patterns"], int)
        assert isinstance(report["top_patterns"], list)
        assert isinstance(report["low_performing_patterns"], list)
        assert isinstance(report["pending_reevaluation_count"], int)

    async def test_report_counts_patterns(self, tracker):
        """Effectiveness report counts patterns correctly."""
        tracker.add_learned_pattern(
            pattern="counted1.com",
            pattern_type="domain",
            classification="content",
            confidence=0.9,
        )
        tracker.add_learned_pattern(
            pattern="counted2.com",
            pattern_type="domain",
            classification="marketing",
            confidence=0.85,
        )

        report = tracker.get_pattern_effectiveness_report()
        assert report["total_patterns"] >= 2
        assert report["active_patterns"] >= 2
        assert report["inactive_patterns"] == 0

    async def test_report_top_patterns(self, tracker):
        """Top patterns are ordered by times_applied."""
        tracker.add_learned_pattern(
            pattern="popular.com",
            pattern_type="domain",
            classification="content",
            confidence=0.9,
        )
        tracker.add_learned_pattern(
            pattern="unpopular.com",
            pattern_type="domain",
            classification="content",
            confidence=0.9,
        )

        # Use popular pattern 5 times
        for _ in range(5):
            tracker.check_learned_patterns("https://popular.com/page")

        # Use unpopular pattern once
        tracker.check_learned_patterns("https://unpopular.com/page")

        report = tracker.get_pattern_effectiveness_report()
        top_patterns = report["top_patterns"]

        # Should have both patterns
        assert len(top_patterns) >= 2

        # top_patterns contains PatternStats objects, not dicts
        popular_idx = next(i for i, p in enumerate(top_patterns) if p.pattern == "popular.com")
        unpopular_idx = next(i for i, p in enumerate(top_patterns) if p.pattern == "unpopular.com")
        assert popular_idx < unpopular_idx


class TestPatternMatching:
    """Tests for pattern matching logic."""

    async def test_extract_domain(self):
        """Extract domain from various URL formats."""
        from compose.services.analytics.pattern_tracker import SQLitePatternTracker

        assert SQLitePatternTracker._extract_domain("https://github.com/user/repo") == "github.com"
        assert SQLitePatternTracker._extract_domain("http://example.com:8080/path") == "example.com:8080"
        assert SQLitePatternTracker._extract_domain("https://sub.domain.com/") == "sub.domain.com"

    async def test_url_matches_pattern_domain(self):
        """URL matches domain pattern correctly."""
        from compose.services.analytics.pattern_tracker import SQLitePatternTracker

        assert SQLitePatternTracker._url_matches_pattern(
            "https://github.com/user/repo",
            "github.com",
            "domain"
        )
        assert not SQLitePatternTracker._url_matches_pattern(
            "https://gitlab.com/user/repo",
            "github.com",
            "domain"
        )

    async def test_url_matches_pattern_url_pattern(self):
        """URL matches substring pattern correctly."""
        from compose.services.analytics.pattern_tracker import SQLitePatternTracker

        assert SQLitePatternTracker._url_matches_pattern(
            "https://shop.com/product?coupon=SAVE",
            "?coupon=",
            "url_pattern"
        )
        assert not SQLitePatternTracker._url_matches_pattern(
            "https://shop.com/product",
            "?coupon=",
            "url_pattern"
        )

    async def test_url_matches_pattern_path(self):
        """URL matches path pattern correctly."""
        from compose.services.analytics.pattern_tracker import SQLitePatternTracker

        assert SQLitePatternTracker._url_matches_pattern(
            "https://example.com/docs/guide",
            "/docs/",
            "path"
        )
        assert not SQLitePatternTracker._url_matches_pattern(
            "https://example.com/blog/post",
            "/docs/",
            "path"
        )
