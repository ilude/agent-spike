"""Ingest a single YouTube video with transcript and tags into Qdrant cache."""

import asyncio
import sys
from pathlib import Path

# Add project root and lesson-001 to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))
sys.path.insert(0, str(project_root / "lessons" / "lesson-001"))

from youtube_agent.tools import get_transcript, extract_video_id
from youtube_agent.agent import create_agent
from tools.services.cache import create_qdrant_cache
from tools.services.archive import create_local_archive_writer
from tools.env_loader import load_root_env

load_root_env()


async def ingest_video(url: str, collection_name: str = "cached_content"):
    """Fetch transcript, generate tags, archive, and insert into Qdrant.

    Pipeline:
    1. Fetch transcript (expensive API call) -> Archive immediately
    2. Generate tags (expensive LLM call) -> Archive immediately
    3. Cache in Qdrant (derived data)

    Args:
        url: YouTube video URL
        collection_name: Qdrant collection name
    """
    print(f"\nProcessing video: {url}")

    # Initialize cache and archive
    cache = create_qdrant_cache(collection_name=collection_name)
    archive = create_local_archive_writer()  # Uses default projects/data/archive
    print(f"[OK] Connected to Qdrant collection: {collection_name}")

    # Extract video ID
    video_id = extract_video_id(url)
    cache_key = f"youtube:video:{video_id}"

    # Check if already archived
    if archive.exists(video_id):
        print(f"[INFO] Video already archived: {video_id}")
        existing_archive = archive.get(video_id)

        # Check if also in cache
        if cache.exists(cache_key):
            print(f"[INFO] Video also in cache - nothing to do")
            cached = cache.get(cache_key)
            if cached:
                print(f"   Transcript: {len(cached.get('transcript', ''))} chars")
                print(f"   Tags: {cached.get('tags', 'N/A')}")
            return cached
        else:
            print(f"[INFO] Archive exists but not in cache - will re-cache from archive")
            # We'll re-cache from archive data below

    # Fetch transcript (NOT using cache parameter to avoid caching twice)
    print(f"\n[1/5] Fetching transcript...")
    transcript = get_transcript(url, cache=None)

    if transcript.startswith("ERROR:"):
        print(f"[ERROR] {transcript}")
        return None

    print(f"[OK] Transcript fetched: {len(transcript)} characters")

    # Archive the transcript immediately (protect against rate limits)
    print(f"\n[2/5] Archiving transcript...")
    archive_path = archive.archive_youtube_video(
        video_id=video_id,
        url=url,
        transcript=transcript,
        metadata={"source": "youtube-transcript-api"},
    )
    print(f"[OK] Archived to: {archive_path}")

    # Generate tags using the agent
    print(f"\n[3/5] Generating tags with AI agent...")
    agent = create_agent(instrument=False)  # Disable instrumentation for this script

    result = await agent.run(
        f"Analyze this YouTube video transcript and generate 3-5 relevant tags. "
        f"Return ONLY the tags as a comma-separated list, nothing else.\n\n"
        f"Transcript:\n{transcript[:15000]}"  # Truncate to 15k chars
    )

    tags = result.output if hasattr(result, 'output') else str(result)
    tags = tags.strip()
    print(f"[OK] Tags generated: {tags}")

    # Archive the LLM output immediately (track cost)
    print(f"\n[4/5] Archiving LLM output...")
    archive.add_llm_output(
        video_id=video_id,
        output_type="tags",
        output_value=tags,
        model="claude-3-5-haiku-20241022",
        cost_usd=None,  # TODO: Extract from result metadata if available
    )
    print(f"[OK] Tags archived")

    # Prepare cache entry
    cache_data = {
        "video_id": video_id,
        "url": url,
        "transcript": transcript,
        "tags": tags,
        "transcript_length": len(transcript),
    }

    metadata = {
        "type": "youtube_video",
        "source": "youtube-transcript-api",
        "video_id": video_id,
        "tags": tags,
    }

    # Insert into Qdrant (derived data)
    print(f"\n[5/5] Inserting into Qdrant...")
    cache.set(cache_key, cache_data, metadata=metadata)
    print(f"[OK] Successfully cached with key: {cache_key}")

    # Add processing record to archive
    archive.add_processing_record(
        video_id=video_id,
        version="v1_full_embed",
        collection_name=collection_name,
        notes="Full transcript embedding",
    )

    # Verify insertion
    print(f"\n[VERIFY] Verifying cache entry...")
    retrieved = cache.get(cache_key)
    if retrieved:
        print(f"[OK] Cache verification successful")
        print(f"   Video ID: {retrieved.get('video_id')}")
        print(f"   Transcript: {len(retrieved.get('transcript', ''))} chars")
        print(f"   Tags: {retrieved.get('tags')}")
    else:
        print(f"[ERROR] Cache verification failed!")

    return cache_data


async def main():
    """Main entry point."""
    if len(sys.argv) < 2:
        print("Usage: python ingest_single_video.py <youtube_url> [collection_name]")
        print("\nExample:")
        print("  python ingest_single_video.py https://www.youtube.com/watch?v=MuP9ki6Bdtg")
        print("  python ingest_single_video.py https://www.youtube.com/watch?v=MuP9ki6Bdtg cached_content")
        sys.exit(1)

    url = sys.argv[1]
    collection_name = sys.argv[2] if len(sys.argv) > 2 else "cached_content"

    result = await ingest_video(url, collection_name)

    if result:
        print(f"\n[SUCCESS] Video cached and ready for use.")
    else:
        print(f"\n[FAILED] Failed to cache video.")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
