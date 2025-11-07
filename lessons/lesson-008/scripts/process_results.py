"""Download and process batch results.

This script downloads the completed batch results, parses them,
and updates the cache with generated tags.

Usage:
    python process_results.py --batch-id batch_xyz789
    python process_results.py --batch-id batch_xyz789 --no-update  # Don't update cache
"""

import sys
import os
from pathlib import Path
import argparse

# Add parent directories to path
lesson_008_dir = Path(__file__).parent.parent
lesson_007_dir = lesson_008_dir.parent / "lesson-007"

sys.path.insert(0, str(lesson_008_dir))
sys.path.insert(0, str(lesson_007_dir))

from rich.console import Console
from rich.console import Console

from cache import QdrantCache
from batch import BatchProcessor
from tools.dotenv import load_root_env

console = Console()
load_root_env()


def main():
    """Main CLI entrypoint."""
    parser = argparse.ArgumentParser(
        description="Download and process batch results",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Download and update cache
  python process_results.py --batch-id batch_xyz789

  # Download only (don't update cache)
  python process_results.py --batch-id batch_xyz789 --no-update

  # Custom output file
  python process_results.py --batch-id batch_xyz789 --output results.jsonl
        """
    )

    parser.add_argument(
        "--batch-id",
        type=str,
        help="Batch job ID to process"
    )

    parser.add_argument(
        "--output",
        type=Path,
        default=Path("batch_results.jsonl"),
        help="Output file for results (default: batch_results.jsonl)"
    )

    parser.add_argument(
        "--no-update",
        action="store_true",
        help="Don't update cache with results"
    )

    parser.add_argument(
        "--collection",
        type=str,
        default="content",
        help="Collection name"
    )

    args = parser.parse_args()

    # Try to read batch_id from file if not provided
    if not args.batch_id:
        batch_id_file = Path("batch_id.txt")
        if batch_id_file.exists():
            args.batch_id = batch_id_file.read_text().strip()
            console.print(f"[dim]Using batch ID from {batch_id_file}[/dim]\n")
        else:
            console.print("[red]Error: --batch-id required (or batch_id.txt file)[/red]")
            sys.exit(1)

    # Check API key
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        console.print("[red]Error: OPENAI_API_KEY not found in environment[/red]")
        sys.exit(1)

    # Initialize
    console.print(f"[cyan]Initializing cache (collection: {args.collection})...[/cyan]")
    cache = QdrantCache(collection_name=args.collection)

    console.print("[cyan]Initializing batch processor...[/cyan]")
    processor = BatchProcessor(cache, api_key=api_key)

    try:
        # Download results
        console.print(f"\n[bold cyan]Downloading results for {args.batch_id}...[/bold cyan]")

        results_file = processor.download_results(
            batch_id=args.batch_id,
            output_file=args.output
        )

        # Process results
        console.print(f"\n[bold cyan]Processing results...[/bold cyan]")

        update_cache = not args.no_update
        if not update_cache:
            console.print("[yellow]Cache update disabled (--no-update)[/yellow]")

        stats = processor.process_results(
            results_file=results_file,
            update_cache=update_cache
        )

        # Display summary table
        console.print("\n")
        table = Table(title="Batch Processing Summary")
        table.add_column("Metric", style="cyan")
        table.add_column("Count", style="white")

        table.add_row("Total Responses", str(stats["total"]))
        table.add_row("Successful", f"[green]{stats['successful']}[/green]")

        if stats["failed"] > 0:
            table.add_row("Failed", f"[red]{stats['failed']}[/red]")

        if update_cache:
            table.add_row("Cache Updated", f"[cyan]{stats['cache_updated']}[/cyan]")

        console.print(table)

        # Show errors if any
        if stats["errors"]:
            console.print(f"\n[yellow]Errors encountered ({len(stats['errors'])}):[/yellow]")
            for i, error in enumerate(stats["errors"][:5], 1):  # Show first 5
                console.print(f"  {i}. {error.get('custom_id', 'unknown')}: {error.get('error', 'unknown error')}")

            if len(stats["errors"]) > 5:
                console.print(f"  ... and {len(stats['errors']) - 5} more errors")

        # Success
        if stats["successful"] > 0:
            console.print("\n[bold green]✓ Batch processing complete![/bold green]")

            if update_cache:
                console.print(f"[green]✓ Updated {stats['cache_updated']} items in cache[/green]")
                console.print("\n[cyan]Next steps:[/cyan]")
                console.print(f"  • Query cache for tagged content")
                console.print(f"  • Search by semantic similarity")
                console.print(f"  • Build recommendation engine")

        sys.exit(0 if stats["failed"] == 0 else 1)

    except KeyboardInterrupt:
        console.print("\n[yellow]Interrupted by user[/yellow]")
        sys.exit(130)
    except Exception as e:
        console.print(f"\n[red]Error processing results: {e}[/red]")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
