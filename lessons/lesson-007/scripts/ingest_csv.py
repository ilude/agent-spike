"""CSV ingestion script for populating cache with content from URL lists.

This script reads a CSV file containing URLs and other metadata, fetches the content
using the appropriate agent (via lesson-003 router), and stores it in the cache.

Usage:
    python ingest_csv.py --csv path/to/file.csv
    python ingest_csv.py --csv path/to/file.csv --collection my_content
    python ingest_csv.py --csv path/to/file.csv --limit 10

Requirements:
    - CSV must have a 'url' column (required)
    - Optional columns: title, upload_date, duration, etc.
    - Additional columns will be stored as metadata
"""

import asyncio
import csv
import sys
import time
from pathlib import Path
from typing import Optional
import argparse

# Add parent directories to path for imports
lesson_007_dir = Path(__file__).parent.parent
lesson_003_dir = lesson_007_dir.parent / "lesson-003"
lesson_001_dir = lesson_007_dir.parent / "lesson-001"
lesson_002_dir = lesson_007_dir.parent / "lesson-002"

sys.path.insert(0, str(lesson_007_dir))
sys.path.insert(0, str(lesson_003_dir))
sys.path.insert(0, str(lesson_001_dir))
sys.path.insert(0, str(lesson_002_dir))

from tqdm import tqdm
from rich.console import Console
from rich.table import Table

# Import cache from lesson-007
from cache import QdrantCache

# Import router from lesson-003
from coordinator_agent.router import URLRouter, URLType

# Import tools from lessons 001/002
from youtube_agent.tools import get_transcript, get_video_info, extract_video_id
from webpage_agent.tools import fetch_webpage, get_page_info

console = Console()


def read_csv(csv_path: Path) -> list[dict]:
    """Read CSV file and return list of dictionaries.

    Args:
        csv_path: Path to CSV file

    Returns:
        List of row dictionaries

    Raises:
        ValueError: If CSV doesn't have 'url' column
    """
    with open(csv_path, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        rows = list(reader)

    if not rows:
        raise ValueError("CSV file is empty")

    if 'url' not in rows[0]:
        raise ValueError("CSV must have a 'url' column")

    return rows


def fetch_content(url: str, content_type: str, cache: Optional[QdrantCache] = None) -> Optional[dict]:
    """Fetch content for a URL using appropriate tools.

    Args:
        url: URL to fetch
        content_type: Content type ('youtube' or 'webpage')
        cache: Optional cache for tools to use

    Returns:
        Dictionary with fetched content, or None if error.
        Returns {"_rate_limited": True} if YouTube rate limiting detected.
    """
    try:
        if content_type == "youtube":
            # Fetch YouTube content
            video_id = extract_video_id(url)
            transcript = get_transcript(url, cache=cache)

            if transcript.startswith("ERROR:"):
                console.print(f"[yellow]Warning: {transcript}[/yellow]")

                # Check if this is a rate limiting error
                if "YouTube is blocking requests from your IP" in transcript:
                    return {"_rate_limited": True}

                return None

            return {
                "video_id": video_id,
                "url": url,
                "transcript": transcript,
                "type": "youtube_video"
            }

        elif content_type == "webpage":
            # Fetch webpage content
            markdown = fetch_webpage(url, cache=cache)

            if markdown.startswith("ERROR:"):
                console.print(f"[yellow]Warning: {markdown}[/yellow]")
                return None

            return {
                "url": url,
                "markdown": markdown,
                "length": len(markdown),
                "type": "webpage"
            }

        else:
            console.print(f"[red]Unknown content type: {content_type}[/red]")
            return None

    except Exception as e:
        console.print(f"[red]Error fetching {url}: {e}[/red]")
        return None


def generate_cache_key(url: str, content_type: str) -> str:
    """Generate cache key for content.

    Args:
        url: Content URL
        content_type: Type of content

    Returns:
        Cache key string
    """
    if content_type == "youtube":
        try:
            video_id = extract_video_id(url)
            return f"youtube:transcript:{video_id}"
        except:
            return f"{content_type}:{url}"
    else:
        import hashlib
        url_hash = hashlib.sha256(url.encode()).hexdigest()[:16]
        return f"{content_type}:content:{url_hash}"


def ingest_csv(
    csv_path: Path,
    collection_name: str = "content",
    limit: Optional[int] = None,
    skip_existing: bool = True,
    delay: float = 5.0
) -> dict:
    """Ingest CSV file into cache.

    Args:
        csv_path: Path to CSV file
        collection_name: Qdrant collection name
        limit: Optional limit on number of NEW items to download (excludes cached)
        skip_existing: Skip URLs that are already cached
        delay: Delay in seconds between requests to avoid rate limiting (default: 5.0)

    Returns:
        Statistics dictionary with counts
    """
    # Read CSV
    console.print(f"[cyan]Reading CSV: {csv_path}[/cyan]")
    rows = read_csv(csv_path)
    total_rows = len(rows)

    if limit:
        console.print(f"[yellow]Will download up to {limit} new transcripts (out of {total_rows} total URLs)[/yellow]")

    if delay > 0:
        console.print(f"[yellow]Rate limiting: {delay}s delay between requests[/yellow]")

    # Initialize cache
    console.print(f"[cyan]Initializing cache (collection: {collection_name})...[/cyan]")
    cache = QdrantCache(collection_name=collection_name)
    console.print(f"[green]Cache initialized. Current count: {cache.count()}[/green]")

    # Process each row
    stats = {
        "total": total_rows,
        "processed": 0,
        "skipped": 0,
        "errors": 0,
        "youtube": 0,
        "webpage": 0,
        "other": 0,
        "rate_limited": False
    }

    with tqdm(total=total_rows, desc="Ingesting content") as pbar:
        for row in rows:
            # Check if we've hit the download limit
            if limit and stats["processed"] >= limit:
                console.print(f"\n[yellow]Reached download limit of {limit} new items. Stopping.[/yellow]")
                stats["total"] = stats["processed"] + stats["skipped"] + stats["errors"]
                break
            url = row["url"]

            # Determine content type using router
            url_type = URLRouter.classify_url(url)

            # Skip invalid URLs
            if url_type == URLType.INVALID:
                stats["errors"] += 1
                console.print(f"[yellow]Skipping invalid URL: {url}[/yellow]")
                pbar.set_postfix({"skipped": stats["skipped"], "errors": stats["errors"]})
                pbar.update(1)
                continue

            # Convert enum to string
            content_type = url_type.value

            # Generate cache key
            cache_key = generate_cache_key(url, content_type)

            # Skip if already cached
            if skip_existing and cache.exists(cache_key):
                stats["skipped"] += 1
                pbar.set_postfix({"skipped": stats["skipped"], "errors": stats["errors"]})
                pbar.update(1)
                continue

            # Fetch content
            content = fetch_content(url, content_type, cache=cache)

            # Check for rate limiting
            if content and content.get("_rate_limited"):
                stats["rate_limited"] = True
                console.print("\n[bold red]⚠️  YouTube Rate Limiting Detected![/bold red]")
                console.print("[yellow]Your IP has been temporarily blocked by YouTube.[/yellow]")
                console.print("[yellow]Stopping ingestion to avoid further errors.[/yellow]")
                console.print(f"\n[cyan]Progress: {stats['processed']} downloaded, {stats['skipped']} skipped, {stats['errors']} errors[/cyan]")
                console.print("\n[cyan]Wait a few hours before retrying. The script will resume from where it left off.[/cyan]")
                stats["total"] = stats["processed"] + stats["skipped"] + stats["errors"]
                break

            if content is None:
                stats["errors"] += 1
                pbar.set_postfix({"skipped": stats["skipped"], "errors": stats["errors"]})
                pbar.update(1)
                continue

            # Add any additional CSV fields as metadata
            metadata = {
                "type": content_type,
                "source": "csv_ingestion"
            }

            # Copy CSV columns to content and metadata
            for key, value in row.items():
                if key != "url" and value:  # Skip empty values
                    content[key] = value
                    if key in ["title", "upload_date", "duration", "view_count", "description"]:
                        metadata[key] = value

            # Store in cache
            cache.set(cache_key, content, metadata=metadata)

            # Update stats
            stats["processed"] += 1
            if content_type == "youtube":
                stats["youtube"] += 1
            elif content_type == "webpage":
                stats["webpage"] += 1
            else:
                stats["other"] += 1

            pbar.set_postfix({
                "processed": stats["processed"],
                "errors": stats["errors"]
            })
            pbar.update(1)

            # Rate limiting: delay between requests
            if delay > 0 and stats["processed"] < (limit or float('inf')):
                time.sleep(delay)

    # Print summary
    if stats["rate_limited"]:
        console.print("\n[bold yellow]Ingestion Stopped (Rate Limited)[/bold yellow]")
        table_title = "Ingestion Statistics (Partial)"
    else:
        console.print("\n[bold green]Ingestion Complete![/bold green]")
        table_title = "Ingestion Statistics"

    table = Table(title=table_title)
    table.add_column("Metric", style="cyan")
    table.add_column("Count", style="magenta")

    table.add_row("Total rows", str(stats["total"]))
    table.add_row("Processed", str(stats["processed"]))
    table.add_row("Skipped (cached)", str(stats["skipped"]))
    table.add_row("Errors", str(stats["errors"]))
    table.add_row("", "")
    table.add_row("YouTube videos", str(stats["youtube"]))
    table.add_row("Webpages", str(stats["webpage"]))
    table.add_row("Other", str(stats["other"]))
    table.add_row("", "")
    table.add_row("Cache total", str(cache.count()))

    console.print(table)

    if stats["rate_limited"]:
        console.print("\n[yellow]💡 Tip: Re-run the same command later to continue from where you left off.[/yellow]")

    return stats


def main():
    """Main CLI entrypoint."""
    parser = argparse.ArgumentParser(
        description="Ingest CSV file into content cache",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Ingest Nate Jones videos with default 5s delay
  python ingest_csv.py --csv ../../projects/video-lists/nate_jones_videos.csv

  # Limit to 10 new downloads (skips cached)
  python ingest_csv.py --csv file.csv --limit 10

  # Custom delay to avoid rate limiting (default: 5s)
  python ingest_csv.py --csv file.csv --limit 30 --delay 10

  # No delay (faster but may hit rate limits)
  python ingest_csv.py --csv file.csv --limit 10 --delay 0

  # Use custom collection name
  python ingest_csv.py --csv file.csv --collection my_content

  # Force re-fetch (don't skip existing)
  python ingest_csv.py --csv file.csv --no-skip
        """
    )

    parser.add_argument(
        "--csv",
        type=Path,
        required=True,
        help="Path to CSV file with URLs"
    )

    parser.add_argument(
        "--collection",
        type=str,
        default="content",
        help="Qdrant collection name (default: content)"
    )

    parser.add_argument(
        "--limit",
        type=int,
        help="Limit number of NEW items to download (excludes already cached)"
    )

    parser.add_argument(
        "--no-skip",
        action="store_true",
        help="Don't skip already cached URLs (re-fetch)"
    )

    parser.add_argument(
        "--delay",
        type=float,
        default=5.0,
        help="Delay in seconds between requests to avoid rate limiting (default: 5.0)"
    )

    args = parser.parse_args()

    # Validate CSV path
    if not args.csv.exists():
        console.print(f"[red]Error: CSV file not found: {args.csv}[/red]")
        sys.exit(1)

    # Run ingestion
    try:
        stats = ingest_csv(
            csv_path=args.csv,
            collection_name=args.collection,
            limit=args.limit,
            skip_existing=not args.no_skip,
            delay=args.delay
        )

        # Exit with error code if there were errors
        if stats["errors"] > 0:
            sys.exit(1)

    except KeyboardInterrupt:
        console.print("\n[yellow]Interrupted by user[/yellow]")
        sys.exit(130)
    except Exception as e:
        console.print(f"\n[red]Fatal error: {e}[/red]")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
