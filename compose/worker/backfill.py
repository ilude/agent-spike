#!/usr/bin/env python
"""Backfill worker - processes stale videos that need pipeline step updates.

This worker scans Neo4j for videos with outdated pipeline step versions
and reprocesses them. It can be run alongside queue_processor.

Usage:
    python -m compose.worker.backfill --step fetch_transcript --batch 50
    python -m compose.worker.backfill --all --batch 20
"""

import argparse
import asyncio
from datetime import datetime

from compose.lib.env_loader import load_root_env


def log(msg: str):
    """Log with timestamp."""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"[{timestamp}] {msg}", flush=True)


def run_backfill_for_step(step_name: str, batch_size: int = 50) -> dict:
    """Run backfill for a specific pipeline step.

    Args:
        step_name: Name of the step to backfill
        batch_size: Number of videos to process

    Returns:
        Summary dict
    """
    from compose.services.pipeline import run_backfill, get_step, get_backfill_counts

    step = get_step(step_name)
    if not step:
        log(f"ERROR: Step '{step_name}' not found")
        return {"error": f"Step '{step_name}' not found"}

    _, metadata = step
    log(f"Backfilling step: {step_name} (version: {metadata.version_hash})")

    # Get count of stale videos
    counts = get_backfill_counts()
    stale_count = counts.get(step_name, 0)
    log(f"Found {stale_count} videos needing reprocessing")

    if stale_count == 0:
        return {"step": step_name, "queued": 0, "succeeded": 0, "failed": 0}

    # Process batch
    summary = run_backfill(step_name, batch_size=batch_size)
    log(f"Processed: {summary['succeeded']} succeeded, {summary['failed']} failed")

    return summary


def run_backfill_all(batch_size: int = 20) -> dict:
    """Run backfill for all pipeline steps.

    Args:
        batch_size: Number of videos to process per step

    Returns:
        Summary dict
    """
    from compose.services.pipeline import get_all_steps, get_backfill_counts

    log("=== Backfill All Steps ===")
    steps = get_all_steps()
    counts = get_backfill_counts()

    total_summary = {
        "steps_processed": 0,
        "total_succeeded": 0,
        "total_failed": 0,
        "details": {},
    }

    for step_name in steps:
        stale_count = counts.get(step_name, 0)
        if stale_count == 0:
            log(f"  {step_name}: 0 stale videos (skip)")
            continue

        log(f"  {step_name}: {stale_count} stale videos")
        summary = run_backfill_for_step(step_name, batch_size)

        total_summary["steps_processed"] += 1
        total_summary["total_succeeded"] += summary.get("succeeded", 0)
        total_summary["total_failed"] += summary.get("failed", 0)
        total_summary["details"][step_name] = summary

    log(f"=== Complete: {total_summary['total_succeeded']} succeeded, {total_summary['total_failed']} failed ===")
    return total_summary


def show_status():
    """Show backfill status for all steps."""
    import asyncio
    from compose.services.pipeline import get_all_steps, get_backfill_counts
    from compose.services.surrealdb import get_video_count

    log("=== Backfill Status ===")

    total_videos = asyncio.run(get_video_count())
    log(f"Total videos in database: {total_videos}")

    steps = get_all_steps()
    counts = get_backfill_counts()

    log("\nStep Status:")
    for step_name, metadata in steps.items():
        stale = counts.get(step_name, 0)
        processed = total_videos - stale
        pct = (processed / total_videos * 100) if total_videos > 0 else 0
        log(f"  {step_name}: {processed}/{total_videos} ({pct:.1f}%) - {stale} need backfill")
        log(f"    version: {metadata.version_hash}")


def main():
    load_root_env()

    parser = argparse.ArgumentParser(description="Backfill pipeline steps for stale videos")
    parser.add_argument("--step", help="Specific step to backfill")
    parser.add_argument("--all", action="store_true", help="Backfill all steps")
    parser.add_argument("--status", action="store_true", help="Show backfill status")
    parser.add_argument("--batch", type=int, default=50, help="Batch size (default: 50)")

    args = parser.parse_args()

    if args.status:
        show_status()
    elif args.all:
        run_backfill_all(batch_size=args.batch)
    elif args.step:
        run_backfill_for_step(args.step, batch_size=args.batch)
    else:
        show_status()


if __name__ == "__main__":
    main()
