"""Dead simple batch CSV ingestion - NO REPL, NO ASYNC, JUST A LOOP."""

import csv
import sys
from pathlib import Path

# Setup environment
from compose.cli.base import setup_script_environment
setup_script_environment(needs_agent=True)

# Imports
from compose.services.youtube import get_transcript, extract_video_id
from compose.services.cache import create_qdrant_cache
from compose.services.archive import create_local_archive_writer, ImportMetadata, ChannelContext
from youtube_agent.agent import create_agent
from datetime import datetime
import asyncio

print("[OK] Imports complete\n")

def main():
    if len(sys.argv) < 2:
        print("Usage: python simple_batch_ingest.py <csv_file>")
        sys.exit(1)

    csv_path = Path(sys.argv[1])
    collection_name = "cached_content"

    print(f"CSV: {csv_path}")
    print(f"Collection: {collection_name}\n")

    # Read CSV
    with open(csv_path, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        videos = list(reader)

    print(f"Found {len(videos)} videos\n")

    # Setup services
    cache = create_qdrant_cache(
        collection_name=collection_name,
        qdrant_url="http://localhost:6335",
        infinity_url="http://localhost:7997"
    )
    archive = create_local_archive_writer()

    processed = 0
    skipped = 0
    errors = 0

    for i, video in enumerate(videos, 1):
        url = video['url']
        title = video.get('title', 'N/A')[:60]

        print(f"[{i}/{len(videos)}] {title}")
        print(f"  URL: {url}")

        try:
            video_id = extract_video_id(url)
            cache_key = f"youtube:video:{video_id}"

            # Check cache
            if cache.exists(cache_key):
                print(f"  SKIPPED - Already cached\n")
                skipped += 1
                continue

            # Fetch transcript
            print(f"  [1/3] Fetching transcript...")
            transcript = get_transcript(url, cache=None)

            if "ERROR:" in transcript:
                print(f"  ERROR - {transcript}\n")
                errors += 1
                continue

            # Archive
            import_metadata = ImportMetadata(
                source_type="bulk_channel",
                imported_at=datetime.now(),
                import_method="cli",
                channel_context=ChannelContext(
                    channel_id=None,
                    channel_name=None,
                    is_bulk_import=True,
                ),
                recommendation_weight=0.5,
            )

            archive.archive_youtube_video(
                video_id=video_id,
                url=url,
                transcript=transcript,
                metadata={"source": "youtube-transcript-api"},
                import_metadata=import_metadata,
            )

            # Generate tags
            print(f"  [2/3] Generating tags ({len(transcript)} chars)...")
            agent = create_agent(instrument=False)

            result = asyncio.run(agent.run(
                f"Analyze this YouTube video transcript and generate 3-5 relevant tags. "
                f"Return ONLY the tags as a comma-separated list, nothing else.\n\n"
                f"Transcript:\n{transcript[:15000]}"
            ))

            tags = result.output if hasattr(result, 'output') else str(result)
            tags = tags.strip()

            # Archive LLM output
            archive.add_llm_output(
                video_id=video_id,
                output_type="tags",
                output_value=tags,
                model="claude-3-5-haiku-20241022",
                cost_usd=0.001,
            )

            # Cache
            print(f"  [3/3] Caching...")
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
                "source_type": "bulk_channel",
                "recommendation_weight": 0.5,
                "imported_at": datetime.now().isoformat(),
                "is_bulk_import": True,
            }

            cache.set(cache_key, cache_data, metadata=metadata)

            print(f"  SUCCESS - {tags[:50]}...\n")
            processed += 1

        except Exception as e:
            print(f"  ERROR - {type(e).__name__}: {e}\n")
            errors += 1

    cache.close()

    print(f"\n{'='*70}")
    print(f"COMPLETE: {processed} processed, {skipped} skipped, {errors} errors")
    print(f"{'='*70}")

if __name__ == "__main__":
    main()
