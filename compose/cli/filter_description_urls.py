#!/usr/bin/env python
"""Filter URLs from YouTube video descriptions in existing archives.

This script processes YouTube archives to extract and classify URLs from video descriptions.
Uses heuristic filtering + LLM classification to identify content-related URLs.

Usage:
    # Process single video
    uv run python tools/scripts/filter_description_urls.py VIDEO_ID

    # Process all archives
    uv run python tools/scripts/filter_description_urls.py --all

    # Dry run (show what would be filtered)
    uv run python tools/scripts/filter_description_urls.py VIDEO_ID --dry-run

    # Heuristic only (no LLM calls)
    uv run python tools/scripts/filter_description_urls.py VIDEO_ID --heuristic-only
"""

import sys
import json
import asyncio
from pathlib import Path
from datetime import datetime

# Setup script environment
sys.path.insert(0, str(Path(__file__).parent))
from compose.cli.base import setup_script_environment
setup_script_environment()

from compose.services.archive import create_archive_manager
from compose.services.youtube.url_filter import filter_urls
from compose.services.analytics import create_async_pattern_tracker


def safe_print(text: str, **kwargs) -> None:
    """Print text with unicode encoding error handling for Windows console.

    Args:
        text: Text to print (may contain unicode characters)
        **kwargs: Additional arguments to pass to print()
    """
    try:
        print(text, **kwargs)
    except UnicodeEncodeError:
        # Replace problematic characters with safe representation
        safe_text = text.encode('ascii', errors='replace').decode('ascii')
        print(safe_text, **kwargs)


# Progress tracking
PROGRESS_FILE = Path("compose/data/archive/.url_filter_progress.json")


def update_progress(
    status: str,
    total: int = 0,
    processed: int = 0,
    current_video_id: str = "",
    errors: int = 0,
    started_at: str = None,
) -> None:
    """Update progress state file.

    Args:
        status: "running", "completed", or "idle"
        total: Total number of archives to process
        processed: Number of archives processed so far
        current_video_id: Currently processing video ID
        errors: Number of errors encountered
        started_at: ISO timestamp when processing started
    """
    progress_data = {
        "status": status,
        "total_archives": total,
        "processed": processed,
        "current_video_id": current_video_id,
        "errors": errors,
        "started_at": started_at or datetime.now().isoformat(),
        "last_updated": datetime.now().isoformat(),
    }

    PROGRESS_FILE.parent.mkdir(parents=True, exist_ok=True)
    PROGRESS_FILE.write_text(json.dumps(progress_data, indent=2))


def clear_progress() -> None:
    """Remove progress state file."""
    if PROGRESS_FILE.exists():
        PROGRESS_FILE.unlink()


async def process_video_urls(
    video_id: str,
    archive_manager,
    pattern_tracker,
    dry_run: bool = False,
    use_llm: bool = True,
) -> dict:
    """Process URLs for a single video with pattern learning.

    Args:
        video_id: YouTube video ID
        archive_manager: ArchiveManager instance
        pattern_tracker: PatternTracker instance
        dry_run: If True, don't update archive
        use_llm: If True, use LLM for classification

    Returns:
        Dict with processing results
    """
    # Get archive
    archive = archive_manager.get(video_id)
    if not archive:
        return {
            "success": False,
            "message": f"Archive not found for video_id: {video_id}",
        }

    # Check if description exists
    description = archive.youtube_metadata.get("description")
    if not description:
        return {
            "success": False,
            "message": f"No description found in archive for {video_id}",
        }

    # Build video context for LLM
    video_context = {
        "video_title": archive.youtube_metadata.get("title", "N/A"),
        "description": description,
        "channel": archive.youtube_metadata.get("channel_title", "N/A"),
    }

    # Filter URLs
    print(f"\nProcessing video: {video_id}")
    safe_print(f"Title: {video_context['video_title']}")
    safe_print(f"Channel: {video_context['channel']}")

    result = await filter_urls(
        description,
        video_context,
        video_id=video_id,
        use_llm=use_llm,
        pattern_tracker=pattern_tracker,
    )

    # Print summary
    print(f"\nURL Filtering Results:")
    print(f"  Total URLs found: {len(result['all_urls'])}")
    print(f"  Blocked (heuristic): {len(result['blocked_urls'])}")
    print(f"  Learned patterns: {len(result['learned_pattern_urls'])}")
    print(f"  Content URLs: {len(result['content_urls'])}")
    print(f"  Marketing URLs: {len(result['marketing_urls'])}")

    if use_llm:
        print(f"  LLM cost: ${result['total_llm_cost']:.4f}")

    # Print details
    if result['content_urls']:
        print(f"\n  Content URLs:")
        for url in result['content_urls']:
            print(f"    [+] {url}")

    if result['blocked_urls']:
        print(f"\n  Blocked URLs:")
        for url in result['blocked_urls']:
            print(f"    [-] {url}")

    if result['marketing_urls']:
        print(f"\n  Marketing URLs (LLM):")
        for url in result['marketing_urls']:
            print(f"    [-] {url}")

    # Print learned pattern matches
    if result['learned_patterns_applied']:
        print(f"\n  Learned Pattern Matches:")
        for item in result['learned_patterns_applied']:
            symbol = "[+]" if item['classification'] == "content" else "[-]"
            print(f"    {symbol} {item['url']} (confidence: {item['confidence']:.2f})")
            print(f"      {item['reason']}")

    # Print LLM classifications
    if use_llm and result['llm_classifications']:
        print(f"\n  LLM Classifications:")
        for item in result['llm_classifications']:
            symbol = "[+]" if item['classification'] == "content" else "[-]"
            confidence = item.get('confidence', 0.0)
            print(f"    {symbol} {item['url']} (confidence: {confidence:.2f})")
            print(f"      Reason: {item['reason']}")
            if item.get('suggested_pattern'):
                pattern_info = item['suggested_pattern']
                print(f"      Pattern suggested: {pattern_info.get('pattern')} ({pattern_info.get('type')})")

    # Update archive (if not dry run)
    if not dry_run:
        print(f"\nUpdating archive...")

        # Add URL fields to youtube_metadata
        archive.youtube_metadata["all_urls"] = result["all_urls"]
        archive.youtube_metadata["blocked_urls"] = result["blocked_urls"]
        archive.youtube_metadata["content_urls"] = result["content_urls"]
        archive.youtube_metadata["marketing_urls"] = result["marketing_urls"]
        archive.youtube_metadata["url_filter_version"] = "v1_heuristic_llm"
        archive.youtube_metadata["url_filtered_at"] = datetime.now().isoformat()

        # Update archive using manager
        archive_manager.writer.update(video_id, archive)
        print(f"  [OK] Archive updated")
    else:
        print(f"\n[DRY RUN] Archive NOT updated")

    return {
        "success": True,
        "video_id": video_id,
        "stats": {
            "total_urls": len(result["all_urls"]),
            "blocked_urls": len(result["blocked_urls"]),
            "learned_pattern_urls": len(result["learned_pattern_urls"]),
            "content_urls": len(result["content_urls"]),
            "marketing_urls": len(result["marketing_urls"]),
            "llm_cost": result["total_llm_cost"],
        },
    }


async def process_all_videos(
    archive_manager,
    pattern_tracker,
    dry_run: bool = False,
    use_llm: bool = True,
) -> dict:
    """Process URLs for all videos in archive with pattern learning.

    Args:
        archive_manager: ArchiveManager instance
        pattern_tracker: PatternTracker instance
        dry_run: If True, don't update archives
        use_llm: If True, use LLM for classification

    Returns:
        Dict with batch processing results
    """
    # Get all archive files
    youtube_dir = archive_manager.writer.youtube_dir

    # Find all JSON files
    archive_files = []
    if archive_manager.writer.config.organize_by_month:
        # Search in month directories
        for month_dir in youtube_dir.iterdir():
            if month_dir.is_dir():
                archive_files.extend(month_dir.glob("*.json"))
    else:
        # Search in flat structure
        archive_files = list(youtube_dir.glob("*.json"))

    print(f"Found {len(archive_files)} archives to process")

    # Initialize progress tracking
    started_at = datetime.now().isoformat()
    update_progress(
        status="running",
        total=len(archive_files),
        processed=0,
        errors=0,
        started_at=started_at,
    )

    # Process each video
    total_stats = {
        "processed": 0,
        "skipped": 0,
        "errors": 0,
        "total_urls": 0,
        "content_urls": 0,
        "blocked_urls": 0,
        "marketing_urls": 0,
        "total_llm_cost": 0.0,
    }

    for i, archive_file in enumerate(archive_files, 1):
        video_id = archive_file.stem

        # Update progress
        update_progress(
            status="running",
            total=len(archive_files),
            processed=i - 1,
            current_video_id=video_id,
            errors=total_stats["errors"],
            started_at=started_at,
        )

        try:
            result = await process_video_urls(video_id, archive_manager, pattern_tracker, dry_run, use_llm)

            if result["success"]:
                total_stats["processed"] += 1
                total_stats["total_urls"] += result["stats"]["total_urls"]
                total_stats["content_urls"] += result["stats"]["content_urls"]
                total_stats["blocked_urls"] += result["stats"]["blocked_urls"]
                total_stats["marketing_urls"] += result["stats"]["marketing_urls"]
                total_stats["total_llm_cost"] += result["stats"]["llm_cost"]
            else:
                total_stats["skipped"] += 1
                print(f"  [SKIP] {result['message']}")

        except Exception as e:
            total_stats["errors"] += 1
            print(f"  [ERROR] {video_id}: {e}")

        print("-" * 70)

    # Mark as completed
    update_progress(
        status="completed",
        total=len(archive_files),
        processed=len(archive_files),
        errors=total_stats["errors"],
        started_at=started_at,
    )

    # Print summary
    print(f"\n{'='*70}")
    print(f"Batch Processing Summary")
    print(f"{'='*70}")
    print(f"Total archives: {len(archive_files)}")
    print(f"Processed: {total_stats['processed']}")
    print(f"Skipped: {total_stats['skipped']}")
    print(f"Errors: {total_stats['errors']}")
    print(f"\nURL Statistics:")
    print(f"  Total URLs found: {total_stats['total_urls']}")
    print(f"  Content URLs: {total_stats['content_urls']}")
    print(f"  Blocked (heuristic): {total_stats['blocked_urls']}")
    print(f"  Marketing (LLM): {total_stats['marketing_urls']}")

    if use_llm:
        print(f"\nTotal LLM cost: ${total_stats['total_llm_cost']:.4f}")

    print(f"{'='*70}\n")

    return total_stats


async def show_pattern_stats(pattern_tracker) -> None:
    """Show pattern effectiveness statistics.

    Args:
        pattern_tracker: PatternTracker instance
    """
    print(f"{'='*70}")
    print(f"Pattern Effectiveness Report")
    print(f"{'='*70}\n")

    report = await pattern_tracker.get_pattern_effectiveness_report()

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


async def batch_reevaluate_low_confidence(pattern_tracker, archive_manager) -> None:
    """Batch re-evaluate low-confidence URLs from same domains.

    Args:
        pattern_tracker: PatternTracker instance
        archive_manager: ArchiveManager instance
    """
    from compose.services.youtube.url_filter import classify_url_with_llm

    print(f"{'='*70}")
    print(f"Batch Re-evaluation of Low-Confidence URLs")
    print(f"{'='*70}\n")

    # Get domains ready for batch re-evaluation
    domains = await pattern_tracker.get_domains_for_batch_reeval(min_count=3)

    if not domains:
        print("No domains found with 3+ low-confidence URLs")
        print("Re-evaluation requires multiple URLs from the same domain for better context\n")
        return

    print(f"Found {len(domains)} domains ready for re-evaluation:\n")

    total_cost = 0.0
    total_reevaluated = 0

    for domain_info in domains:
        print(f"Domain: {domain_info.domain}")
        print(f"  URLs: {domain_info.url_count}")
        print(f"  Avg confidence: {domain_info.avg_confidence:.2f}")
        print(f"  Classifications: {domain_info.classifications}")

        # Build aggregate context from all videos
        video_titles = []
        for video_id in domain_info.video_ids:
            archive = archive_manager.get(video_id)
            if archive:
                title = archive.youtube_metadata.get("title", "Unknown")
                video_titles.append(title)

        # Build enhanced context for re-evaluation
        aggregate_context = {
            "video_title": f"Aggregate context from {len(video_titles)} videos",
            "description": f"This domain appeared in videos: {', '.join(video_titles[:5])}...",
            "channel": "Multiple channels",
        }

        print(f"\n  Re-evaluating {len(domain_info.urls)} URLs...")

        # Re-evaluate each URL with aggregate context
        for url in domain_info.urls:
            try:
                classification, confidence, reason, suggested_pattern, cost = classify_url_with_llm(
                    url, aggregate_context
                )

                total_cost += cost
                total_reevaluated += 1

                print(f"    {url}")
                print(f"      New classification: {classification} (confidence: {confidence:.2f})")
                print(f"      Reason: {reason}")

                # Mark as re-evaluated
                await pattern_tracker.mark_reevaluated(url, classification, confidence)

                # Record new classification
                # Note: video_id would need to be looked up from pending_reevaluation table
                # For now, we'll skip recording to avoid complexity

                # If high confidence, suggest adding pattern
                if suggested_pattern and confidence >= 0.7:
                    print(f"      Suggested pattern: {suggested_pattern.get('pattern')} ({suggested_pattern.get('type')})")
                    await pattern_tracker.add_learned_pattern(
                        pattern=suggested_pattern.get("pattern"),
                        pattern_type=suggested_pattern.get("type", "domain"),
                        classification=classification,
                        confidence=confidence,
                    )

            except Exception as e:
                print(f"    [ERROR] {url}: {e}")

        print()

    print(f"{'='*70}")
    print(f"Re-evaluation Summary")
    print(f"{'='*70}")
    print(f"Domains processed: {len(domains)}")
    print(f"URLs re-evaluated: {total_reevaluated}")
    print(f"Total LLM cost: ${total_cost:.4f}")
    print(f"{'='*70}\n")


async def main():
    """Main entry point."""
    import argparse

    parser = argparse.ArgumentParser(
        description="Filter URLs from YouTube video descriptions"
    )
    parser.add_argument(
        "video_id",
        nargs="?",
        help="YouTube video ID to process (omit for --all)",
    )
    parser.add_argument(
        "--all",
        action="store_true",
        help="Process all archives",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be filtered without updating archives",
    )
    parser.add_argument(
        "--heuristic-only",
        action="store_true",
        help="Use heuristic filter only (no LLM calls)",
    )
    parser.add_argument(
        "--show-pattern-stats",
        action="store_true",
        help="Show learned pattern effectiveness statistics",
    )
    parser.add_argument(
        "--reevaluate-low-confidence",
        action="store_true",
        help="Batch re-evaluate low-confidence URLs from same domains",
    )

    args = parser.parse_args()

    # Validate arguments
    if not args.video_id and not args.all and not args.show_pattern_stats and not args.reevaluate_low_confidence:
        parser.print_help()
        print("\nError: Provide VIDEO_ID, --all, --show-pattern-stats, or --reevaluate-low-confidence")
        sys.exit(1)

    if args.video_id and args.all:
        print("Error: Cannot specify both VIDEO_ID and --all")
        sys.exit(1)

    # Initialize services
    archive_manager = create_archive_manager()
    pattern_tracker = await create_async_pattern_tracker()
    await pattern_tracker.init_schema()

    # Configure LLM usage
    use_llm = not args.heuristic_only

    try:
        if args.show_pattern_stats:
            # Show pattern statistics
            await show_pattern_stats(pattern_tracker)
        elif args.reevaluate_low_confidence:
            # Batch re-evaluate low-confidence URLs
            await batch_reevaluate_low_confidence(pattern_tracker, archive_manager)
        elif args.all:
            # Process all videos
            print(f"{'='*70}")
            print(f"Batch URL Filtering")
            print(f"{'='*70}")
            print(f"Mode: {'Heuristic + LLM' if use_llm else 'Heuristic only'}")
            print(f"Dry run: {args.dry_run}")
            print(f"{'='*70}\n")

            stats = await process_all_videos(archive_manager, pattern_tracker, args.dry_run, use_llm)

            if stats["errors"] > 0:
                sys.exit(1)
        else:
            # Process single video
            print(f"{'='*70}")
            print(f"Single Video URL Filtering")
            print(f"{'='*70}")
            print(f"Video ID: {args.video_id}")
            print(f"Mode: {'Heuristic + LLM' if use_llm else 'Heuristic only'}")
            print(f"Dry run: {args.dry_run}")
            print(f"{'='*70}")

            result = await process_video_urls(
                args.video_id,
                archive_manager,
                pattern_tracker,
                args.dry_run,
                use_llm,
            )

            if not result["success"]:
                print(f"\n[ERROR] {result['message']}")
                sys.exit(1)

            print(f"\n{'='*70}")
            print(f"SUCCESS!")
            print(f"{'='*70}\n")

    except KeyboardInterrupt:
        print("\n\nInterrupted by user")
        sys.exit(0)
    except Exception as e:
        import traceback
        traceback.print_exc()
        print(f"\n[ERROR] {type(e).__name__}: {e}")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
