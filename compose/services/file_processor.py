"""File processing service for extracting text and indexing to Qdrant.

Handles uploaded project files:
- Text extraction via Docling (PDF, DOCX, etc.) or direct read (MD, TXT)
- Chunking for optimal embedding
- Vector embedding via Infinity
- Indexing to Qdrant with project metadata
"""

import os
import uuid
from pathlib import Path
from typing import Optional

import httpx
from qdrant_client import QdrantClient
from qdrant_client.models import PointStruct

# Configuration
DOCLING_URL = os.getenv("DOCLING_URL", "http://localhost:5001")
INFINITY_URL = os.getenv("INFINITY_URL", "http://localhost:7997")
INFINITY_MODEL = os.getenv("INFINITY_MODEL", "Alibaba-NLP/gte-large-en-v1.5")
QDRANT_URL = os.getenv("QDRANT_URL", "http://localhost:6335")
PROJECT_COLLECTION = os.getenv("PROJECT_COLLECTION", "project_files")

# Lazy clients
_qdrant_client: Optional[QdrantClient] = None


def get_qdrant_client() -> QdrantClient:
    """Get Qdrant client, creating it on first use."""
    global _qdrant_client
    if _qdrant_client is None:
        _qdrant_client = QdrantClient(url=QDRANT_URL)
    return _qdrant_client


async def get_embedding(text: str) -> list[float]:
    """Get embedding from Infinity service."""
    async with httpx.AsyncClient(timeout=60.0) as client:
        response = await client.post(
            f"{INFINITY_URL}/embeddings",
            json={"model": INFINITY_MODEL, "input": [text]}
        )
        response.raise_for_status()
        data = response.json()
        return data["data"][0]["embedding"]


def extract_text_from_file(file_path: Path, content_type: str) -> str:
    """Extract text content from a file.

    Args:
        file_path: Path to the file
        content_type: MIME type of the file

    Returns:
        Extracted text content
    """
    # Direct text file types
    text_types = {
        "text/plain",
        "text/markdown",
        "text/x-markdown",
        "application/json",
        "text/csv",
        "text/html",
        "text/xml",
    }

    # Code file extensions (read directly)
    code_extensions = {
        ".py", ".js", ".ts", ".jsx", ".tsx", ".java", ".c", ".cpp", ".h",
        ".go", ".rs", ".rb", ".php", ".swift", ".kt", ".scala", ".sh",
        ".yaml", ".yml", ".toml", ".ini", ".cfg", ".conf",
    }

    suffix = file_path.suffix.lower()

    # Direct read for text and code files
    if content_type in text_types or suffix in code_extensions:
        try:
            return file_path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            return file_path.read_text(encoding="latin-1")

    # Use Docling for documents (PDF, DOCX, etc.)
    if content_type in {
        "application/pdf",
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        "application/msword",
        "application/vnd.openxmlformats-officedocument.presentationml.presentation",
    } or suffix in {".pdf", ".docx", ".doc", ".pptx"}:
        return extract_with_docling(file_path)

    # Fallback: try to read as text
    try:
        return file_path.read_text(encoding="utf-8")
    except (UnicodeDecodeError, Exception):
        return f"[Unable to extract text from {content_type} file]"


def extract_with_docling(file_path: Path) -> str:
    """Extract text from document using Docling.

    Args:
        file_path: Path to the document file

    Returns:
        Extracted markdown content
    """
    try:
        # Read file as bytes
        file_bytes = file_path.read_bytes()

        # Send to Docling convert endpoint
        with httpx.Client(timeout=60.0) as client:
            response = client.post(
                f"{DOCLING_URL}/v1/convert/file",
                files={"file": (file_path.name, file_bytes)},
            )
            response.raise_for_status()

            data = response.json()

            if data.get("status") != "success":
                errors = data.get("errors", [])
                return f"[Docling extraction failed: {errors}]"

            return data["document"]["md_content"]

    except httpx.ConnectError:
        return "[Cannot connect to Docling service - ensure docling-serve is running]"
    except httpx.TimeoutException:
        return "[Docling conversion timeout]"
    except Exception as e:
        return f"[Docling extraction error: {e}]"


def chunk_text(text: str, chunk_size: int = 1000, overlap: int = 200) -> list[str]:
    """Split text into overlapping chunks for embedding.

    Args:
        text: Text to chunk
        chunk_size: Target size of each chunk
        overlap: Number of characters to overlap between chunks

    Returns:
        List of text chunks
    """
    if len(text) <= chunk_size:
        return [text]

    chunks = []
    start = 0

    while start < len(text):
        end = start + chunk_size

        # Try to break at sentence/paragraph boundary
        if end < len(text):
            # Look for paragraph break
            para_break = text.rfind("\n\n", start, end)
            if para_break > start + chunk_size // 2:
                end = para_break + 2
            else:
                # Look for sentence break
                sent_break = text.rfind(". ", start, end)
                if sent_break > start + chunk_size // 2:
                    end = sent_break + 2

        chunks.append(text[start:end].strip())
        start = end - overlap

    return [c for c in chunks if c]  # Filter empty chunks


async def process_and_index_file(
    project_id: str,
    file_id: str,
    file_path: Path,
    filename: str,
    content_type: str,
) -> dict:
    """Process a file and index its contents to Qdrant.

    Args:
        project_id: Project the file belongs to
        file_id: Unique file identifier
        file_path: Path to the file on disk
        filename: Original filename
        content_type: MIME type

    Returns:
        Processing result with status and details
    """
    try:
        # Extract text
        text = extract_text_from_file(file_path, content_type)

        if text.startswith("[") and text.endswith("]"):
            # Extraction error
            return {
                "success": False,
                "error": text[1:-1],
                "chunks_indexed": 0,
            }

        if len(text.strip()) < 50:
            return {
                "success": False,
                "error": "Insufficient text content extracted",
                "chunks_indexed": 0,
            }

        # Chunk text
        chunks = chunk_text(text)

        # Ensure collection exists
        qdrant = get_qdrant_client()
        try:
            qdrant.get_collection(PROJECT_COLLECTION)
        except Exception:
            # Create collection if it doesn't exist
            # Get vector size from a test embedding
            test_embedding = await get_embedding("test")
            from qdrant_client.models import Distance, VectorParams
            qdrant.create_collection(
                collection_name=PROJECT_COLLECTION,
                vectors_config=VectorParams(
                    size=len(test_embedding),
                    distance=Distance.COSINE,
                ),
            )

        # Index each chunk
        points = []
        for i, chunk in enumerate(chunks):
            embedding = await get_embedding(chunk)

            point_id = str(uuid.uuid4())
            points.append(
                PointStruct(
                    id=point_id,
                    vector=embedding,
                    payload={
                        "project_id": project_id,
                        "file_id": file_id,
                        "filename": filename,
                        "content_type": content_type,
                        "chunk_index": i,
                        "total_chunks": len(chunks),
                        "text": chunk,
                    },
                )
            )

        # Batch upsert to Qdrant
        if points:
            qdrant.upsert(collection_name=PROJECT_COLLECTION, points=points)

        return {
            "success": True,
            "chunks_indexed": len(points),
            "total_chars": len(text),
        }

    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "chunks_indexed": 0,
        }


async def search_project_files(
    project_id: str,
    query: str,
    limit: int = 5,
) -> list[dict]:
    """Search project files using semantic search.

    Args:
        project_id: Project to search within
        query: Search query
        limit: Max results to return

    Returns:
        List of matching chunks with metadata
    """
    try:
        query_embedding = await get_embedding(query)

        qdrant = get_qdrant_client()
        results = qdrant.query_points(
            collection_name=PROJECT_COLLECTION,
            query=query_embedding,
            query_filter={
                "must": [
                    {"key": "project_id", "match": {"value": project_id}}
                ]
            },
            limit=limit,
        )

        return [
            {
                "score": r.score,
                "text": r.payload.get("text", ""),
                "filename": r.payload.get("filename", ""),
                "file_id": r.payload.get("file_id", ""),
                "chunk_index": r.payload.get("chunk_index", 0),
            }
            for r in results.points
        ]

    except Exception as e:
        print(f"Project file search error: {e}")
        return []


def delete_file_from_index(project_id: str, file_id: str) -> bool:
    """Remove all indexed chunks for a file.

    Args:
        project_id: Project ID
        file_id: File ID to remove

    Returns:
        True if successful
    """
    try:
        qdrant = get_qdrant_client()
        qdrant.delete(
            collection_name=PROJECT_COLLECTION,
            points_selector={
                "filter": {
                    "must": [
                        {"key": "project_id", "match": {"value": project_id}},
                        {"key": "file_id", "match": {"value": file_id}},
                    ]
                }
            },
        )
        return True
    except Exception as e:
        print(f"Failed to delete file from index: {e}")
        return False
