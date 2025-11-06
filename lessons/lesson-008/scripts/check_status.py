"""Check status of OpenAI batch job.

This script monitors the progress of a batch job and displays current status.

Usage:
    python check_status.py --batch-id batch_xyz789
    python check_status.py --batch-id batch_xyz789 --watch  # Auto-refresh
"""

import sys
import os
import time
from pathlib import Path
import argparse
from datetime import datetime

# Add parent directories to path
lesson_008_dir = Path(__file__).parent.parent
lesson_007_dir = lesson_008_dir.parent / "lesson-007"

sys.path.insert(0, str(lesson_008_dir))
sys.path.insert(0, str(lesson_007_dir))

from rich.console import Console
from rich.table import Table
from rich.live import Live
from dotenv import load_dotenv

from cache import QdrantCache
from batch import BatchProcessor

console = Console()
load_dotenv()


def display_status(status_info: dict) -> Table:
    """Create rich table for status display."""
    table = Table(title="Batch Job Status", show_header=False)
    table.add_column("Field", style="cyan")
    table.add_column("Value", style="white")

    # Basic info
    table.add_row("Batch ID", status_info["id"])
    table.add_row("Status", f"[bold]{status_info['status']}[/bold]")

    # Timestamps
    if "created_at" in status_info:
        table.add_row("Created", status_info["created_at"])

    if "started_at" in status_info:
        table.add_row("Started", status_info["started_at"])

    if "completed_at" in status_info:
        table.add_row("Completed", status_info["completed_at"])

    # Progress
    if "total" in status_info:
        completed = status_info.get("completed", 0)
        failed = status_info.get("failed", 0)
        total = status_info["total"]

        table.add_row("", "")  # Separator
        table.add_row("Total Requests", str(total))
        table.add_row("Completed", f"[green]{completed}[/green]")
        table.add_row("Failed", f"[red]{failed}[/red]" if failed > 0 else str(failed))

        if "progress_pct" in status_info:
            progress = status_info["progress_pct"]
            table.add_row("Progress", f"{progress}%")

    # File IDs
    if "output_file_id" in status_info:
        table.add_row("", "")
        table.add_row("Output File", status_info["output_file_id"])

    if "error_file_id" in status_info:
        table.add_row("Error File", status_info["error_file_id"])

    return table


def main():
    """Main CLI entrypoint."""
    parser = argparse.ArgumentParser(
        description="Check batch job status",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Single status check
  python check_status.py --batch-id batch_xyz789

  # Watch mode (auto-refresh every 60 seconds)
  python check_status.py --batch-id batch_xyz789 --watch

  # Custom refresh interval
  python check_status.py --batch-id batch_xyz789 --watch --interval 30
        """
    )

    parser.add_argument(
        "--batch-id",
        type=str,
        help="Batch job ID to check"
    )

    parser.add_argument(
        "--watch",
        action="store_true",
        help="Auto-refresh status (poll periodically)"
    )

    parser.add_argument(
        "--interval",
        type=int,
        default=60,
        help="Refresh interval in seconds (default: 60)"
    )

    parser.add_argument(
        "--collection",
        type=str,
        default="content",
        help="Collection name (for processor initialization)"
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
    cache = QdrantCache(collection_name=args.collection)
    processor = BatchProcessor(cache, api_key=api_key)

    try:
        if args.watch:
            # Watch mode with auto-refresh
            console.print("[cyan]Monitoring batch status (Ctrl+C to exit)...[/cyan]\n")

            with Live(console=console, refresh_per_second=1) as live:
                while True:
                    status_info = processor.check_status(args.batch_id)
                    table = display_status(status_info)
                    live.update(table)

                    # Check if completed
                    if status_info["status"] in ["completed", "failed", "cancelled", "expired"]:
                        console.print(f"\n[bold]Batch {status_info['status']}![/bold]")

                        if status_info["status"] == "completed":
                            console.print(f"[green]✓ Ready to process results![/green]")
                            console.print(f"[cyan]Run: python process_results.py --batch-id {args.batch_id}[/cyan]")

                        break

                    # Wait before next check
                    time.sleep(args.interval)

        else:
            # Single check
            status_info = processor.check_status(args.batch_id)
            table = display_status(status_info)
            console.print(table)

            # Show next steps
            if status_info["status"] == "completed":
                console.print(f"\n[green]✓ Batch completed![/green]")
                console.print(f"[cyan]Run: python process_results.py --batch-id {args.batch_id}[/cyan]")
            elif status_info["status"] in ["validating", "in_progress", "finalizing"]:
                console.print(f"\n[yellow]⏳ Batch still processing...[/yellow]")
                console.print(f"[cyan]Use --watch to monitor: python check_status.py --batch-id {args.batch_id} --watch[/cyan]")
            elif status_info["status"] in ["failed", "cancelled", "expired"]:
                console.print(f"\n[red]✗ Batch {status_info['status']}[/red]")

    except KeyboardInterrupt:
        console.print("\n[yellow]Interrupted by user[/yellow]")
        sys.exit(0)
    except Exception as e:
        console.print(f"\n[red]Error checking status: {e}[/red]")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
