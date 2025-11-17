"""SQLite-based pattern tracker for URL analytics."""

import sqlite3
import re
from pathlib import Path
from datetime import datetime
from typing import Optional
from urllib.parse import urlparse

from .config import AnalyticsConfig
from .models import PatternStats, DomainReevaluation


class SQLitePatternTracker:
    """SQLite implementation of PatternTracker protocol.

    Tracks URL classifications, learns patterns, and manages re-evaluation
    of low-confidence URLs using a SQLite database.

    Example:
        >>> tracker = SQLitePatternTracker()
        >>> tracker.record_classification(
        ...     url="https://github.com/user/repo",
        ...     video_id="abc123",
        ...     classification="content",
        ...     confidence=0.95,
        ...     method="llm"
        ... )
    """

    def __init__(self, config: Optional[AnalyticsConfig] = None):
        """Initialize pattern tracker.

        Args:
            config: Analytics configuration (uses defaults if not provided)
        """
        if config is None:
            from .config import get_default_config
            config = get_default_config()

        self.config = config
        self.db_path = config.db_path

        # Ensure database directory exists
        self.db_path.parent.mkdir(parents=True, exist_ok=True)

        # Initialize database
        self._init_db()

    def _init_db(self) -> None:
        """Initialize SQLite database with required tables."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        # URL classifications table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS url_classifications (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                url TEXT NOT NULL,
                domain TEXT NOT NULL,
                video_id TEXT NOT NULL,
                classification TEXT NOT NULL CHECK (classification IN ('content', 'marketing')),
                confidence REAL NOT NULL CHECK (confidence >= 0.0 AND confidence <= 1.0),
                method TEXT NOT NULL CHECK (method IN ('heuristic', 'llm', 'learned_pattern')),
                reason TEXT,
                pattern_suggested TEXT,
                classified_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_domain ON url_classifications (domain)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_confidence ON url_classifications (confidence)")

        # Learned patterns table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS learned_patterns (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                pattern TEXT UNIQUE NOT NULL,
                pattern_type TEXT NOT NULL CHECK (pattern_type IN ('domain', 'url_pattern', 'path')),
                classification TEXT NOT NULL CHECK (classification IN ('content', 'marketing')),
                suggested_confidence REAL NOT NULL CHECK (suggested_confidence >= 0.0 AND suggested_confidence <= 1.0),
                times_applied INTEGER DEFAULT 0,
                correct_count INTEGER DEFAULT 0,
                precision REAL DEFAULT 1.0 CHECK (precision >= 0.0 AND precision <= 1.0),
                status TEXT DEFAULT 'active' CHECK (status IN ('active', 'inactive', 'pending_review')),
                added_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                last_used_at TIMESTAMP
            )
        """)

        # Pending re-evaluation table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS pending_reevaluation (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                url TEXT NOT NULL,
                domain TEXT NOT NULL,
                video_id TEXT NOT NULL,
                classification TEXT NOT NULL CHECK (classification IN ('content', 'marketing')),
                confidence REAL NOT NULL CHECK (confidence >= 0.0 AND confidence <= 1.0),
                domain_occurrence_count INTEGER DEFAULT 1,
                first_seen TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                last_seen TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                reevaluated BOOLEAN DEFAULT 0
            )
        """)
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_pending_domain ON pending_reevaluation (domain)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_pending_reevaluated ON pending_reevaluation (reevaluated)")

        conn.commit()
        conn.close()

    @staticmethod
    def _extract_domain(url: str) -> str:
        """Extract domain from URL.

        Args:
            url: Full URL

        Returns:
            Domain (e.g., "github.com")
        """
        parsed = urlparse(url)
        return parsed.netloc

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
        """Record a URL classification."""
        domain = self._extract_domain(url)

        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute(
            """
            INSERT INTO url_classifications
            (url, domain, video_id, classification, confidence, method, reason, pattern_suggested)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (url, domain, video_id, classification, confidence, method, reason, pattern_suggested),
        )

        # If low confidence, add to pending re-evaluation
        if confidence < self.config.low_confidence_threshold:
            # Check if domain already in pending re-evaluation
            cursor.execute(
                "SELECT domain_occurrence_count FROM pending_reevaluation WHERE domain = ? AND reevaluated = 0",
                (domain,),
            )
            existing = cursor.fetchone()

            if existing:
                # Update occurrence count and last_seen
                cursor.execute(
                    """
                    UPDATE pending_reevaluation
                    SET domain_occurrence_count = domain_occurrence_count + 1,
                        last_seen = CURRENT_TIMESTAMP
                    WHERE domain = ? AND reevaluated = 0
                    """,
                    (domain,),
                )
            else:
                # Insert new pending re-evaluation record
                cursor.execute(
                    """
                    INSERT INTO pending_reevaluation
                    (url, domain, video_id, classification, confidence)
                    VALUES (?, ?, ?, ?, ?)
                    """,
                    (url, domain, video_id, classification, confidence),
                )

        conn.commit()
        conn.close()

    def add_learned_pattern(
        self,
        pattern: str,
        pattern_type: str,
        classification: str,
        confidence: float,
    ) -> None:
        """Add a learned pattern to the database."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        try:
            cursor.execute(
                """
                INSERT INTO learned_patterns
                (pattern, pattern_type, classification, suggested_confidence)
                VALUES (?, ?, ?, ?)
                """,
                (pattern, pattern_type, classification, confidence),
            )
            conn.commit()
        except sqlite3.IntegrityError:
            # Pattern already exists, skip
            pass
        finally:
            conn.close()

    def check_learned_patterns(
        self, url: str
    ) -> Optional[tuple[str, str, float]]:
        """Check if URL matches any active learned patterns."""
        if not self.config.use_learned_patterns:
            return None

        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        # Get all active patterns
        cursor.execute(
            "SELECT pattern, pattern_type, classification, suggested_confidence FROM learned_patterns WHERE status = 'active'"
        )
        patterns = cursor.fetchall()

        for pattern, pattern_type, classification, confidence in patterns:
            if self._url_matches_pattern(url, pattern, pattern_type):
                # Update usage stats
                cursor.execute(
                    """
                    UPDATE learned_patterns
                    SET times_applied = times_applied + 1,
                        last_used_at = CURRENT_TIMESTAMP
                    WHERE pattern = ?
                    """,
                    (pattern,),
                )
                conn.commit()
                conn.close()

                reason = f"Matched learned pattern: {pattern} ({pattern_type})"
                return (classification, reason, confidence)

        conn.close()
        return None

    @staticmethod
    def _url_matches_pattern(url: str, pattern: str, pattern_type: str) -> bool:
        """Check if URL matches a pattern.

        Args:
            url: URL to check
            pattern: Pattern to match
            pattern_type: 'domain', 'url_pattern', or 'path'

        Returns:
            True if match, False otherwise
        """
        url_lower = url.lower()
        pattern_lower = pattern.lower()

        if pattern_type == "domain":
            # Match domain
            parsed = urlparse(url)
            return pattern_lower in parsed.netloc.lower()

        elif pattern_type == "url_pattern":
            # Match as substring or regex
            return pattern_lower in url_lower

        elif pattern_type == "path":
            # Match path component
            parsed = urlparse(url)
            return pattern_lower in parsed.path.lower()

        return False

    def get_pattern_stats(self, pattern: str) -> Optional[PatternStats]:
        """Get statistics for a specific pattern."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute(
            """
            SELECT pattern, pattern_type, classification, times_applied, correct_count,
                   precision, status, added_at, last_used_at
            FROM learned_patterns
            WHERE pattern = ?
            """,
            (pattern,),
        )

        row = cursor.fetchone()
        conn.close()

        if not row:
            return None

        return PatternStats(
            pattern=row[0],
            pattern_type=row[1],
            classification=row[2],
            times_applied=row[3],
            correct_count=row[4],
            precision=row[5],
            status=row[6],
            added_at=datetime.fromisoformat(row[7]) if row[7] else datetime.now(),
            last_used_at=datetime.fromisoformat(row[8]) if row[8] else None,
        )

    def get_low_confidence_urls(
        self, threshold: float = 0.7
    ) -> list[dict]:
        """Get all URLs classified with confidence below threshold."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute(
            """
            SELECT url, video_id, classification, confidence, reason
            FROM url_classifications
            WHERE confidence < ?
            ORDER BY confidence ASC
            """,
            (threshold,),
        )

        results = []
        for row in cursor.fetchall():
            results.append({
                "url": row[0],
                "video_id": row[1],
                "classification": row[2],
                "confidence": row[3],
                "reason": row[4],
            })

        conn.close()
        return results

    def get_domains_for_batch_reeval(
        self, min_count: int = 3
    ) -> list[DomainReevaluation]:
        """Get domains that have min_count+ low-confidence URLs for batch re-evaluation."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        # Find domains with min_count+ pending URLs
        cursor.execute(
            """
            SELECT domain, COUNT(*) as url_count
            FROM pending_reevaluation
            WHERE reevaluated = 0
            GROUP BY domain
            HAVING url_count >= ?
            ORDER BY url_count DESC
            """,
            (min_count,),
        )

        results = []
        for domain, url_count in cursor.fetchall():
            # Get URLs and video IDs for this domain
            cursor.execute(
                """
                SELECT url, video_id, classification, confidence
                FROM pending_reevaluation
                WHERE domain = ? AND reevaluated = 0
                """,
                (domain,),
            )

            urls = []
            video_ids = []
            confidences = []
            classifications = {"content": 0, "marketing": 0}

            for url, video_id, classification, confidence in cursor.fetchall():
                urls.append(url)
                video_ids.append(video_id)
                confidences.append(confidence)
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

        conn.close()
        return results

    def mark_reevaluated(
        self,
        url: str,
        new_classification: str,
        new_confidence: float,
    ) -> None:
        """Mark a URL as re-evaluated with new classification."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute(
            """
            UPDATE pending_reevaluation
            SET reevaluated = 1
            WHERE url = ?
            """,
            (url,),
        )

        conn.commit()
        conn.close()

    def get_pattern_effectiveness_report(self) -> dict:
        """Get report on pattern effectiveness."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        # Total patterns
        cursor.execute("SELECT COUNT(*) FROM learned_patterns")
        total_patterns = cursor.fetchone()[0]

        # Active patterns
        cursor.execute("SELECT COUNT(*) FROM learned_patterns WHERE status = 'active'")
        active_patterns = cursor.fetchone()[0]

        # Inactive patterns
        cursor.execute("SELECT COUNT(*) FROM learned_patterns WHERE status = 'inactive'")
        inactive_patterns = cursor.fetchone()[0]

        # Top patterns (by times_applied)
        cursor.execute(
            """
            SELECT pattern, pattern_type, classification, times_applied, correct_count,
                   precision, status, added_at, last_used_at
            FROM learned_patterns
            WHERE status = 'active'
            ORDER BY times_applied DESC
            LIMIT 10
            """
        )
        top_patterns = [
            PatternStats(
                pattern=row[0],
                pattern_type=row[1],
                classification=row[2],
                times_applied=row[3],
                correct_count=row[4],
                precision=row[5],
                status=row[6],
                added_at=datetime.fromisoformat(row[7]) if row[7] else datetime.now(),
                last_used_at=datetime.fromisoformat(row[8]) if row[8] else None,
            )
            for row in cursor.fetchall()
        ]

        # Low-performing patterns
        cursor.execute(
            """
            SELECT pattern, pattern_type, classification, times_applied, correct_count,
                   precision, status, added_at, last_used_at
            FROM learned_patterns
            WHERE precision < ? AND times_applied > 5
            ORDER BY precision ASC
            """,
            (self.config.pattern_precision_threshold,),
        )
        low_performing_patterns = [
            PatternStats(
                pattern=row[0],
                pattern_type=row[1],
                classification=row[2],
                times_applied=row[3],
                correct_count=row[4],
                precision=row[5],
                status=row[6],
                added_at=datetime.fromisoformat(row[7]) if row[7] else datetime.now(),
                last_used_at=datetime.fromisoformat(row[8]) if row[8] else None,
            )
            for row in cursor.fetchall()
        ]

        # Pending re-evaluation count
        cursor.execute("SELECT COUNT(*) FROM pending_reevaluation WHERE reevaluated = 0")
        pending_reevaluation_count = cursor.fetchone()[0]

        conn.close()

        return {
            "total_patterns": total_patterns,
            "active_patterns": active_patterns,
            "inactive_patterns": inactive_patterns,
            "top_patterns": top_patterns,
            "low_performing_patterns": low_performing_patterns,
            "pending_reevaluation_count": pending_reevaluation_count,
        }

    def update_pattern_stats(
        self,
        pattern: str,
        correct: bool,
    ) -> None:
        """Update pattern statistics after verification."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        if correct:
            cursor.execute(
                """
                UPDATE learned_patterns
                SET correct_count = correct_count + 1,
                    precision = CAST(correct_count + 1 AS REAL) / CAST(times_applied AS REAL)
                WHERE pattern = ?
                """,
                (pattern,),
            )
        else:
            cursor.execute(
                """
                UPDATE learned_patterns
                SET precision = CAST(correct_count AS REAL) / CAST(times_applied AS REAL)
                WHERE pattern = ?
                """,
                (pattern,),
            )

        # Check if precision dropped below threshold
        cursor.execute(
            "SELECT precision FROM learned_patterns WHERE pattern = ?",
            (pattern,),
        )
        row = cursor.fetchone()
        if row and row[0] < self.config.pattern_precision_threshold:
            cursor.execute(
                "UPDATE learned_patterns SET status = 'inactive' WHERE pattern = ?",
                (pattern,),
            )

        conn.commit()
        conn.close()

    def close(self) -> None:
        """Close database connection.

        Note: SQLite connections are created per-operation, so this is a no-op.
        Included for protocol compliance.
        """
        pass
