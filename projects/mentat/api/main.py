"""
Mentat API - Chat interface with WebSocket streaming

This is the minimal spike implementation. Iteration 2 will add RAG.
"""
import asyncio
import json
import os
from datetime import datetime
from typing import Any

import httpx
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from openai import AsyncOpenAI
from pydantic import BaseModel
from qdrant_client import QdrantClient
from qdrant_client.models import QueryRequest

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

# Initialize Qdrant client (connects to qdrant service in Docker)
# In Docker: use service name "qdrant", Outside Docker: use "localhost"
QDRANT_URL = os.getenv("QDRANT_URL", "http://qdrant:6333")
qdrant_client = QdrantClient(url=QDRANT_URL)
COLLECTION_NAME = "mentat_video_chunks"

# Initialize OpenAI client for embeddings
openai_client = AsyncOpenAI(api_key=os.getenv("OPENAI_API_KEY"))

# Model cache with TTL
models_cache = {
    "data": None,
    "timestamp": None,
    "ttl": 300  # 5 minutes
}

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


@app.get("/models")
async def list_models():
    """
    Fetch available models from OpenRouter API.

    Returns free models (ending with :free) plus specific paid models:
    - OpenAI GPT-5 models
    - Anthropic Claude 4.5 models

    Results are cached for 5 minutes to avoid rate limits.
    """
    # Check cache first
    now = datetime.utcnow().timestamp()
    if (
        models_cache["data"] is not None
        and models_cache["timestamp"] is not None
        and (now - models_cache["timestamp"]) < models_cache["ttl"]
    ):
        return models_cache["data"]

    try:
        # Fetch models from OpenRouter
        async with httpx.AsyncClient(timeout=10.0) as http_client:
            response = await http_client.get(
                "https://openrouter.ai/api/v1/models",
                headers={"Authorization": f"Bearer {OPENROUTER_API_KEY}"}
            )
            response.raise_for_status()
            all_models = response.json()["data"]

        # Filter models
        filtered_models = []

        for model in all_models:
            model_id = model.get("id", "")
            pricing = model.get("pricing", {})

            # Include free models (ending with :free)
            is_free = (
                model_id.endswith(":free") and
                pricing.get("prompt") == "0" and
                pricing.get("completion") == "0"
            )

            # Include GPT-5 models (exclude image and 5.1 variants)
            is_gpt5 = (
                "gpt-5" in model_id.lower() and
                "image" not in model_id.lower() and
                "5.1" not in model_id.lower()
            )

            # Include only Claude 4.5 models
            is_anthropic = (
                ("anthropic/" in model_id.lower() or "claude" in model_id.lower()) and
                "4.5" in model_id.lower()
            )

            if is_free or is_gpt5 or is_anthropic:
                # Clean up name: remove "(free)" suffix since we group by free/paid
                name = model.get("name", model_id)
                name = name.replace(" (free)", "").replace("(free)", "")

                filtered_models.append({
                    "id": model_id,
                    "name": name,
                    "context_length": model.get("context_length", 0),
                    "pricing": {
                        "prompt": pricing.get("prompt", "0"),
                        "completion": pricing.get("completion", "0"),
                    },
                    "is_free": is_free
                })

        # Sort: free first, then by name
        filtered_models.sort(key=lambda m: (not m["is_free"], m["name"]))

        result = {"models": filtered_models}

        # Update cache
        models_cache["data"] = result
        models_cache["timestamp"] = now

        return result

    except Exception as e:
        print(f"Error fetching models from OpenRouter: {e}")
        # Return fallback list
        return {
            "models": [
                {
                    "id": "moonshotai/kimi-k2:free",
                    "name": "Moonshot Kimi K2",
                    "context_length": 128000,
                    "pricing": {"prompt": "0", "completion": "0"},
                    "is_free": True
                },
                {
                    "id": "google/gemini-2.5-pro-exp-03-25:free",
                    "name": "Gemini 2.5 Pro Exp",
                    "context_length": 1000000,
                    "pricing": {"prompt": "0", "completion": "0"},
                    "is_free": True
                },
                {
                    "id": "deepseek/deepseek-chat-v3-0324:free",
                    "name": "DeepSeek Chat V3",
                    "context_length": 64000,
                    "pricing": {"prompt": "0", "completion": "0"},
                    "is_free": True
                }
            ]
        }


@app.get("/random-question")
async def get_random_question():
    """
    Generate a random question based on indexed video content.

    Queries Qdrant for random videos and creates a question based on their tags.
    """
    import random

    try:
        # Get collection info to determine total points
        collection_info = qdrant_client.get_collection(COLLECTION_NAME)
        points_count = collection_info.points_count

        if points_count == 0:
            # No videos indexed, return fallback question
            return {
                "question": "What are the best practices for prompt engineering?"
            }

        # Get a random offset and scroll to get some random points
        random_offset = random.randint(0, max(0, points_count - 10))

        scroll_result = qdrant_client.scroll(
            collection_name=COLLECTION_NAME,
            limit=10,
            offset=random_offset,
            with_payload=True,
        )

        points = scroll_result[0]  # First element is the list of points

        if not points:
            return {
                "question": "What are the best practices for prompt engineering?"
            }

        # Extract unique tags and video titles from the points
        all_tags = set()
        video_titles = set()

        for point in points:
            payload = point.payload
            if 'tags' in payload:
                all_tags.update(payload['tags'])
            if 'video_title' in payload:
                video_titles.add(payload['video_title'])

        # Remove empty tags
        all_tags = [tag for tag in all_tags if tag]
        video_titles = list(video_titles)

        if not all_tags and not video_titles:
            return {
                "question": "What are the best practices for prompt engineering?"
            }

        # Generate question based on what we have
        question_templates = []

        if all_tags:
            # Tag-based questions
            random_tag = random.choice(list(all_tags))
            question_templates.extend([
                f"What videos discuss {random_tag}?",
                f"Tell me about {random_tag}",
                f"What are the key concepts related to {random_tag}?",
                f"How does {random_tag} work?",
            ])

        if video_titles:
            # Video-specific questions
            random_video = random.choice(video_titles)
            question_templates.extend([
                f"What does {random_video} cover?",
                f"Summarize the main points from {random_video}",
                f"What are the key takeaways from {random_video}?",
            ])

        if len(all_tags) >= 2:
            # Multi-tag questions
            tag1, tag2 = random.sample(list(all_tags), 2)
            question_templates.extend([
                f"How do {tag1} and {tag2} relate to each other?",
                f"What's the difference between {tag1} and {tag2}?",
            ])

        # Pick a random question from templates
        question = random.choice(question_templates)

        return {"question": question}

    except Exception as e:
        print(f"Error generating random question: {e}")
        # Return fallback question on error
        return {
            "question": "What are the best practices for prompt engineering?"
        }


@app.websocket("/ws/chat")
async def websocket_chat(websocket: WebSocket):
    """
    WebSocket endpoint for streaming chat responses.

    Client sends: {"message": "user question", "model": "model-id"} (model optional)
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
            selected_model = request.get("model", "moonshotai/kimi-k2:free")

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

            print(f"Received message: {message[:100]}... (model: {selected_model})")

            # Stream response from OpenRouter
            try:
                stream = await client.chat.completions.create(
                    model=selected_model,
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


@app.websocket("/ws/rag-chat")
async def websocket_rag_chat(websocket: WebSocket):
    """
    WebSocket endpoint for RAG-powered streaming chat responses.

    Client sends: {"message": "user question", "model": "model-id"} (model optional)
    Server streams: {"type": "token", "content": "word"}
    Server finishes: {"type": "done", "sources": [{video_title, url, tags}...]}
    """
    await websocket.accept()
    print(f"RAG WebSocket connection accepted from {websocket.client}")

    try:
        while True:
            # Receive message from client
            data = await websocket.receive_text()
            request = json.loads(data)
            message = request.get("message", "")
            selected_model = request.get("model", "moonshotai/kimi-k2:free")

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

            print(f"RAG query: {message[:100]}... (model: {selected_model})")

            try:
                # Step 1: Embed the user's question
                embedding_response = await openai_client.embeddings.create(
                    model="text-embedding-3-small",
                    input=[message],
                )
                query_vector = embedding_response.data[0].embedding

                # Step 2: Search Qdrant for relevant chunks
                search_results = qdrant_client.query_points(
                    collection_name=COLLECTION_NAME,
                    query=query_vector,
                    limit=5,  # Top 5 most relevant chunks
                )

                # Step 3: Build context from search results
                context_chunks = []
                sources = []
                seen_videos = set()

                for result in search_results.points:
                    payload = result.payload
                    context_chunks.append(
                        f"[Video: \"{payload['video_title']}\" - {', '.join(payload['tags'])}]\n{payload['text']}"
                    )

                    # Track unique videos for sources
                    if payload['video_id'] not in seen_videos:
                        source = {
                            "video_title": payload['video_title'],
                            "url": payload['url'],
                            "tags": payload['tags'],
                            "description": payload['text'][:200],  # First 200 chars as description
                        }
                        # Add timestamp if available
                        if 'start_time' in payload and payload['start_time'] is not None:
                            source["start_time"] = payload['start_time']
                        sources.append(source)
                        seen_videos.add(payload['video_id'])

                # Step 4: Build augmented prompt
                context_section = "\n\n".join(context_chunks)

                # Build list of video titles for citation reference
                video_titles_list = "\n".join([f"- {s['video_title']}" for s in sources])

                augmented_prompt = f"""You are Mentat, an AI assistant with access to video transcripts.

Context from videos:
{context_section}

---
Available videos to cite:
{video_titles_list}

---
User question: {message}

CRITICAL INSTRUCTIONS FOR CITATIONS:
1. Write your answer in natural flowing prose (paragraphs, NOT bullet points or lists)
2. Embed video titles NATURALLY in your sentences when referencing them
3. Use the EXACT title text from the "Available videos to cite" list above
4. ABSOLUTELY NO QUOTES OR APOSTROPHES around video titles - this is critical
5. DO NOT create a separate "Sources:" section or bibliography at the end
6. DO NOT use bullet points or numbered lists to present videos
7. Cite each video ONLY ONCE - do not repeat the same video title multiple times

CORRECT citation examples:
- "In Prompts for learning AI, the presenter explains..."
- "According to From chatgpt to better reasoning models: practical prompts for 2025, we learn..."
- "The video Advanced prompting techniques: self-correction, meta prompting, and reasoning scaffolds discusses..."

WRONG citation examples (DO NOT DO THIS):
- "In 'Prompts for learning AI', the presenter..." (has quotes - WRONG)
- "In \"From chatgpt to better reasoning models\", we learn..." (has quotes - WRONG)
- Creating a bulleted list of videos (WRONG)

Write naturally without any quotes, apostrophes, or formatting around video titles. Just use the title directly in your sentence."""

                # Step 5: Stream response from LLM
                stream = await client.chat.completions.create(
                    model=selected_model,
                    messages=[{"role": "user", "content": augmented_prompt}],
                    stream=True,
                )

                # Stream tokens as they arrive
                async for chunk in stream:
                    if chunk.choices[0].delta.content:
                        await websocket.send_json({
                            "type": "token",
                            "content": chunk.choices[0].delta.content
                        })

                # Send completion message with sources
                print(f"Sending sources: {sources}")
                await websocket.send_json({
                    "type": "done",
                    "sources": sources
                })

            except Exception as rag_error:
                print(f"RAG error: {rag_error}")
                await websocket.send_json({
                    "type": "error",
                    "content": f"RAG service error: {str(rag_error)}"
                })
                continue

    except WebSocketDisconnect:
        print(f"RAG WebSocket disconnected from {websocket.client}")
    except json.JSONDecodeError as e:
        print(f"JSON decode error: {e}")
        await websocket.send_json({
            "type": "error",
            "content": "Invalid JSON format"
        })
    except Exception as e:
        print(f"RAG WebSocket error: {e}")
        await websocket.send_json({
            "type": "error",
            "content": f"Server error: {str(e)}"
        })
        raise


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
