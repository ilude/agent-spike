"""FastAPI application for exposing Python agents to N8N."""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from api.routers import health, youtube, cache

# Create FastAPI app
app = FastAPI(
    title="Agent Spike API",
    description="FastAPI service exposing Python 3.14 agents for N8N integration",
    version="0.1.0",
)

# Add CORS middleware for N8N cross-origin requests
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allow all origins (adjust for production)
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(health.router)
app.include_router(youtube.router, prefix="/youtube", tags=["youtube"])
app.include_router(cache.router, prefix="/cache", tags=["cache"])


@app.get("/")
async def root():
    """Root endpoint with API information."""
    return {
        "name": "Agent Spike API",
        "version": "0.1.0",
        "docs": "/docs",
        "health": "/health",
        "endpoints": {
            "youtube_analyze": "POST /youtube/analyze",
            "cache_search": "POST /cache/search",
        },
    }
