"""Migrate URL pattern analytics data from SQLite to SurrealDB.

This script performs a one-time migration of:
- url_classifications table (~4,500 records)
- learned_patterns table (~106 records)
- pending_reevaluation table

Usage:
    python compose/cli/migrate_url_patterns.py [--dry-run] [--batch-size 100]

Arguments:
    --dry-run: Read SQLite data and show stats, but don't write to SurrealDB
    --batch-size: Number of records to insert per batch (default: 100)

Example:
    # Preview migration
    python compose/cli/migrate_url_patterns.py --dry-run

    # Run migration with custom batch size
    python compose/cli/migrate_url_patterns.py --batch-size 50

    # Run full migration
    python compose/cli/migrate_url_patterns.py
"""

import asyncio
import sqlite3
import argparse
from pathlib import Path
from datetime import datetime
from typing import Any

from compose.cli.base import setup_script_environment

# Setup environment and imports
setup_script_environment(load_env=True)

from compose.services.analytics import repository
from compose.services.analytics.config import get_default_config


def chunk_list(items: list[Any], chunk_size: int) -> list[list[Any]]:
    """Split list into chunks of specified size."""
    return [items[i:i + chunk_size] for i in range(0, len(items), chunk_size)]


async def migrate_classifications(
    db_path: Path,
    dry_run: bool = False,
    batch_size: int = 100
) -> tuple[int, int]:
    """Migrate url_classifications table from SQLite to SurrealDB.

    Args:
        db_path: Path to SQLite database
        dry_run: If True, read data but don't write to SurrealDB
        batch_size: Number of records to insert per batch

    Returns:
        Tuple of (sqlite_count, surrealdb_count)
    """
    print("=" * 60)
    print("Migrating URL Classifications")
    print("=" * 60)

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # Read all classifications from SQLite
    cursor.execute("""
        SELECT url, domain, video_id, classification, confidence, method, reason, pattern_suggested, classified_at
        FROM url_classifications
        ORDER BY id
    """)

    rows = cursor.fetchall()
    sqlite_count = len(rows)
    print(f"📊 Found {sqlite_count} classifications in SQLite")

    conn.close()

    if dry_run:
        print("🔍 DRY RUN: Skipping SurrealDB writes")
        return (sqlite_count, 0)

    # Convert to batches
    batches = chunk_list(rows, batch_size)
    surrealdb_count = 0

    print(f"📦 Processing {len(batches)} batches of {batch_size} records each...")

    for batch_idx, batch in enumerate(batches, 1):
        print(f"  Batch {batch_idx}/{len(batches)}: {len(batch)} records...", end=" ", flush=True)

        for row in batch:
            url, domain, video_id, classification, confidence, method, reason, pattern_suggested, classified_at = row

            # Convert SQLite timestamp to datetime
            if classified_at:
                # SQLite stores as ISO string
                classified_dt = datetime.fromisoformat(classified_at.replace(' ', 'T'))
            else:
                classified_dt = datetime.now()

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
            surrealdb_count += 1

        print("✓")

    print(f"✅ Migrated {surrealdb_count} classifications to SurrealDB")
    return (sqlite_count, surrealdb_count)


async def migrate_patterns(
    db_path: Path,
    dry_run: bool = False,
    batch_size: int = 100
) -> tuple[int, int]:
    """Migrate learned_patterns table from SQLite to SurrealDB.

    Args:
        db_path: Path to SQLite database
        dry_run: If True, read data but don't write to SurrealDB
        batch_size: Number of records to insert per batch

    Returns:
        Tuple of (sqlite_count, surrealdb_count)
    """
    print("\n" + "=" * 60)
    print("Migrating Learned Patterns")
    print("=" * 60)

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # Read all patterns from SQLite
    cursor.execute("""
        SELECT pattern, pattern_type, classification, suggested_confidence, times_applied,
               correct_count, precision, status, added_at, last_used_at
        FROM learned_patterns
        ORDER BY id
    """)

    rows = cursor.fetchall()
    sqlite_count = len(rows)
    print(f"📊 Found {sqlite_count} learned patterns in SQLite")

    conn.close()

    if dry_run:
        print("🔍 DRY RUN: Skipping SurrealDB writes")
        return (sqlite_count, 0)

    # Convert to batches
    batches = chunk_list(rows, batch_size)
    surrealdb_count = 0

    print(f"📦 Processing {len(batches)} batches of {batch_size} records each...")

    for batch_idx, batch in enumerate(batches, 1):
        print(f"  Batch {batch_idx}/{len(batches)}: {len(batch)} records...", end=" ", flush=True)

        for row in batch:
            pattern, pattern_type, classification, suggested_confidence, times_applied, correct_count, precision, status, added_at, last_used_at = row

            await repository.add_learned_pattern(
                pattern=pattern,
                pattern_type=pattern_type,
                classification=classification,
                suggested_confidence=suggested_confidence,
            )

            # Update stats if pattern has been used
            if times_applied > 0:
                # Update times_applied and precision
                await repository.update_pattern_usage(pattern)

                # Update correct_count by calling update_pattern_precision
                for _ in range(correct_count):
                    await repository.update_pattern_precision(pattern, correct=True)

                # Update incorrect_count
                incorrect_count = times_applied - correct_count
                for _ in range(incorrect_count):
                    await repository.update_pattern_precision(pattern, correct=False)

            surrealdb_count += 1

        print("✓")

    print(f"✅ Migrated {surrealdb_count} learned patterns to SurrealDB")
    return (sqlite_count, surrealdb_count)


async def migrate_pending_reevaluation(
    db_path: Path,
    dry_run: bool = False,
    batch_size: int = 100
) -> tuple[int, int]:
    """Migrate pending_reevaluation table from SQLite to SurrealDB.

    Args:
        db_path: Path to SQLite database
        dry_run: If True, read data but don't write to SurrealDB
        batch_size: Number of records to insert per batch

    Returns:
        Tuple of (sqlite_count, surrealdb_count)
    """
    print("\n" + "=" * 60)
    print("Migrating Pending Re-evaluations")
    print("=" * 60)

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # Read all pending re-evaluations from SQLite
    cursor.execute("""
        SELECT url, domain, video_id, classification, confidence, domain_occurrence_count,
               first_seen, last_seen, reevaluated
        FROM pending_reevaluation
        ORDER BY id
    """)

    rows = cursor.fetchall()
    sqlite_count = len(rows)
    print(f"📊 Found {sqlite_count} pending re-evaluations in SQLite")

    conn.close()

    if dry_run:
        print("🔍 DRY RUN: Skipping SurrealDB writes")
        return (sqlite_count, 0)

    # Convert to batches
    batches = chunk_list(rows, batch_size)
    surrealdb_count = 0

    print(f"📦 Processing {len(batches)} batches of {batch_size} records each...")

    for batch_idx, batch in enumerate(batches, 1):
        print(f"  Batch {batch_idx}/{len(batches)}: {len(batch)} records...", end=" ", flush=True)

        for row in batch:
            url, domain, video_id, classification, confidence, domain_occurrence_count, first_seen, last_seen, reevaluated = row

            await repository.add_or_update_pending_reevaluation(
                url=url,
                domain=domain,
                video_id=video_id,
                classification=classification,
                confidence=confidence,
            )

            # If reevaluated, mark as such
            if reevaluated:
                await repository.mark_reevaluated(url)

            surrealdb_count += 1

        print("✓")

    print(f"✅ Migrated {surrealdb_count} pending re-evaluations to SurrealDB")
    return (sqlite_count, surrealdb_count)


async def verify_migration(
    classification_counts: tuple[int, int],
    pattern_counts: tuple[int, int],
    pending_counts: tuple[int, int]
) -> bool:
    """Verify migration was successful by comparing counts.

    Args:
        classification_counts: (sqlite_count, surrealdb_count) for classifications
        pattern_counts: (sqlite_count, surrealdb_count) for patterns
        pending_counts: (sqlite_count, surrealdb_count) for pending re-evaluations

    Returns:
        True if all counts match, False otherwise
    """
    print("\n" + "=" * 60)
    print("Verification Summary")
    print("=" * 60)

    all_match = True

    # Classifications
    sqlite_class, surrealdb_class = classification_counts
    class_match = sqlite_class == surrealdb_class
    symbol = "✅" if class_match else "❌"
    print(f"{symbol} Classifications: SQLite={sqlite_class}, SurrealDB={surrealdb_class}")
    all_match = all_match and class_match

    # Patterns
    sqlite_pat, surrealdb_pat = pattern_counts
    pat_match = sqlite_pat == surrealdb_pat
    symbol = "✅" if pat_match else "❌"
    print(f"{symbol} Patterns: SQLite={sqlite_pat}, SurrealDB={surrealdb_pat}")
    all_match = all_match and pat_match

    # Pending re-evaluations
    sqlite_pend, surrealdb_pend = pending_counts
    pend_match = sqlite_pend == surrealdb_pend
    symbol = "✅" if pend_match else "❌"
    print(f"{symbol} Pending Re-evals: SQLite={sqlite_pend}, SurrealDB={surrealdb_pend}")
    all_match = all_match and pend_match

    print("=" * 60)

    if all_match:
        print("🎉 Migration completed successfully! All counts match.")
    else:
        print("⚠️ Migration completed with count mismatches. Review logs.")

    return all_match


async def main():
    """Main migration function."""
    parser = argparse.ArgumentParser(
        description="Migrate URL pattern analytics data from SQLite to SurrealDB"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Read SQLite data and show stats, but don't write to SurrealDB"
    )
    parser.add_argument(
        "--batch-size",
        type=int,
        default=100,
        help="Number of records to insert per batch (default: 100)"
    )
    args = parser.parse_args()

    # Get database path from config
    config = get_default_config()
    db_path = config.db_path

    if not db_path.exists():
        print(f"❌ SQLite database not found at {db_path}")
        print("   Please ensure the database exists before running migration.")
        return

    print("\n" + "=" * 60)
    print("URL Pattern Analytics Migration")
    print("=" * 60)
    print(f"Source: SQLite ({db_path})")
    print(f"Target: SurrealDB")
    print(f"Mode: {'DRY RUN' if args.dry_run else 'LIVE MIGRATION'}")
    print(f"Batch size: {args.batch_size}")
    print("=" * 60)

    if not args.dry_run:
        # Initialize SurrealDB schema
        print("\n🔧 Initializing SurrealDB schema...")
        await repository.init_analytics_schema()
        print("✅ Schema initialized")

    # Migrate each table
    classification_counts = await migrate_classifications(db_path, args.dry_run, args.batch_size)
    pattern_counts = await migrate_patterns(db_path, args.dry_run, args.batch_size)
    pending_counts = await migrate_pending_reevaluation(db_path, args.dry_run, args.batch_size)

    # Verify migration
    if not args.dry_run:
        await verify_migration(classification_counts, pattern_counts, pending_counts)
    else:
        print("\n🔍 DRY RUN complete. No data was written to SurrealDB.")
        print(f"   Run without --dry-run to perform actual migration.")


if __name__ == "__main__":
    asyncio.run(main())
