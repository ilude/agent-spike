#!/usr/bin/env python
"""Generate embeddings for video transcripts via Infinity.

Loads transcripts from archive, generates embeddings, and saves for clustering.
"""

import json
import os
import sys
from datetime import datetime
from pathlib import Path

# Add project root to path for imports
PROJECT_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from compose.services.embeddings import EmbeddingService

OUTPUT_DIR = Path(__file__).parent / "output"
ARCHIVE_DIR = PROJECT_ROOT / "compose/data/archive/youtube"

# Infinity URL from environment or default to GPU server
INFINITY_URL = os.getenv("INFINITY_URL", "http://192.168.16.241:7997")

# Batch size for embedding generation
BATCH_SIZE = 10

# Max transcript length (truncate longer transcripts)
MAX_TRANSCRIPT_LENGTH = 8000  # characters


def load_ready_videos() -> list[dict]:
    """Load list of videos that are ready (have transcripts in archive)."""
    ready_file = OUTPUT_DIR / "videos_ready.json"
    if not ready_file.exists():
        print("No videos_ready.json found. Run merge_video_ids.py first.")
        return []

    with open(ready_file) as f:
        data = json.load(f)

    return data.get("videos", [])


def load_transcript_from_archive(video_id: str) -> str | None:
    """Load transcript from archive for a video."""
    # Search in all month directories
    for month_dir in ARCHIVE_DIR.iterdir():
        if month_dir.is_dir():
            archive_file = month_dir / f"{video_id}.json"
            if archive_file.exists():
                try:
                    with open(archive_file, encoding="utf-8") as f:
                        data = json.load(f)
                        return data.get("raw_transcript")
                except (UnicodeDecodeError, json.JSONDecodeError) as e:
                    print(f"Warning: Failed to load {video_id}: {e}")
                    return None
    return None


def truncate_transcript(transcript: str, max_length: int = MAX_TRANSCRIPT_LENGTH) -> str:
    """Truncate transcript to max length, preferring to cut at sentence boundaries."""
    if len(transcript) <= max_length:
        return transcript

    # Try to cut at a sentence boundary
    truncated = transcript[:max_length]
    last_period = truncated.rfind(". ")
    if last_period > max_length * 0.8:  # Only if we're not losing too much
        return truncated[:last_period + 1]

    return truncated


def main():
    """Generate embeddings for video transcripts."""
    OUTPUT_DIR.mkdir(exist_ok=True)

    # Load ready videos
    videos = load_ready_videos()
    if not videos:
        return

    print(f"Videos to process: {len(videos)}")
    print(f"Infinity URL: {INFINITY_URL}")

    # Initialize embedding service
    try:
        embedder = EmbeddingService(
            infinity_url=INFINITY_URL,
            model="Alibaba-NLP/gte-large-en-v1.5",  # Good for document-level
            timeout=120.0,
        )
        # Test connection
        test_embedding = embedder.embed("test")
        print(f"Embedding dimension: {len(test_embedding)}")
    except Exception as e:
        print(f"Failed to connect to Infinity: {e}")
        print("Make sure Infinity service is running on the GPU server.")
        return

    # Process videos
    results = []
    failed = []
    skipped = []

    for i, video in enumerate(videos):
        video_id = video["video_id"]

        # Load transcript
        transcript = load_transcript_from_archive(video_id)
        if not transcript:
            skipped.append(video_id)
            continue

        # Truncate if needed
        transcript = truncate_transcript(transcript)

        try:
            embedding = embedder.embed(transcript)
            results.append({
                "video_id": video_id,
                "title": video.get("title", ""),
                "source": video.get("source", ""),
                "embedding": embedding,
                "transcript_length": len(transcript),
            })

            if (i + 1) % 50 == 0:
                print(f"Progress: {i + 1}/{len(videos)} ({len(results)} embedded, {len(skipped)} skipped)")

        except Exception as e:
            print(f"Failed to embed {video_id}: {e}")
            failed.append(video_id)

    print(f"\nCompleted!")
    print(f"  Embedded: {len(results)}")
    print(f"  Skipped (no transcript): {len(skipped)}")
    print(f"  Failed: {len(failed)}")

    # Save embeddings
    output_file = OUTPUT_DIR / "video_embeddings.json"
    with open(output_file, "w") as f:
        json.dump({
            "generated_at": datetime.now().isoformat(),
            "model": "Alibaba-NLP/gte-large-en-v1.5",
            "embedding_dim": len(results[0]["embedding"]) if results else 0,
            "count": len(results),
            "videos": results,
        }, f)  # Don't pretty-print, embeddings are large

    print(f"\nSaved to: {output_file}")
    print(f"File size: {output_file.stat().st_size / 1024 / 1024:.1f} MB")

    # Also save a lightweight version without embeddings for reference
    metadata_file = OUTPUT_DIR / "video_metadata.json"
    with open(metadata_file, "w") as f:
        json.dump({
            "generated_at": datetime.now().isoformat(),
            "count": len(results),
            "videos": [
                {
                    "video_id": v["video_id"],
                    "title": v["title"],
                    "source": v["source"],
                    "transcript_length": v["transcript_length"],
                }
                for v in results
            ],
        }, f, indent=2)

    print(f"Metadata saved to: {metadata_file}")


if __name__ == "__main__":
    main()
