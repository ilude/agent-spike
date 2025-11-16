#!/usr/bin/env python
"""Ingest a single YouTube video with transcript and tags.

This script fetches a video transcript, generates tags, and stores everything
in both the archive (JSON) and cache (Qdrant) for fast retrieval.

Usage:
    # Single video
    uv run python tools/scripts/ingest_video.py "https://youtube.com/watch?v=..."

    # With custom collection
    uv run python tools/scripts/ingest_video.py "https://youtube.com/watch?v=..." my_collection

    # Just show what would be done (dry run)
    uv run python tools/scripts/ingest_video.py "https://youtube.com/watch?v=..." --dry-run
"""

import asyncio
import sys
from pathlib import Path
from datetime import datetime

# Setup script environment
sys.path.insert(0, str(Path(__file__).parent))  # Add tools/scripts to path
from script_base import setup_script_environment
setup_script_environment(needs_agent=True)

# Import from centralized services
from tools.services.youtube import get_transcript, extract_video_id, fetch_video_metadata
from tools.services.cache import create_qdrant_cache
from tools.services.archive import create_archive_manager, ImportMetadata, ChannelContext

# Import agent from lesson (still experimental)
from youtube_agent.agent import create_agent


async def ingest_single_video(
    url: str,
    collection_name: str = "cached_content",
    dry_run: bool = False
) -> tuple[bool, str]:
    """Ingest a single YouTube video.

    Pipeline:
    1. Check if already cached (skip if exists)
    2. Fetch transcript -> Archive immediately
    3. Generate tags (LLM) -> Archive immediately
    4. Cache result in Qdrant

    Args:
        url: YouTube video URL
        collection_name: Qdrant collection name
        dry_run: If True, only show what would be done

    Returns:
        Tuple of (success: bool, message: str)
    """
    try:
        # Extract video ID
        video_id = extract_video_id(url)
        cache_key = f"youtube:video:{video_id}"

        print(f"\n{'='*70}")
        print(f"Ingesting Video")
        print(f"{'='*70}")
        print(f"Video ID: {video_id}")
        print(f"URL: {url}")
        print(f"Collection: {collection_name}")
        print(f"Dry Run: {dry_run}")
        print(f"{'='*70}\n")

        # Initialize services
        cache = create_qdrant_cache(collection_name=collection_name)
        archive = create_archive_manager()

        try:
            # Check if already cached
            print("[1/5] Checking cache...")
            if cache.exists(cache_key):
                print(f"  [SKIP] Video already cached: {video_id}\n")
                cached = cache.get(cache_key)
                if cached:
                    print(f"  Transcript: {cached.get('transcript_length', 0):,} chars")
                    print(f"  Tags: {cached.get('tags', 'N/A')}")
                return True, "Already cached"

            print(f"  [OK] Video not in cache, proceeding...\n")

            # Fetch transcript
            print("[2/6] Fetching transcript (via Webshare proxy)...")
            transcript = get_transcript(url, cache=None)

            if "ERROR:" in transcript:
                return False, f"Transcript fetch failed: {transcript}"

            print(f"  [OK] Fetched {len(transcript):,} characters\n")

            # Fetch YouTube metadata
            print("[3/6] Fetching YouTube metadata (Data API v3)...")
            youtube_metadata, metadata_error = fetch_video_metadata(video_id)

            if metadata_error:
                print(f"  [WARN] Metadata fetch failed: {metadata_error}")
                print(f"  [WARN] Continuing without metadata...\n")
                youtube_metadata = {}
            else:
                print(f"  [OK] Fetched metadata:")
                print(f"      Title: {youtube_metadata.get('title', 'N/A')}")
                print(f"      Duration: {youtube_metadata.get('duration', 'N/A')}")
                print(f"      Views: {youtube_metadata.get('view_count', 0):,}\n")

            if dry_run:
                print("[DRY RUN] Would archive transcript, metadata, and generate tags")
                print(f"  Archive path: projects/data/archive/YYYY-MM/{video_id}.json")
                print(f"  Cache key: {cache_key}")
                return True, "Dry run complete (no changes made)"

            # Archive transcript
            print("[4/6] Archiving transcript...")

            # Create import metadata for single CLI import
            import_metadata = ImportMetadata(
                source_type="single_import",
                imported_at=datetime.now(),
                import_method="cli",
                channel_context=ChannelContext(),
                recommendation_weight=1.0
            )

            # Use Archive Manager to handle transcript
            archive.update_transcript(
                video_id=video_id,
                url=url,
                transcript=transcript,
                import_metadata=import_metadata
            )

            # Archive metadata (merges with existing transcript)
            if youtube_metadata:
                archive.update_metadata(
                    video_id=video_id,
                    url=url,
                    metadata=youtube_metadata
                )

            print(f"  [OK] Archived transcript and metadata\n")

            # Generate structured metadata
            print("[5/6] Generating tags with Claude Haiku...")
            agent = create_agent(instrument=False)

            # Agent will use the new prompt from prompts.py
            result = await agent.run(url)

            # Extract structured tags (JSON response)
            import json
            tags_output = result.output if hasattr(result, 'output') else str(result)

            try:
                # Parse JSON response
                tags_data = json.loads(tags_output)
                print(f"  [OK] Generated metadata:")
                print(f"      Title: {tags_data.get('title', 'N/A')}")
                print(f"      Subject: {tags_data.get('subject_matter', [])[:3]}...")
                print(f"      Style: {tags_data.get('content_style', 'N/A')}\n")
            except json.JSONDecodeError:
                # Fallback to old format if JSON parsing fails
                print(f"  [WARN] Failed to parse JSON, using fallback format\n")
                tags_data = {"raw_output": tags_output}

            # Archive LLM output (full structured data)
            archive.writer.add_llm_output(
                video_id=video_id,
                output_type="metadata",
                output_value=json.dumps(tags_data, indent=2),
                model="claude-3-5-haiku-20241022",
                cost_usd=0.001,  # Approximate
            )

            # Cache result
            print("[6/6] Caching in Qdrant...")
            cache_data = {
                "video_id": video_id,
                "url": url,
                "transcript": transcript,
                "transcript_length": len(transcript),
                "metadata": tags_data,  # Full structured metadata
            }

            # Build flattened metadata for Qdrant filtering
            metadata = {
                "type": "youtube_video",
                "source": "youtube-transcript-api",
                "video_id": video_id,
                "content_style": tags_data.get("content_style"),
                "difficulty": tags_data.get("difficulty"),
                # Import tracking for recommendations
                "source_type": "single_import",
                "recommendation_weight": 1.0,
                "imported_at": datetime.now().isoformat(),
                "is_bulk_import": False,
                # YouTube metadata (if available)
                "youtube_title": youtube_metadata.get("title"),
                "youtube_channel": youtube_metadata.get("channel_title"),
                "youtube_duration_seconds": youtube_metadata.get("duration_seconds"),
                "youtube_view_count": youtube_metadata.get("view_count"),
                "youtube_published_at": youtube_metadata.get("published_at"),
            }

            # Flatten metadata for Qdrant filtering
            from tools.services.metadata import flatten_video_metadata
            flattened = flatten_video_metadata(tags_data)
            metadata.update(flattened)

            cache.set(cache_key, cache_data, metadata=metadata)
            print(f"  [OK] Cached with key: {cache_key}\n")

            print(f"{'='*70}")
            print(f"SUCCESS!")
            print(f"{'='*70}")
            print(f"Video ID: {video_id}")
            print(f"Transcript: {len(transcript):,} characters")
            print(f"Title: {tags_data.get('title', 'N/A')}")
            print(f"Summary: {tags_data.get('summary', 'N/A')}")
            print(f"Subject Matter: {', '.join(tags_data.get('subject_matter', [])[:5])}")
            print(f"Content Style: {tags_data.get('content_style', 'N/A')}")
            print(f"Archive: {archive.writer.config.base_dir}")
            print(f"Cache: {collection_name}")
            print(f"{'='*70}\n")

            return True, f"Ingested {video_id} successfully"

        finally:
            cache.close()

    except ValueError as e:
        return False, f"Invalid URL: {e}"
    except Exception as e:
        import traceback
        traceback.print_exc()
        return False, f"Error: {type(e).__name__}: {e}"


async def main():
    """Main entry point."""
    try:
        if len(sys.argv) < 2:
            print("Error: YouTube URL required")
            print()
            print("Usage:")
            print("  uv run python tools/scripts/ingest_video.py <url> [collection_name] [--dry-run]")
            print()
            print("Examples:")
            print("  uv run python tools/scripts/ingest_video.py 'https://youtube.com/watch?v=dQw4w9WgXcQ'")
            print("  uv run python tools/scripts/ingest_video.py 'https://youtube.com/watch?v=dQw4w9WgXcQ' my_videos")
            print("  uv run python tools/scripts/ingest_video.py 'https://youtube.com/watch?v=dQw4w9WgXcQ' --dry-run")
            sys.exit(1)

        url = sys.argv[1]

        # Check for flags
        dry_run = "--dry-run" in sys.argv or "-n" in sys.argv

        # Get collection name (skip flags)
        collection_name = "cached_content"
        for arg in sys.argv[2:]:
            if not arg.startswith("-"):
                collection_name = arg
                break

        success, message = await ingest_single_video(url, collection_name, dry_run)

        if not success:
            print(f"\n[ERROR] {message}\n")
            sys.exit(1)

    except (KeyboardInterrupt, asyncio.CancelledError):
        print("\n\nKeyboard Interrupt Received... Exiting!")
        sys.exit(0)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        pass  # Clean exit - already handled in main()
