"""FastAPI application for exposing Python agents and chat interface."""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from compose.api.routers import health, youtube, cache, chat, stats, ingest, conversations

# Create FastAPI app
app = FastAPI(
    title="Agent Spike API",
    description="FastAPI service with chat interface and agent integration",
    version="0.2.0",
)

# CORS configuration for frontend and N8N
CORS_ORIGINS = [
    "http://localhost:5173",    # Vite dev server
    "http://127.0.0.1:5173",
    "http://frontend:5173",     # Docker container
    "http://localhost:8000",
    "*",                        # N8N and other integrations
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(health.router)
app.include_router(youtube.router, prefix="/youtube", tags=["youtube"])
app.include_router(cache.router, prefix="/cache", tags=["cache"])
app.include_router(chat.router, prefix="/chat", tags=["chat"])
app.include_router(stats.router, tags=["stats"])
app.include_router(ingest.router, tags=["ingest"])
app.include_router(conversations.router, tags=["conversations"])


@app.get("/")
async def root():
    """Root endpoint with API information."""
    return {
        "name": "Agent Spike API",
        "version": "0.2.0",
        "docs": "/docs",
        "health": "/health",
        "endpoints": {
            "youtube_analyze": "POST /youtube/analyze",
            "cache_search": "POST /cache/search",
            "chat_models": "GET /chat/models",
            "chat_random": "GET /chat/random-question",
            "chat_ws": "WS /chat/ws/chat",
            "chat_rag_ws": "WS /chat/ws/rag-chat",
            "ingest": "POST /ingest",
            "ingest_detect": "GET /ingest/detect",
            "conversations_list": "GET /conversations",
            "conversations_create": "POST /conversations",
            "conversations_get": "GET /conversations/{id}",
            "conversations_search": "GET /conversations/search?q=",
        },
    }
