"""Prepare batch input JSONL file from cached content.

This script loads content from the Qdrant cache and creates a JSONL file
suitable for submission to OpenAI's Batch API.

Usage:
    python prepare_batch.py --collection nate_content --output batch.jsonl
    python prepare_batch.py --collection content --limit 10 --output test.jsonl
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
from dotenv import load_dotenv

from cache import QdrantCache
from batch import BatchProcessor

console = Console()
load_dotenv()


def main():
    """Main CLI entrypoint."""
    parser = argparse.ArgumentParser(
        description="Prepare batch input file from cached content",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Prepare all YouTube videos
  python prepare_batch.py --collection nate_content --output batch.jsonl

  # Prepare first 10 items for testing
  python prepare_batch.py --collection content --limit 10 --output test.jsonl

  # Filter by metadata
  python prepare_batch.py --collection content --filter type=youtube_video --output yt_batch.jsonl
        """
    )

    parser.add_argument(
        "--collection",
        type=str,
        default="content",
        help="Qdrant collection name (default: content)"
    )

    parser.add_argument(
        "--output",
        type=Path,
        default=Path("batch_input.jsonl"),
        help="Output JSONL file path (default: batch_input.jsonl)"
    )

    parser.add_argument(
        "--limit",
        type=int,
        help="Limit number of items to process"
    )

    parser.add_argument(
        "--filter",
        type=str,
        action="append",
        help="Metadata filter (format: key=value, can specify multiple)"
    )

    parser.add_argument(
        "--model",
        type=str,
        default="gpt-4o-mini",
        help="OpenAI model to use (default: gpt-4o-mini)"
    )

    args = parser.parse_args()

    # Check API key
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        console.print("[red]Error: OPENAI_API_KEY not found in environment[/red]")
        console.print("[yellow]Make sure you have a .env file with OPENAI_API_KEY=sk-...[/yellow]")
        sys.exit(1)

    # Parse filters
    filters = {}
    if args.filter:
        for f in args.filter:
            if '=' not in f:
                console.print(f"[red]Invalid filter format: {f}[/red]")
                console.print("[yellow]Use format: key=value[/yellow]")
                sys.exit(1)
            key, value = f.split('=', 1)
            filters[key] = value

    # Initialize
    console.print(f"[cyan]Initializing cache (collection: {args.collection})...[/cyan]")
    cache = QdrantCache(collection_name=args.collection)

    console.print(f"[cyan]Initializing batch processor (model: {args.model})...[/cyan]")
    processor = BatchProcessor(cache, api_key=api_key, model=args.model)

    # Prepare batch
    try:
        count = processor.prepare_batch_input(
            filters=filters if filters else None,
            output_file=args.output,
            limit=args.limit
        )

        if count == 0:
            console.print("[yellow]No items prepared. Check your filters and cache content.[/yellow]")
            sys.exit(1)

        # Show file size
        file_size = args.output.stat().st_size
        console.print(f"[green]✓ Batch input ready: {args.output} ({file_size:,} bytes)[/green]")
        console.print(f"[cyan]Next step: python submit_batch.py --input {args.output}[/cyan]")

    except KeyboardInterrupt:
        console.print("\n[yellow]Interrupted by user[/yellow]")
        sys.exit(130)
    except Exception as e:
        console.print(f"\n[red]Error: {e}[/red]")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
