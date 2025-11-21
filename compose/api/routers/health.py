"""Health check endpoints."""

import os

import httpx
from fastapi import APIRouter
from qdrant_client import QdrantClient

from compose.api.models import HealthCheckResponse

router = APIRouter(tags=["health"])

# Service URLs (container networking)
QDRANT_URL = os.getenv("QDRANT_URL", "http://localhost:6335")
INFINITY_URL = os.getenv("INFINITY_URL", "http://localhost:7997")


@router.get("/health", response_model=HealthCheckResponse)
async def health_check():
    """Check overall service health."""
    checks = {
        "qdrant": await check_qdrant(),
        "infinity": await check_infinity(),
    }

    # Determine overall status
    all_ok = all(check["status"] == "ok" for check in checks.values())
    status = "ok" if all_ok else "degraded"

    return HealthCheckResponse(status=status, checks=checks)


async def check_qdrant() -> dict:
    """Check if Qdrant is accessible."""
    try:
        client = QdrantClient(url=QDRANT_URL)
        collections = client.get_collections()
        collection_names = [c.name for c in collections.collections]

        return {
            "status": "ok",
            "message": f"Qdrant accessible with {len(collection_names)} collections",
            "collections": collection_names,
        }
    except Exception as e:
        return {"status": "error", "message": f"Qdrant check failed: {str(e)}"}


async def check_infinity() -> dict:
    """Check if Infinity embedding service is accessible."""
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            response = await client.get(f"{INFINITY_URL}/health")
            if response.status_code == 200:
                return {"status": "ok", "message": "Infinity embedding service accessible"}
            return {"status": "error", "message": f"Infinity returned {response.status_code}"}
    except Exception as e:
        return {"status": "error", "message": f"Infinity check failed: {str(e)}"}
