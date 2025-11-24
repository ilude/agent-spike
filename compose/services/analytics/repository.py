"""SurrealDB repository for analytics pattern tracking operations.

Provides:
- Schema initialization for pattern analytics tables
- CRUD operations for URL classifications
- CRUD operations for learned patterns
- CRUD operations for pending re-evaluations
- Analytics queries for pattern effectiveness
"""

import logging
from datetime import datetime
from typing import Optional

from compose.services.surrealdb.driver import execute_query
from .models import (
    DomainReevaluation,
    LearnedPatternRecord,
    PatternStats,
    PendingReevaluationRecord,
    URLClassificationRecord,
)

logger = logging.getLogger(__name__)


def _parse_datetime(value, default: datetime | None = None) -> datetime:
    """Parse datetime from SurrealDB result.

    SurrealDB can return datetimes as either ISO strings or native datetime objects.
    This handles both cases safely.
    """
    if isinstance(value, datetime):
        return value
    if isinstance(value, str):
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    return default if default is not None else datetime.now()


def _parse_datetime_optional(value) -> datetime | None:
    """Parse optional datetime from SurrealDB result."""
    if value is None:
        return None
    if isinstance(value, datetime):
        return value
    if isinstance(value, str):
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    return None


# =============================================================================
# Schema Initialization
# =============================================================================


async def init_analytics_schema() -> None:
    """Initialize SurrealDB schema for analytics tables.

    Creates 3 tables: pattern_classification, pattern_learned, pattern_pending_reeval
    """
    queries = [
        # URL Classifications
        """
        DEFINE TABLE pattern_classification SCHEMAFULL;
        DEFINE FIELD url ON TABLE pattern_classification TYPE string;
        DEFINE FIELD domain ON TABLE pattern_classification TYPE string;
        DEFINE FIELD video_id ON TABLE pattern_classification TYPE string;
        DEFINE FIELD classification ON TABLE pattern_classification TYPE string ASSERT $value IN ["content", "marketing"];
        DEFINE FIELD confidence ON TABLE pattern_classification TYPE float ASSERT $value >= 0.0 AND $value <= 1.0;
        DEFINE FIELD method ON TABLE pattern_classification TYPE string ASSERT $value IN ["heuristic", "llm", "learned_pattern"];
        DEFINE FIELD reason ON TABLE pattern_classification TYPE option<string>;
        DEFINE FIELD pattern_suggested ON TABLE pattern_classification TYPE option<string>;
        DEFINE FIELD classified_at ON TABLE pattern_classification TYPE datetime VALUE time::now();
        DEFINE INDEX idx_domain ON TABLE pattern_classification COLUMNS domain;
        DEFINE INDEX idx_confidence ON TABLE pattern_classification COLUMNS confidence;
        """,
        # Learned Patterns
        """
        DEFINE TABLE pattern_learned SCHEMAFULL;
        DEFINE FIELD pattern ON TABLE pattern_learned TYPE string;
        DEFINE FIELD pattern_type ON TABLE pattern_learned TYPE string ASSERT $value IN ["domain", "url_pattern", "path"];
        DEFINE FIELD classification ON TABLE pattern_learned TYPE string ASSERT $value IN ["content", "marketing"];
        DEFINE FIELD suggested_confidence ON TABLE pattern_learned TYPE float;
        DEFINE FIELD times_applied ON TABLE pattern_learned TYPE int DEFAULT 0;
        DEFINE FIELD correct_count ON TABLE pattern_learned TYPE int DEFAULT 0;
        DEFINE FIELD precision ON TABLE pattern_learned TYPE float DEFAULT 1.0;
        DEFINE FIELD status ON TABLE pattern_learned TYPE string DEFAULT "active" ASSERT $value IN ["active", "inactive", "pending_review"];
        DEFINE FIELD added_at ON TABLE pattern_learned TYPE datetime VALUE time::now();
        DEFINE FIELD last_used_at ON TABLE pattern_learned TYPE option<datetime>;
        DEFINE INDEX idx_pattern_unique ON TABLE pattern_learned COLUMNS pattern UNIQUE;
        """,
        # Pending Re-evaluation
        """
        DEFINE TABLE pattern_pending_reeval SCHEMAFULL;
        DEFINE FIELD url ON TABLE pattern_pending_reeval TYPE string;
        DEFINE FIELD domain ON TABLE pattern_pending_reeval TYPE string;
        DEFINE FIELD video_id ON TABLE pattern_pending_reeval TYPE string;
        DEFINE FIELD classification ON TABLE pattern_pending_reeval TYPE string;
        DEFINE FIELD confidence ON TABLE pattern_pending_reeval TYPE float;
        DEFINE FIELD domain_occurrence_count ON TABLE pattern_pending_reeval TYPE int DEFAULT 1;
        DEFINE FIELD first_seen ON TABLE pattern_pending_reeval TYPE datetime VALUE time::now();
        DEFINE FIELD last_seen ON TABLE pattern_pending_reeval TYPE datetime VALUE time::now();
        DEFINE FIELD reevaluated ON TABLE pattern_pending_reeval TYPE bool DEFAULT false;
        DEFINE INDEX idx_pending_domain ON TABLE pattern_pending_reeval COLUMNS domain;
        DEFINE INDEX idx_pending_reevaluated ON TABLE pattern_pending_reeval COLUMNS reevaluated;
        """,
    ]

    for query in queries:
        try:
            await execute_query(query.strip())
        except Exception as e:
            # Table/index may already exist
            logger.debug(f"Schema initialization note: {e}")


# =============================================================================
# Classification Operations
# =============================================================================


async def record_classification(
    url: str,
    video_id: str,
    domain: str,
    classification: str,
    confidence: float,
    method: str,
    reason: Optional[str] = None,
    pattern_suggested: Optional[str] = None,
) -> dict:
    """Record a URL classification.

    Args:
        url: Full URL
        video_id: YouTube video ID
        domain: Extracted domain
        classification: "content" or "marketing"
        confidence: Confidence score (0.0-1.0)
        method: "heuristic", "llm", or "learned_pattern"
        reason: Optional explanation
        pattern_suggested: Optional pattern to learn

    Returns:
        Query result with created record
    """
    query = """
    INSERT INTO pattern_classification {
        url: $url,
        video_id: $video_id,
        domain: $domain,
        classification: $classification,
        confidence: $confidence,
        method: $method,
        reason: $reason,
        pattern_suggested: $pattern_suggested
    };
    """

    params = {
        "url": url,
        "video_id": video_id,
        "domain": domain,
        "classification": classification,
        "confidence": confidence,
        "method": method,
        "reason": reason,
        "pattern_suggested": pattern_suggested,
    }

    result = await execute_query(query, params)
    return {"created": len(result) > 0}


async def get_low_confidence_classifications(threshold: float = 0.7) -> list[URLClassificationRecord]:
    """Get classifications below confidence threshold.

    Args:
        threshold: Confidence threshold (default 0.7)

    Returns:
        List of URLClassificationRecord instances
    """
    query = """
    SELECT * FROM pattern_classification
    WHERE confidence < $threshold
    ORDER BY confidence ASC;
    """

    results = await execute_query(query, {"threshold": threshold})

    records = []
    for r in results:
        records.append(URLClassificationRecord(
            id=r.get("id"),
            url=r.get("url"),
            domain=r.get("domain"),
            video_id=r.get("video_id"),
            classification=r.get("classification"),
            confidence=r.get("confidence"),
            method=r.get("method"),
            reason=r.get("reason"),
            pattern_suggested=r.get("pattern_suggested"),
            classified_at=_parse_datetime(r.get("classified_at")),
        ))

    return records


# =============================================================================
# Pending Re-evaluation Operations
# =============================================================================


async def add_or_update_pending_reevaluation(
    url: str,
    domain: str,
    video_id: str,
    classification: str,
    confidence: float,
) -> dict:
    """Add or update pending re-evaluation record.

    If domain already exists with reevaluated=false, increment occurrence count.
    Otherwise insert new record.

    Args:
        url: URL to track
        domain: Domain extracted from URL
        video_id: YouTube video ID
        classification: "content" or "marketing"
        confidence: Classification confidence (0.0-1.0)

    Returns:
        Dict with "created" or "updated" key
    """
    # Check if domain already has pending records
    check_query = """
    SELECT id, domain_occurrence_count
    FROM pattern_pending_reeval
    WHERE domain = $domain AND reevaluated = false
    LIMIT 1;
    """

    existing = await execute_query(check_query, {"domain": domain})

    if existing:
        # Update occurrence count and last_seen
        update_query = """
        UPDATE pattern_pending_reeval SET
            domain_occurrence_count = domain_occurrence_count + 1,
            last_seen = time::now()
        WHERE domain = $domain AND reevaluated = false;
        """

        result = await execute_query(update_query, {"domain": domain})
        return {"updated": len(result) > 0}
    else:
        # Insert new pending re-evaluation record
        insert_query = """
        INSERT INTO pattern_pending_reeval {
            url: $url,
            domain: $domain,
            video_id: $video_id,
            classification: $classification,
            confidence: $confidence,
            domain_occurrence_count: 1,
            first_seen: time::now(),
            last_seen: time::now(),
            reevaluated: false
        };
        """

        params = {
            "url": url,
            "domain": domain,
            "video_id": video_id,
            "classification": classification,
            "confidence": confidence,
        }

        result = await execute_query(insert_query, params)
        return {"created": len(result) > 0}


async def get_domains_for_batch_reeval(min_count: int = 3) -> list[DomainReevaluation]:
    """Get domains with min_count+ pending URLs for batch re-evaluation.

    Args:
        min_count: Minimum number of pending URLs required

    Returns:
        List of DomainReevaluation objects with aggregated data
    """
    # Find domains with min_count+ pending URLs
    domain_query = """
    SELECT domain, count() AS url_count
    FROM pattern_pending_reeval
    WHERE reevaluated = false
    GROUP BY domain
    ORDER BY url_count DESC;
    """

    domain_results = await execute_query(domain_query)

    # Filter domains with min_count+ URLs and fetch details
    results = []
    for domain_row in domain_results:
        domain = domain_row.get("domain")
        url_count = int(domain_row.get("url_count", 0))

        if url_count < min_count:
            continue

        # Get URLs and video IDs for this domain
        detail_query = """
        SELECT url, video_id, classification, confidence
        FROM pattern_pending_reeval
        WHERE domain = $domain AND reevaluated = false;
        """

        detail_results = await execute_query(detail_query, {"domain": domain})

        urls = []
        video_ids = []
        confidences = []
        classifications = {"content": 0, "marketing": 0}

        for row in detail_results:
            urls.append(row.get("url"))
            video_ids.append(row.get("video_id"))
            confidences.append(float(row.get("confidence", 0.0)))

            classification = row.get("classification")
            if classification in classifications:
                classifications[classification] += 1

        avg_confidence = sum(confidences) / len(confidences) if confidences else 0.0

        results.append(
            DomainReevaluation(
                domain=domain,
                url_count=url_count,
                urls=urls,
                video_ids=video_ids,
                avg_confidence=avg_confidence,
                classifications=classifications,
            )
        )

    return results


async def mark_reevaluated(url: str) -> dict:
    """Mark URL as re-evaluated.

    Sets reevaluated flag to true for the specified URL.

    Args:
        url: URL to mark as re-evaluated

    Returns:
        Dict with "updated" count
    """
    query = """
    UPDATE pattern_pending_reeval SET
        reevaluated = true
    WHERE url = $url;
    """

    result = await execute_query(query, {"url": url})
    return {"updated": len(result) > 0}


# =============================================================================
# Pattern Operations
# =============================================================================


async def add_learned_pattern(
    pattern: str,
    pattern_type: str,
    classification: str,
    suggested_confidence: float,
) -> dict:
    """Add a learned pattern (handles unique constraint).

    Args:
        pattern: Pattern string (e.g., "github.com", "/docs/")
        pattern_type: "domain", "url_pattern", or "path"
        classification: "content" or "marketing"
        suggested_confidence: Confidence score for matches (0.0-1.0)

    Returns:
        Query result with created status
    """
    query = """
    INSERT INTO pattern_learned {
        pattern: $pattern,
        pattern_type: $pattern_type,
        classification: $classification,
        suggested_confidence: $suggested_confidence,
        times_applied: 0,
        correct_count: 0,
        precision: 1.0,
        status: "active"
    };
    """

    params = {
        "pattern": pattern,
        "pattern_type": pattern_type,
        "classification": classification,
        "suggested_confidence": suggested_confidence,
    }

    try:
        result = await execute_query(query, params)
        return {"created": len(result) > 0}
    except Exception as e:
        # Unique constraint violation - pattern already exists, skip
        if "already exists" in str(e).lower() or "unique" in str(e).lower():
            logger.debug(f"Pattern {pattern} already exists, skipping")
            return {"created": False, "exists": True}
        raise


async def get_active_patterns() -> list[LearnedPatternRecord]:
    """Get all active learned patterns.

    Returns:
        List of LearnedPatternRecord instances with status='active'
    """
    query = """
    SELECT * FROM pattern_learned
    WHERE status = "active";
    """

    results = await execute_query(query)

    records = []
    for r in results:
        records.append(LearnedPatternRecord(
            id=r.get("id"),
            pattern=r.get("pattern"),
            pattern_type=r.get("pattern_type"),
            classification=r.get("classification"),
            suggested_confidence=r.get("suggested_confidence"),
            times_applied=r.get("times_applied", 0),
            correct_count=r.get("correct_count", 0),
            precision=r.get("precision", 1.0),
            status=r.get("status", "active"),
            added_at=_parse_datetime(r.get("added_at")),
            last_used_at=_parse_datetime_optional(r.get("last_used_at")),
        ))

    return records


async def get_pattern_stats(pattern: str) -> Optional[PatternStats]:
    """Get stats for a specific pattern.

    Args:
        pattern: Pattern string to query

    Returns:
        PatternStats instance if found, None otherwise
    """
    query = """
    SELECT * FROM pattern_learned
    WHERE pattern = $pattern
    LIMIT 1;
    """

    results = await execute_query(query, {"pattern": pattern})

    if not results:
        return None

    r = results[0]
    return PatternStats(
        pattern=r.get("pattern"),
        pattern_type=r.get("pattern_type"),
        classification=r.get("classification"),
        times_applied=r.get("times_applied", 0),
        correct_count=r.get("correct_count", 0),
        precision=r.get("precision", 1.0),
        status=r.get("status", "active"),
        added_at=_parse_datetime(r.get("added_at")),
        last_used_at=_parse_datetime_optional(r.get("last_used_at")),
    )


async def update_pattern_usage(pattern: str) -> dict:
    """Increment times_applied and update last_used_at.

    Args:
        pattern: Pattern string to update

    Returns:
        Query result with updated status
    """
    query = """
    UPDATE pattern_learned SET
        times_applied += 1,
        last_used_at = time::now()
    WHERE pattern = $pattern;
    """

    result = await execute_query(query, {"pattern": pattern})
    return {"updated": len(result) > 0}


async def update_pattern_precision(pattern: str, correct: bool) -> dict:
    """Update precision after verification.

    Increments correct_count if correct=True, recalculates precision,
    and marks pattern as inactive if precision falls below threshold.

    Args:
        pattern: Pattern string to update
        correct: True if pattern was correctly applied

    Returns:
        Query result with updated status
    """
    # First, get current stats
    stats = await get_pattern_stats(pattern)
    if not stats:
        return {"updated": False, "error": "Pattern not found"}

    # Calculate new values
    new_correct_count = stats.correct_count + (1 if correct else 0)
    new_precision = new_correct_count / stats.times_applied if stats.times_applied > 0 else 1.0

    # Update query with conditional status change
    # Pattern precision threshold is typically 0.7-0.8
    precision_threshold = 0.7

    query = """
    UPDATE pattern_learned SET
        correct_count = $correct_count,
        precision = $precision,
        status = IF($precision < $threshold, "inactive", status)
    WHERE pattern = $pattern;
    """

    params = {
        "pattern": pattern,
        "correct_count": new_correct_count,
        "precision": new_precision,
        "threshold": precision_threshold,
    }

    result = await execute_query(query, params)
    return {
        "updated": len(result) > 0,
        "precision": new_precision,
        "status": "inactive" if new_precision < precision_threshold else stats.status,
    }


async def get_pattern_effectiveness_report() -> dict:
    """Get aggregated pattern statistics.

    Returns:
        Dict with:
        - total_patterns: Total count
        - active_patterns: Active count
        - inactive_patterns: Inactive count
        - top_patterns: Top 10 by usage
        - low_performing_patterns: Patterns with precision < threshold
        - pending_reevaluation_count: Count of pending re-evaluations
    """
    # Total patterns
    total_query = "SELECT COUNT() AS count FROM pattern_learned GROUP ALL;"
    total_result = await execute_query(total_query)
    total_patterns = int(total_result[0].get("count", 0)) if total_result else 0

    # Active patterns
    active_query = 'SELECT COUNT() AS count FROM pattern_learned WHERE status = "active" GROUP ALL;'
    active_result = await execute_query(active_query)
    active_patterns = int(active_result[0].get("count", 0)) if active_result else 0

    # Inactive patterns
    inactive_query = 'SELECT COUNT() AS count FROM pattern_learned WHERE status = "inactive" GROUP ALL;'
    inactive_result = await execute_query(inactive_query)
    inactive_patterns = int(inactive_result[0].get("count", 0)) if inactive_result else 0

    # Top patterns (by times_applied)
    top_query = """
    SELECT * FROM pattern_learned
    WHERE status = "active"
    ORDER BY times_applied DESC
    LIMIT 10;
    """
    top_results = await execute_query(top_query)
    top_patterns = []
    for r in top_results:
        top_patterns.append(PatternStats(
            pattern=r.get("pattern"),
            pattern_type=r.get("pattern_type"),
            classification=r.get("classification"),
            times_applied=r.get("times_applied", 0),
            correct_count=r.get("correct_count", 0),
            precision=r.get("precision", 1.0),
            status=r.get("status", "active"),
            added_at=_parse_datetime(r.get("added_at")),
            last_used_at=_parse_datetime_optional(r.get("last_used_at")),
        ))

    # Low-performing patterns (precision < threshold, times_applied > 5)
    precision_threshold = 0.7
    low_query = """
    SELECT * FROM pattern_learned
    WHERE precision < $threshold AND times_applied > 5
    ORDER BY precision ASC;
    """
    low_results = await execute_query(low_query, {"threshold": precision_threshold})
    low_performing_patterns = []
    for r in low_results:
        low_performing_patterns.append(PatternStats(
            pattern=r.get("pattern"),
            pattern_type=r.get("pattern_type"),
            classification=r.get("classification"),
            times_applied=r.get("times_applied", 0),
            correct_count=r.get("correct_count", 0),
            precision=r.get("precision", 1.0),
            status=r.get("status", "active"),
            added_at=_parse_datetime(r.get("added_at")),
            last_used_at=_parse_datetime_optional(r.get("last_used_at")),
        ))

    # Pending re-evaluation count
    pending_query = "SELECT COUNT() AS count FROM pattern_pending_reeval WHERE reevaluated = false GROUP ALL;"
    pending_result = await execute_query(pending_query)
    pending_reevaluation_count = int(pending_result[0].get("count", 0)) if pending_result else 0

    return {
        "total_patterns": total_patterns,
        "active_patterns": active_patterns,
        "inactive_patterns": inactive_patterns,
        "top_patterns": top_patterns,
        "low_performing_patterns": low_performing_patterns,
        "pending_reevaluation_count": pending_reevaluation_count,
    }
