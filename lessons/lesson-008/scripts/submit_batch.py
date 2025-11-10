"""Submit batch job to OpenAI Batch API.

This script uploads the prepared JSONL file and creates a batch job.

Usage:
    python submit_batch.py --input batch.jsonl
    python submit_batch.py --input batch.jsonl --description "Tag Nate Jones videos"
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

from cache import QdrantCache
from batch import BatchProcessor
from tools.env_loader import load_root_env

console = Console()
load_root_env()


def main():
    """Main CLI entrypoint."""
    parser = argparse.ArgumentParser(
        description="Submit batch job to OpenAI",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Submit batch
  python submit_batch.py --input batch_input.jsonl

  # With description
  python submit_batch.py --input batch.jsonl --description "Tag AI videos"
        """
    )

    parser.add_argument(
        "--input",
        type=Path,
        required=True,
        help="Input JSONL file to submit"
    )

    parser.add_argument(
        "--description",
        type=str,
        help="Description for batch job"
    )

    parser.add_argument(
        "--collection",
        type=str,
        default="content",
        help="Collection name (for processor initialization)"
    )

    args = parser.parse_args()

    # Check file exists
    if not args.input.exists():
        console.print(f"[red]Error: Input file not found: {args.input}[/red]")
        sys.exit(1)

    # Check API key
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        console.print("[red]Error: OPENAI_API_KEY not found in environment[/red]")
        console.print("[yellow]Make sure you have a .env file with OPENAI_API_KEY=sk-...[/yellow]")
        sys.exit(1)

    # Initialize
    cache = QdrantCache(collection_name=args.collection)
    processor = BatchProcessor(cache, api_key=api_key)

    # Submit batch
    console.print(f"[bold cyan]Submitting batch job...[/bold cyan]")
    console.print(f"Input file: {args.input}")

    if args.description:
        console.print(f"Description: {args.description}")

    try:
        batch_id = processor.submit_batch(
            input_file=args.input,
            description=args.description
        )

        console.print("\n[bold green]✓ Batch submitted successfully![/bold green]")
        console.print(f"\n[bold yellow]Batch ID: {batch_id}[/bold yellow]")
        console.print("\n[cyan]Save this batch ID! You'll need it to check status and download results.[/cyan]")
        console.print(f"\n[cyan]Next steps:[/cyan]")
        console.print(f"  1. Monitor: python check_status.py --batch-id {batch_id}")
        console.print(f"  2. When complete: python process_results.py --batch-id {batch_id}")

        # Save batch ID to file for convenience
        batch_id_file = Path("batch_id.txt")
        with open(batch_id_file, 'w') as f:
            f.write(batch_id)
        console.print(f"\n[dim]Batch ID also saved to {batch_id_file}[/dim]")

    except KeyboardInterrupt:
        console.print("\n[yellow]Interrupted by user[/yellow]")
        sys.exit(130)
    except Exception as e:
        console.print(f"\n[red]Error submitting batch: {e}[/red]")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
