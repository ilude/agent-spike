#!/usr/bin/env python
"""Display URL pattern learning status and statistics.

This script shows the current state of the self-improving URL filter system:
- Learned patterns and their effectiveness
- Pending re-evaluation count
- Top-performing patterns
- Low-performing patterns (precision < 0.7)

Usage:
    # Show current status
    uv run python tools/scripts/url_filter_status.py

    # Show detailed pattern breakdown
    uv run python tools/scripts/url_filter_status.py --detailed

    # Show quick summary only
    uv run python tools/scripts/url_filter_status.py --summary
"""

import sys
import json
from pathlib import Path
from datetime import datetime

# Setup script environment
sys.path.insert(0, str(Path(__file__).parent))
from compose.cli.base import setup_script_environment
setup_script_environment()

from compose.services.analytics import create_pattern_tracker


# Progress tracking
PROGRESS_FILE = Path("projects/data/archive/.url_filter_progress.json")


def get_batch_progress() -> dict:
    """Get current batch processing progress.

    Returns:
        Dict with progress info, or None if no batch is running
    """
    if not PROGRESS_FILE.exists():
        return None

    try:
        progress_data = json.loads(PROGRESS_FILE.read_text())

        # Calculate elapsed time
        if progress_data.get("started_at"):
            started = datetime.fromisoformat(progress_data["started_at"])
            elapsed = datetime.now() - started
            progress_data["elapsed_seconds"] = int(elapsed.total_seconds())

            # Estimate remaining time
            if progress_data.get("processed", 0) > 0:
                avg_per_video = elapsed.total_seconds() / progress_data["processed"]
                remaining = progress_data["total_archives"] - progress_data["processed"]
                progress_data["estimated_remaining_seconds"] = int(avg_per_video * remaining)

        return progress_data
    except Exception:
        return None


def show_batch_progress(progress: dict) -> None:
    """Display batch processing progress.

    Args:
        progress: Progress data from get_batch_progress()
    """
    if not progress:
        return

    status = progress.get("status", "unknown")
    total = progress.get("total_archives", 0)
    processed = progress.get("processed", 0)
    errors = progress.get("errors", 0)
    current_video = progress.get("current_video_id", "")

    print(f"{'='*70}")
    print(f"Batch Processing Status")
    print(f"{'='*70}\n")

    if status == "running":
        percentage = processed/total*100 if total > 0 else 0
        print(f"{processed}/{total} ({percentage:.1f}%)  IN PROGRESS")
        print(f"Current video: {current_video}")
        print(f"Errors: {errors}")

        # Show time estimates
        if "elapsed_seconds" in progress:
            elapsed_mins = progress["elapsed_seconds"] // 60
            print(f"\nElapsed time: {elapsed_mins} minutes")

            if "estimated_remaining_seconds" in progress:
                remaining_mins = progress["estimated_remaining_seconds"] // 60
                print(f"Estimated remaining: {remaining_mins} minutes")

        # Show progress bar
        bar_width = 50
        filled = int(bar_width * processed / total) if total > 0 else 0
        bar = "[" + "=" * filled + ">" + " " * (bar_width - filled - 1) + "]"
        print(f"\n{bar}")

    elif status == "completed":
        percentage = processed/total*100 if total > 0 else 0
        print(f"{processed}/{total} ({percentage:.1f}%)  COMPLETED")
        print(f"Errors: {errors}")

        if "elapsed_seconds" in progress:
            elapsed_mins = progress["elapsed_seconds"] // 60
            print(f"Total time: {elapsed_mins} minutes")

    print(f"\n{'='*70}\n")


def show_summary(report: dict) -> None:
    """Show quick summary of pattern learning status.

    Args:
        report: Pattern effectiveness report from PatternTracker
    """
    print(f"URL Filter Pattern Learning - Quick Status\n")

    print(f"Patterns learned: {report['total_patterns']}")
    print(f"  - Active: {report['active_patterns']}")
    print(f"  - Inactive (low precision): {report['inactive_patterns']}")
    print(f"\nURLs pending re-evaluation: {report['pending_reevaluation_count']}")

    if report['top_patterns']:
        top_pattern = report['top_patterns'][0]
        print(f"\nMost used pattern:")
        print(f"  {top_pattern.pattern} ({top_pattern.pattern_type})")
        print(f"  Precision: {top_pattern.precision:.2%} | Used: {top_pattern.times_applied} times")

    print()


def show_detailed(report: dict) -> None:
    """Show detailed pattern statistics and effectiveness.

    Args:
        report: Pattern effectiveness report from PatternTracker
    """
    print(f"{'='*70}")
    print(f"URL Filter Pattern Learning - Detailed Status")
    print(f"{'='*70}\n")

    # Overview
    print(f"Overview:")
    print(f"  Total learned patterns: {report['total_patterns']}")
    print(f"  Active patterns: {report['active_patterns']}")
    print(f"  Inactive patterns: {report['inactive_patterns']}")
    print(f"  Pending re-evaluation: {report['pending_reevaluation_count']} URLs\n")

    # Top patterns
    if report['top_patterns']:
        print(f"Top Patterns (by usage):")
        print(f"{'-'*70}")
        for i, stats in enumerate(report['top_patterns'], 1):
            classification_symbol = "[+]" if stats.classification == "content" else "[-]"
            print(f"{i}. {stats.pattern} ({stats.pattern_type}) -> {classification_symbol} {stats.classification}")
            print(f"   Precision: {stats.precision:.2%} | Applied: {stats.times_applied} times")
            if stats.last_used_at:
                print(f"   Last used: {stats.last_used_at}")
            print()
    else:
        print(f"No patterns learned yet.\n")

    # Low-performing patterns
    if report['low_performing_patterns']:
        print(f"Low-Performing Patterns (precision < 70%):")
        print(f"{'-'*70}")
        for stats in report['low_performing_patterns']:
            classification_symbol = "[+]" if stats.classification == "content" else "[-]"
            print(f"[!] {stats.pattern} ({stats.pattern_type}) -> {classification_symbol} {stats.classification}")
            print(f"   Precision: {stats.precision:.2%} | Applied: {stats.times_applied} times")
            print(f"   Status: {stats.status}")
            print()

    # Re-evaluation status
    if report['pending_reevaluation_count'] > 0:
        print(f"Re-evaluation Queue:")
        print(f"{'-'*70}")
        print(f"{report['pending_reevaluation_count']} URLs are pending batch re-evaluation.")
        print(f"These are low-confidence classifications that will be re-evaluated")
        print(f"when we have 3+ URLs from the same domain for better context.\n")
        print(f"Run batch re-evaluation with:")
        print(f"  uv run python tools/scripts/filter_description_urls.py --reevaluate-low-confidence\n")

    print(f"{'='*70}\n")


def show_full_report(report: dict) -> None:
    """Show complete pattern effectiveness report.

    Args:
        report: Pattern effectiveness report from PatternTracker
    """
    from compose.services.analytics import create_pattern_tracker

    # This uses the same display logic as filter_description_urls.py --show-pattern-stats
    tracker = create_pattern_tracker()

    print(f"{'='*70}")
    print(f"Pattern Effectiveness Report")
    print(f"{'='*70}\n")

    print(f"Total learned patterns: {report['total_patterns']}")
    print(f"Active patterns: {report['active_patterns']}")
    print(f"Inactive patterns: {report['inactive_patterns']}")
    print(f"Pending re-evaluation: {report['pending_reevaluation_count']} URLs\n")

    if report['top_patterns']:
        print(f"Top Patterns (by usage):")
        print(f"{'-'*70}")
        for i, stats in enumerate(report['top_patterns'], 1):
            print(f"{i}. {stats.pattern} ({stats.pattern_type}) -> {stats.classification}")
            print(f"   Precision: {stats.precision:.2f} | Applied: {stats.times_applied} times")
            if stats.last_used_at:
                print(f"   Last used: {stats.last_used_at}")
            print()

    if report['low_performing_patterns']:
        print(f"\nLow-Performing Patterns (precision < 0.7):")
        print(f"{'-'*70}")
        for stats in report['low_performing_patterns']:
            print(f"- {stats.pattern} ({stats.pattern_type}) -> {stats.classification}")
            print(f"  Precision: {stats.precision:.2f} | Applied: {stats.times_applied} times | Status: {stats.status}")
            print()

    print(f"{'='*70}\n")


def main():
    """Main entry point."""
    import argparse

    parser = argparse.ArgumentParser(
        description="Display URL pattern learning status"
    )
    parser.add_argument(
        "--summary",
        action="store_true",
        help="Show quick summary only",
    )
    parser.add_argument(
        "--detailed",
        action="store_true",
        help="Show detailed pattern breakdown",
    )
    parser.add_argument(
        "--full",
        action="store_true",
        help="Show complete pattern effectiveness report",
    )

    args = parser.parse_args()

    # Initialize pattern tracker
    pattern_tracker = create_pattern_tracker()

    try:
        # Check for batch processing progress
        progress = get_batch_progress()
        if progress:
            show_batch_progress(progress)

        # Get pattern effectiveness report
        report = pattern_tracker.get_pattern_effectiveness_report()

        if args.summary:
            show_summary(report)
        elif args.detailed:
            show_detailed(report)
        elif args.full:
            show_full_report(report)
        else:
            # Default: show detailed view
            show_detailed(report)

    except KeyboardInterrupt:
        print("\n\nInterrupted by user")
        sys.exit(0)
    except Exception as e:
        import traceback
        traceback.print_exc()
        print(f"\n[ERROR] {type(e).__name__}: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
