#!/usr/bin/env python
"""Ingest a single YouTube video with transcript and tags.

This script fetches a video transcript, generates tags, and stores everything
in both the archive (JSON) and SurrealDB for fast retrieval.

Supports two embedding modes:
- Global only (default): One embedding per video for recommendations
- With chunks (--chunks): Global + chunk embeddings for timestamp-level search

Usage:
    # Single video (global embedding only)
    uv run python compose/cli/ingest_video.py "https://youtube.com/watch?v=..."

    # With chunk embeddings (for timestamp search)
    uv run python compose/cli/ingest_video.py "https://youtube.com/watch?v=..." --chunks

    # Just show what would be done (dry run)
    uv run python compose/cli/ingest_video.py "https://youtube.com/watch?v=..." --dry-run
"""

import asyncio
import sys
from pathlib import Path
from datetime import datetime

# Setup script environment - add project root to path
project_root = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(project_root))
from compose.cli.base import setup_script_environment
setup_script_environment(needs_agent=True)

# Import from centralized services
from compose.services.youtube import get_transcript, get_timed_transcript, extract_video_id, fetch_video_metadata
from compose.services.chunking import chunk_youtube_transcript
from compose.services.archive import create_archive_manager, ImportMetadata, ChannelContext
from compose.services.embeddings import get_global_embedder, get_chunk_embedder
from compose.services.surrealdb import repository
from compose.services.surrealdb.models import VideoRecord, VideoChunkRecord

# Import agent from lesson (still experimental)
from youtube_agent.agent import create_agent


async def ingest_single_video(
    url: str,
    dry_run: bool = False,
    use_chunks: bool = False,
) -> tuple[bool, str]:
    """Ingest a single YouTube video.

    Pipeline:
    1. Check if already in SurrealDB (skip if exists with embedding)
    2. Fetch transcript -> Archive immediately
    3. Generate tags (LLM) -> Archive immediately
    4. Store in SurrealDB with embeddings (global + optional chunks)

    Args:
        url: YouTube video URL
        dry_run: If True, only show what would be done
        use_chunks: If True, also create chunk embeddings for timestamp search

    Returns:
        Tuple of (success: bool, message: str)
    """
    try:
        # Extract video ID
        video_id = extract_video_id(url)

        print(f"\n{'='*70}")
        print(f"Ingesting Video")
        print(f"{'='*70}")
        print(f"Video ID: {video_id}")
        print(f"URL: {url}")
        print(f"Store: SurrealDB")
        print(f"Chunk Embeddings: {use_chunks}")
        print(f"Dry Run: {dry_run}")
        print(f"{'='*70}\n")

        # Initialize services
        archive = create_archive_manager()
        global_embedder = get_global_embedder()
        chunk_embedder = get_chunk_embedder() if use_chunks else None

        # Initialize SurrealDB schema
        await repository.init_schema()

        # Check if already exists with embedding
        print("[1/6] Checking SurrealDB...")
        existing = await repository.get_video(video_id)
        if existing and existing.embedding:
            print(f"  [SKIP] Video already indexed: {video_id}\n")
            print(f"  Title: {existing.title or 'N/A'}")
            print(f"  Channel: {existing.channel_name or 'N/A'}")
            if use_chunks:
                chunk_count = await repository.get_chunk_count()
                print(f"  Chunks: {chunk_count}")
            return True, "Already indexed"

        print(f"  [OK] Video needs indexing, proceeding...\n")

        # Fetch transcript (both plain and timed for chunking)
        print("[2/6] Fetching transcript (via Webshare proxy)...")
        transcript = get_transcript(url, cache=None)

        if "ERROR:" in transcript:
            return False, f"Transcript fetch failed: {transcript}"

        # Also fetch timed transcript for chunking
        timed_transcript, timed_error = get_timed_transcript(url)
        if timed_error:
            print(f"  [WARN] Timed transcript failed: {timed_error}")
            print(f"  [WARN] Continuing with plain transcript only...")
            timed_transcript = None
        else:
            print(f"  [OK] Fetched {len(timed_transcript):,} timed segments")

        print(f"  [OK] Fetched {len(transcript):,} characters total\n")

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
            print(f"  Archive path: compose/data/archive/YYYY-MM/{video_id}.json")
            print(f"  SurrealDB: video:{video_id}")
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

        # Use Archive Manager to handle transcript (including timed for chunking)
        archive.update_transcript(
            video_id=video_id,
            url=url,
            transcript=transcript,
            timed_transcript=timed_transcript,
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

        # Store in SurrealDB with embedding
        print("[6/6] Storing in SurrealDB with embeddings...")

        # Generate global embedding from transcript summary + metadata
        # Include video ID, channel, title, summary, and subject tags for better search
        channel_name = youtube_metadata.get("channel_title", "")
        title = youtube_metadata.get("title") or tags_data.get("title", "")
        summary = tags_data.get("summary", "")
        subjects = " ".join(tags_data.get("subject_matter", []))

        summary_text = f"Video ID: {video_id}\nChannel: {channel_name}\nTitle: {title}\nSummary: {summary}\nTopics: {subjects}"
        global_embedding = global_embedder.embed(summary_text)
        print(f"  [OK] Generated global embedding ({len(global_embedding)} dims)")

        # Create video record
        video_record = VideoRecord(
            video_id=video_id,
            url=url,
            fetched_at=datetime.now(),
            title=youtube_metadata.get("title") or tags_data.get("title"),
            channel_id=youtube_metadata.get("channel_id"),
            channel_name=youtube_metadata.get("channel_title"),
            duration_seconds=youtube_metadata.get("duration_seconds"),
            view_count=youtube_metadata.get("view_count"),
            published_at=datetime.fromisoformat(youtube_metadata["published_at"]) if youtube_metadata.get("published_at") else None,
            source_type="single_import",
            import_method="cli",
            recommendation_weight=1.0,
            embedding=global_embedding,
            archive_path=str(archive.writer.config.base_dir),
            last_processed_at=datetime.now(),
        )

        await repository.upsert_video(video_record)
        print(f"  [OK] Stored video record")

        # Link to channel if available
        if youtube_metadata.get("channel_id"):
            await repository.link_video_to_channel(
                video_id=video_id,
                channel_id=youtube_metadata["channel_id"],
                channel_name=youtube_metadata.get("channel_title", "Unknown"),
            )
            print(f"  [OK] Linked to channel: {youtube_metadata.get('channel_title')}")

        # Link to topics/subjects
        subjects = tags_data.get("subject_matter", [])
        if subjects:
            await repository.link_video_to_topics(video_id, subjects)
            print(f"  [OK] Linked to {len(subjects)} topics")

        # Store chunks if requested
        chunks_stored = 0
        if use_chunks and timed_transcript and chunk_embedder:
            chunk_result = chunk_youtube_transcript(timed_transcript, video_id=video_id)
            print(f"  [OK] Created {len(chunk_result.chunks)} chunks")

            # Delete existing chunks first
            await repository.delete_chunks_for_video(video_id)

            # Create chunk records with embeddings
            chunk_records = []
            for chunk in chunk_result.chunks:
                chunk_embedding = chunk_embedder.embed(chunk.text)
                chunk_records.append(VideoChunkRecord(
                    chunk_id=f"{video_id}:{chunk.chunk_index}",
                    video_id=video_id,
                    chunk_index=chunk.chunk_index,
                    text=chunk.text,
                    start_time=chunk.start_time,
                    end_time=chunk.end_time,
                    token_count=chunk.token_count,
                    embedding=chunk_embedding,
                ))

            chunks_stored = await repository.upsert_chunks(chunk_records)
            print(f"  [OK] Stored {chunks_stored} chunks with embeddings")

        print(f"\n{'='*70}")
        print(f"SUCCESS!")
        print(f"{'='*70}")
        print(f"Video ID: {video_id}")
        print(f"Transcript: {len(transcript):,} characters")
        print(f"Title: {tags_data.get('title', 'N/A')}")
        print(f"Summary: {tags_data.get('summary', 'N/A')}")
        print(f"Subject Matter: {', '.join(tags_data.get('subject_matter', [])[:5])}")
        print(f"Content Style: {tags_data.get('content_style', 'N/A')}")
        print(f"Archive: {archive.writer.config.base_dir}")
        print(f"Store: SurrealDB (video:{video_id})")
        if use_chunks:
            print(f"Chunks: {chunks_stored}")
        print(f"{'='*70}\n")

        return True, f"Ingested {video_id} successfully"

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
            print("  uv run python compose/cli/ingest_video.py <url> [--dry-run] [--chunks]")
            print()
            print("Options:")
            print("  --dry-run, -n    Show what would be done without making changes")
            print("  --chunks         Also create chunk embeddings for timestamp search")
            print()
            print("Examples:")
            print("  uv run python compose/cli/ingest_video.py 'https://youtube.com/watch?v=dQw4w9WgXcQ'")
            print("  uv run python compose/cli/ingest_video.py 'https://youtube.com/watch?v=dQw4w9WgXcQ' --chunks")
            print("  uv run python compose/cli/ingest_video.py 'https://youtube.com/watch?v=dQw4w9WgXcQ' --dry-run")
            sys.exit(1)

        url = sys.argv[1]

        # Check for flags
        dry_run = "--dry-run" in sys.argv or "-n" in sys.argv
        use_chunks = "--chunks" in sys.argv

        success, message = await ingest_single_video(url, dry_run, use_chunks)

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
