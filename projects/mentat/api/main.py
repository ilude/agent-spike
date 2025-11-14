"""
Mentat API - Chat interface with WebSocket streaming

This is the minimal spike implementation. Iteration 2 will add RAG.
"""
import asyncio
import json
import os
from datetime import datetime

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from openai import AsyncOpenAI
from pydantic import BaseModel

# Load environment variables from git root
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[3]))
from tools.env_loader import load_root_env

load_root_env()

# Validate API key on startup
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")
if not OPENROUTER_API_KEY:
    print("WARNING: OPENROUTER_API_KEY not found in environment")
    print("Chat will work but with limited functionality")

# Initialize OpenRouter client
client = AsyncOpenAI(
    base_url="https://openrouter.ai/api/v1",
    api_key=OPENROUTER_API_KEY,
)

app = FastAPI(
    title="Mentat API",
    description="AI-powered chat interface for your cached content",
    version="0.1.0"
)

# CORS configuration for both local and Docker development
# Supports localhost (local dev) and container networking (Docker)
CORS_ORIGINS = [
    "http://localhost:5173",
    "http://127.0.0.1:5173",
    "http://frontend:5173",  # Docker container-to-container
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class HealthResponse(BaseModel):
    """Health check response"""
    status: str
    timestamp: str
    api_key_configured: bool


@app.get("/health", response_model=HealthResponse)
async def health():
    """Health check endpoint with diagnostics"""
    return HealthResponse(
        status="ok",
        timestamp=datetime.utcnow().isoformat(),
        api_key_configured=bool(OPENROUTER_API_KEY),
    )


@app.websocket("/ws/chat")
async def websocket_chat(websocket: WebSocket):
    """
    WebSocket endpoint for streaming chat responses.

    Client sends: {"message": "user question"}
    Server streams: {"type": "token", "content": "word"}
    Server finishes: {"type": "done", "sources": []}
    """
    await websocket.accept()
    print(f"WebSocket connection accepted from {websocket.client}")

    try:
        while True:
            # Receive message from client
            data = await websocket.receive_text()
            request = json.loads(data)
            message = request.get("message", "")

            if not message:
                await websocket.send_json({
                    "type": "error",
                    "content": "Message cannot be empty"
                })
                continue

            # Validate message length
            if len(message) > 10000:
                await websocket.send_json({
                    "type": "error",
                    "content": "Message too long (max 10,000 characters)"
                })
                continue

            print(f"Received message: {message[:100]}...")

            # Stream response from OpenRouter
            try:
                stream = await client.chat.completions.create(
                    model="moonshotai/kimi-k2:free",
                    messages=[{"role": "user", "content": message}],
                    stream=True,
                )

                # Stream tokens as they arrive
                async for chunk in stream:
                    if chunk.choices[0].delta.content:
                        await websocket.send_json({
                            "type": "token",
                            "content": chunk.choices[0].delta.content
                        })

                # Send completion message
                await websocket.send_json({
                    "type": "done",
                    "sources": []  # TODO (Iteration 2): Add actual sources from RAG
                })

            except Exception as llm_error:
                print(f"LLM error: {llm_error}")
                await websocket.send_json({
                    "type": "error",
                    "content": f"AI service error: {str(llm_error)}"
                })
                continue

    except WebSocketDisconnect:
        print(f"WebSocket disconnected from {websocket.client}")
    except json.JSONDecodeError as e:
        print(f"JSON decode error: {e}")
        await websocket.send_json({
            "type": "error",
            "content": "Invalid JSON format"
        })
    except Exception as e:
        print(f"WebSocket error: {e}")
        await websocket.send_json({
            "type": "error",
            "content": f"Server error: {str(e)}"
        })
        raise


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
