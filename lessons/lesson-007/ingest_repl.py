"""Interactive REPL for ingesting YouTube videos without needing to quote URLs."""

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
from tools.env_loader import load_root_env

load_root_env()


async def ingest_video(url: str, cache) -> dict | None:
    """Fetch transcript, generate tags, and insert into Qdrant.

    Args:
        url: YouTube video URL
        cache instance

    Returns:
        Cache data dict or None if failed
    """
    try:
        # Extract video ID
        video_id = extract_video_id(url)
        cache_key = f"youtube:video:{video_id}"

        # Check if already cached
        if cache.exists(cache_key):
            print(f"[CACHED] Video already exists (ID: {video_id})")
            existing = cache.get(cache_key)
            if existing:
                print(f"  Transcript: {len(existing.get('transcript', ''))} chars")
                print(f"  Tags: {existing.get('tags', 'N/A')}")
            return existing

        # Fetch transcript
        print(f"[1/3] Fetching transcript for video ID: {video_id}...")
        transcript = get_transcript(url, cache=None)

        if transcript.startswith("ERROR:"):
            print(f"[ERROR] {transcript}")
            return None

        print(f"[OK] Transcript fetched: {len(transcript)} characters")

        # Generate tags using the agent
        print(f"[2/3] Generating tags with AI agent...")
        agent = create_agent(instrument=False)

        result = await agent.run(
            f"Analyze this YouTube video transcript and generate 3-5 relevant tags. "
            f"Return ONLY the tags as a comma-separated list, nothing else.\n\n"
            f"Transcript:\n{transcript[:15000]}"
        )

        tags = result.output if hasattr(result, 'output') else str(result)
        tags = tags.strip()
        print(f"[OK] Tags: {tags}")

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

        # Insert into Qdrant
        print(f"[3/3] Inserting into Qdrant...")
        cache.set(cache_key, cache_data, metadata=metadata)
        print(f"[SUCCESS] Cached with key: {cache_key}")

        return cache_data

    except ValueError as e:
        print(f"[ERROR] Invalid URL: {e}")
        return None
    except Exception as e:
        print(f"[ERROR] Failed to process video: {e}")
        return None


async def repl(collection_name: str = "cached_content"):
    """Run interactive REPL for ingesting videos.

    Args:
        collection_name: Qdrant collection name
    """
    print("=" * 80)
    print("YouTube Video Ingestion REPL")
    print("=" * 80)
    print(f"Collection: {collection_name}")
    print()
    print("Commands:")
    print("  - Paste any YouTube URL (no quotes needed)")
    print("  - 'list' - Show all cached videos")
    print("  - 'count' - Show total cached videos")
    print("  - 'quit' or 'exit' - Exit the REPL")
    print("  - 'help' - Show this help message")
    print("=" * 80)
    print()

    # Initialize cache once
    cache = create_qdrant_cache(collection_name=collection_name)
    print(f"[OK] Connected to Qdrant collection: {collection_name}\n")

    while True:
        try:
            # Get input
            user_input = input(">> ").strip()

            if not user_input:
                continue

            # Handle commands
            if user_input.lower() in ['quit', 'exit', 'q']:
                print("\nGoodbye!")
                break

            elif user_input.lower() == 'help':
                print("\nCommands:")
                print("  - Paste any YouTube URL (no quotes needed)")
                print("  - 'list' - Show all cached videos")
                print("  - 'count' - Show total cached videos")
                print("  - 'quit' or 'exit' - Exit the REPL")
                print("  - 'help' - Show this help message")
                print()

            elif user_input.lower() == 'list':
                print("\nFetching cached videos...")
                videos = cache.filter({"type": "youtube_video"}, limit=100)
                if videos:
                    print(f"\nFound {len(videos)} cached videos:")
                    for i, video in enumerate(videos, 1):
                        video_id = video.get('video_id', 'N/A')
                        transcript_len = video.get('transcript_length', 0)
                        tags = video.get('tags', 'N/A')
                        print(f"\n{i}. Video ID: {video_id}")
                        print(f"   Transcript: {transcript_len:,} chars")
                        print(f"   Tags: {tags}")
                else:
                    print("\n[INFO] No videos found in cache.")
                print()

            elif user_input.lower() == 'count':
                videos = cache.filter({"type": "youtube_video"}, limit=1000)
                print(f"\nTotal cached videos: {len(videos)}\n")

            elif user_input.startswith('http'):
                # Assume it's a YouTube URL
                print(f"\nProcessing: {user_input}")
                result = await ingest_video(user_input, cache)
                if result:
                    print()
                else:
                    print("[FAILED] Could not process video.\n")

            else:
                print(f"[ERROR] Unknown command or invalid URL: {user_input}")
                print("Type 'help' for available commands.\n")

        except KeyboardInterrupt:
            print("\n\nInterrupted. Type 'quit' to exit.\n")
            continue
        except EOFError:
            print("\n\nGoodbye!")
            break
        except Exception as e:
            print(f"[ERROR] Unexpected error: {e}\n")
            continue


def main():
    """Main entry point."""
    collection_name = sys.argv[1] if len(sys.argv) > 1 else "cached_content"

    print("\nStarting YouTube Video Ingestion REPL...")
    print(f"Collection: {collection_name}\n")

    asyncio.run(repl(collection_name))


if __name__ == "__main__":
    main()
