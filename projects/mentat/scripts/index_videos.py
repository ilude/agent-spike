"""
Index YouTube video transcripts into Qdrant for RAG.

Reads archived JSON files, chunks transcripts, embeds with OpenAI,
and uploads to Qdrant collection 'mentat_video_chunks'.
"""

import json
import os
import sys
import uuid
from pathlib import Path
from typing import Any

import tiktoken
from openai import OpenAI
from qdrant_client import QdrantClient
from qdrant_client.models import Distance, PointStruct, VectorParams

# Add project root to path for imports
project_root = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(project_root))

# Load environment from root .env
from dotenv import load_dotenv

env_path = project_root / ".env"
load_dotenv(env_path)

# Configuration
COLLECTION_NAME = "mentat_video_chunks"
EMBEDDING_MODEL = "text-embedding-3-small"
EMBEDDING_DIM = 1536
CHUNK_SIZE = 500  # tokens
CHUNK_OVERLAP = 100  # tokens
ARCHIVE_DIR = project_root / "projects" / "data" / "archive" / "youtube" / "2025-11"
QDRANT_URL = "http://localhost:6333"

# Initialize clients
openai_client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
qdrant_client = QdrantClient(url=QDRANT_URL)
tokenizer = tiktoken.encoding_for_model("gpt-4")


def chunk_text(text: str, chunk_size: int, overlap: int) -> list[str]:
    """Chunk text into overlapping segments by token count."""
    tokens = tokenizer.encode(text)
    chunks = []

    start = 0
    while start < len(tokens):
        end = start + chunk_size
        chunk_tokens = tokens[start:end]
        decoded_chunk = tokenizer.decode(chunk_tokens)
        chunks.append(decoded_chunk)

        # Move start forward by (chunk_size - overlap)
        start += chunk_size - overlap

        # Break if we're past the end
        if end >= len(tokens):
            break

    return chunks


def chunk_timed_transcript(
    timed_transcript: list[dict], chunk_size: int, overlap: int
) -> list[dict]:
    """Chunk timed transcript into overlapping segments by token count.

    Returns list of dicts with:
    - text: chunk text
    - start_time: timestamp in seconds for the start of this chunk
    - segments: list of timed segments in this chunk
    """
    # Build full text and track char positions for each segment
    full_text = ""
    segment_positions = []  # [(start_char, end_char, start_time), ...]

    for segment in timed_transcript:
        start_char = len(full_text)
        segment_text = segment["text"]
        full_text += segment_text + " "
        end_char = len(full_text) - 1  # Exclude the space
        segment_positions.append((start_char, end_char, segment["start"]))

    # Tokenize and chunk
    tokens = tokenizer.encode(full_text)
    chunks = []

    start_token = 0
    while start_token < len(tokens):
        end_token = start_token + chunk_size
        chunk_tokens = tokens[start_token:end_token]
        chunk_text = tokenizer.decode(chunk_tokens)

        # Find the first segment that overlaps with this chunk
        # We'll use the start time of the first segment as the chunk timestamp
        chunk_start_time = None
        for start_char, end_char, segment_start_time in segment_positions:
            # Check if this segment's text appears in the chunk
            if chunk_text.find(full_text[start_char:min(end_char + 1, len(full_text))]) >= 0:
                chunk_start_time = segment_start_time
                break

        chunks.append({
            "text": chunk_text,
            "start_time": chunk_start_time,  # May be None if no match found
        })

        # Move start forward
        start_token += chunk_size - overlap

        if end_token >= len(tokens):
            break

    return chunks


def parse_video_json(file_path: Path) -> dict[str, Any] | None:
    """Parse video JSON and extract relevant fields."""
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        # Extract LLM tags/summary
        title = "Untitled"
        tags = []
        summary = ""

        if "llm_outputs" in data and len(data["llm_outputs"]) > 0:
            llm_output = data["llm_outputs"][0]
            output_value = json.loads(llm_output.get("output_value", "{}"))
            title = output_value.get("video_title", title)
            tags = output_value.get("tags", [])
            summary = output_value.get("summary", "")

        return {
            "video_id": data["video_id"],
            "url": data["url"],
            "transcript": data["raw_transcript"],
            "timed_transcript": data.get("timed_transcript"),  # May be None for old archives
            "title": title,
            "tags": tags,
            "summary": summary,
        }
    except Exception as e:
        print(f"Error parsing {file_path}: {e}")
        return None


def embed_texts(texts: list[str]) -> list[list[float]]:
    """Embed texts using OpenAI API."""
    response = openai_client.embeddings.create(
        model=EMBEDDING_MODEL,
        input=texts,
    )
    return [item.embedding for item in response.data]


def create_collection():
    """Create Qdrant collection if it doesn't exist."""
    collections = qdrant_client.get_collections().collections
    collection_names = [c.name for c in collections]

    if COLLECTION_NAME not in collection_names:
        print(f"Creating collection '{COLLECTION_NAME}'...")
        qdrant_client.create_collection(
            collection_name=COLLECTION_NAME,
            vectors_config=VectorParams(size=EMBEDDING_DIM, distance=Distance.COSINE),
        )
        print(f"[OK] Collection '{COLLECTION_NAME}' created")
    else:
        print(f"[OK] Collection '{COLLECTION_NAME}' already exists")


def index_videos():
    """Main indexing function."""
    print(f"Indexing videos from {ARCHIVE_DIR}")

    # Create collection
    create_collection()

    # Get all JSON files
    json_files = list(ARCHIVE_DIR.glob("*.json"))
    print(f"Found {len(json_files)} video files")

    total_chunks = 0
    batch_size = 50  # Embed in batches

    for i, json_file in enumerate(json_files, 1):
        print(f"\n[{i}/{len(json_files)}] Processing {json_file.name}...")

        # Parse video
        video_data = parse_video_json(json_file)
        if not video_data:
            continue

        # Chunk transcript (use timed version if available)
        if video_data.get("timed_transcript"):
            print("  > Using timed transcript")
            chunk_data = chunk_timed_transcript(
                video_data["timed_transcript"],
                CHUNK_SIZE,
                CHUNK_OVERLAP,
            )
            chunks = [c["text"] for c in chunk_data]
            chunk_timestamps = [c["start_time"] for c in chunk_data]
        else:
            print("  > Using plain text transcript (no timestamps)")
            chunks = chunk_text(
                video_data["transcript"],
                CHUNK_SIZE,
                CHUNK_OVERLAP,
            )
            chunk_timestamps = [None] * len(chunks)

        print(f"  > {len(chunks)} chunks")

        # Embed chunks in batches
        embeddings = []
        for batch_start in range(0, len(chunks), batch_size):
            batch_end = min(batch_start + batch_size, len(chunks))
            batch_chunks = chunks[batch_start:batch_end]
            batch_embeddings = embed_texts(batch_chunks)
            embeddings.extend(batch_embeddings)
            print(f"  > Embedded chunks {batch_start+1}-{batch_end}")

        # Create points
        points = []
        for chunk_idx, (chunk_content, embedding, timestamp) in enumerate(zip(chunks, embeddings, chunk_timestamps)):
            # Generate UUID from video_id + chunk_idx for deterministic IDs
            point_id = str(uuid.uuid5(uuid.NAMESPACE_DNS, f"{video_data['video_id']}_{chunk_idx}"))

            payload = {
                "video_id": video_data["video_id"],
                "chunk_index": chunk_idx,
                "text": chunk_content,
                "video_title": video_data["title"],
                "tags": video_data["tags"],
                "summary": video_data["summary"],
                "url": video_data["url"],
                "total_chunks": len(chunks),
            }

            # Add timestamp if available
            if timestamp is not None:
                payload["start_time"] = timestamp

            point = PointStruct(
                id=point_id,
                vector=embedding,
                payload=payload,
            )
            points.append(point)

        # Upsert to Qdrant
        qdrant_client.upsert(
            collection_name=COLLECTION_NAME,
            points=points,
        )
        print(f"  [OK] Uploaded {len(points)} chunks")
        total_chunks += len(points)

    print(f"\n{'='*50}")
    print(f"[OK] Indexing complete!")
    print(f"  Total videos: {len(json_files)}")
    print(f"  Total chunks: {total_chunks}")
    print(f"  Collection: {COLLECTION_NAME}")


if __name__ == "__main__":
    index_videos()
