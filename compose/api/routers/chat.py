"""Chat router with WebSocket streaming and RAG support."""

import json
import os
import random
from datetime import datetime
from typing import Any

import httpx
from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from openai import AsyncOpenAI
from pydantic import BaseModel
from qdrant_client import QdrantClient

# Initialize clients
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")

# OpenRouter client for chat
openrouter_client = AsyncOpenAI(
    base_url="https://openrouter.ai/api/v1",
    api_key=OPENROUTER_API_KEY,
) if OPENROUTER_API_KEY else None

# Infinity embedding service (gte-large-en-v1.5, 1024-dim)
INFINITY_URL = os.getenv("INFINITY_URL", "http://localhost:7997")
INFINITY_MODEL = os.getenv("INFINITY_MODEL", "Alibaba-NLP/gte-large-en-v1.5")

# Qdrant client - use port 6335 (mapped from container's 6333)
QDRANT_URL = os.getenv("QDRANT_URL", "http://localhost:6335")
qdrant_client = QdrantClient(url=QDRANT_URL)
COLLECTION_NAME = os.getenv("QDRANT_COLLECTION", "content")


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

# Model cache with TTL
models_cache: dict[str, Any] = {
    "data": None,
    "timestamp": None,
    "ttl": 300  # 5 minutes
}

router = APIRouter()


class ModelsResponse(BaseModel):
    """Models list response."""
    models: list[dict[str, Any]]


@router.get("/models", response_model=ModelsResponse)
async def list_models():
    """
    Fetch available models from OpenRouter API.

    Returns free models plus GPT-5 and Claude 4.5 models.
    Results cached for 5 minutes.
    """
    now = datetime.utcnow().timestamp()

    # Check cache
    if (
        models_cache["data"] is not None
        and models_cache["timestamp"] is not None
        and (now - models_cache["timestamp"]) < models_cache["ttl"]
    ):
        return models_cache["data"]

    if not OPENROUTER_API_KEY:
        return _fallback_models()

    try:
        async with httpx.AsyncClient(timeout=10.0) as http_client:
            response = await http_client.get(
                "https://openrouter.ai/api/v1/models",
                headers={"Authorization": f"Bearer {OPENROUTER_API_KEY}"}
            )
            response.raise_for_status()
            all_models = response.json()["data"]

        filtered_models = []
        for model in all_models:
            model_id = model.get("id", "")
            pricing = model.get("pricing", {})

            is_free = (
                model_id.endswith(":free") and
                pricing.get("prompt") == "0" and
                pricing.get("completion") == "0"
            )
            is_gpt5 = (
                "gpt-5" in model_id.lower() and
                "image" not in model_id.lower() and
                "5.1" not in model_id.lower()
            )
            is_anthropic = (
                ("anthropic/" in model_id.lower() or "claude" in model_id.lower()) and
                "4.5" in model_id.lower()
            )

            if is_free or is_gpt5 or is_anthropic:
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

        filtered_models.sort(key=lambda m: (not m["is_free"], m["name"]))
        result = {"models": filtered_models}

        models_cache["data"] = result
        models_cache["timestamp"] = now
        return result

    except Exception as e:
        print(f"Error fetching models: {e}")
        return _fallback_models()


def _fallback_models() -> dict[str, Any]:
    """Return fallback model list."""
    return {
        "models": [
            {"id": "moonshotai/kimi-k2:free", "name": "Moonshot Kimi K2", "context_length": 128000, "is_free": True},
            {"id": "google/gemini-2.5-pro-exp-03-25:free", "name": "Gemini 2.5 Pro", "context_length": 1000000, "is_free": True},
            {"id": "deepseek/deepseek-chat-v3-0324:free", "name": "DeepSeek V3", "context_length": 64000, "is_free": True}
        ]
    }


@router.get("/random-question")
async def get_random_question():
    """Generate a random question based on indexed video content."""
    try:
        collection_info = qdrant_client.get_collection(COLLECTION_NAME)
        points_count = collection_info.points_count

        if points_count == 0:
            return {"question": "What are the best practices for building AI agents?"}

        random_offset = random.randint(0, max(0, points_count - 10))
        scroll_result = qdrant_client.scroll(
            collection_name=COLLECTION_NAME,
            limit=10,
            offset=random_offset,
            with_payload=True,
        )
        points = scroll_result[0]

        if not points:
            return {"question": "What are the best practices for building AI agents?"}

        # Extract tags and titles
        all_tags = set()
        video_titles = set()
        for point in points:
            payload = point.payload or {}
            # Handle different metadata formats
            if 'tags' in payload:
                all_tags.update(payload['tags'])
            if 'metadata' in payload:
                meta = payload['metadata']
                if 'subject' in meta:
                    subjects = meta['subject']
                    if isinstance(subjects, list):
                        all_tags.update(subjects)
                    elif isinstance(subjects, str):
                        all_tags.add(subjects)
                if 'title' in meta:
                    video_titles.add(meta['title'])
            if 'meta_youtube_title' in payload:
                video_titles.add(payload['meta_youtube_title'])

        all_tags = [t for t in all_tags if t]
        video_titles = list(video_titles)

        question_templates = []
        if all_tags:
            tag = random.choice(list(all_tags))
            question_templates.extend([
                f"What videos discuss {tag}?",
                f"Tell me about {tag}",
                f"What are the key concepts related to {tag}?",
            ])
        if video_titles:
            title = random.choice(video_titles)
            question_templates.extend([
                f"What does {title} cover?",
                f"Summarize {title}",
            ])

        if not question_templates:
            return {"question": "What are the best practices for building AI agents?"}

        return {"question": random.choice(question_templates)}

    except Exception as e:
        print(f"Error generating question: {e}")
        return {"question": "What are the best practices for building AI agents?"}


@router.websocket("/ws/chat")
async def websocket_chat(websocket: WebSocket):
    """
    WebSocket endpoint for basic streaming chat (no RAG).

    Client sends: {"message": "...", "model": "model-id"}
    Server streams: {"type": "token", "content": "..."}
    Server finishes: {"type": "done", "sources": []}
    """
    await websocket.accept()
    print(f"Chat WebSocket connected: {websocket.client}")

    if not openrouter_client:
        await websocket.send_json({"type": "error", "content": "OpenRouter API key not configured"})
        await websocket.close()
        return

    try:
        while True:
            data = await websocket.receive_text()
            request = json.loads(data)
            message = request.get("message", "")
            model = request.get("model", "moonshotai/kimi-k2:free")

            if not message:
                await websocket.send_json({"type": "error", "content": "Message cannot be empty"})
                continue

            if len(message) > 10000:
                await websocket.send_json({"type": "error", "content": "Message too long (max 10,000 chars)"})
                continue

            try:
                stream = await openrouter_client.chat.completions.create(
                    model=model,
                    messages=[{"role": "user", "content": message}],
                    stream=True,
                )

                async for chunk in stream:
                    if chunk.choices[0].delta.content:
                        await websocket.send_json({
                            "type": "token",
                            "content": chunk.choices[0].delta.content
                        })

                await websocket.send_json({"type": "done", "sources": []})

            except Exception as e:
                print(f"LLM error: {e}")
                await websocket.send_json({"type": "error", "content": f"AI error: {e}"})

    except WebSocketDisconnect:
        print(f"Chat WebSocket disconnected: {websocket.client}")
    except Exception as e:
        print(f"Chat WebSocket error: {e}")


@router.websocket("/ws/rag-chat")
async def websocket_rag_chat(websocket: WebSocket):
    """
    WebSocket endpoint for RAG-powered streaming chat.

    Searches Qdrant for relevant content, builds context, streams response.
    """
    await websocket.accept()
    print(f"RAG WebSocket connected: {websocket.client}")

    if not openrouter_client:
        await websocket.send_json({"type": "error", "content": "API keys not configured"})
        await websocket.close()
        return

    try:
        while True:
            data = await websocket.receive_text()
            request = json.loads(data)
            message = request.get("message", "")
            model = request.get("model", "moonshotai/kimi-k2:free")

            if not message:
                await websocket.send_json({"type": "error", "content": "Message cannot be empty"})
                continue

            try:
                # Step 1: Embed the query using Infinity (gte-large-en-v1.5)
                query_vector = await get_embedding(message)

                # Step 2: Search Qdrant
                search_results = qdrant_client.query_points(
                    collection_name=COLLECTION_NAME,
                    query=query_vector,
                    limit=5,
                )

                # Step 3: Build context
                context_chunks = []
                sources = []
                seen_ids = set()

                for result in search_results.points:
                    payload = result.payload or {}

                    # Extract text and metadata (handle different formats)
                    text = payload.get('text', payload.get('value', {}).get('transcript', ''))[:1000]
                    video_id = payload.get('video_id', payload.get('key', ''))

                    # Get title from various locations
                    title = (
                        payload.get('video_title') or
                        payload.get('meta_youtube_title') or
                        payload.get('metadata', {}).get('title') or
                        'Unknown Video'
                    )

                    # Get URL
                    url = payload.get('url', f"https://youtube.com/watch?v={video_id.split(':')[-1]}" if 'youtube' in video_id else '')

                    # Get tags
                    tags = (
                        payload.get('tags') or
                        payload.get('metadata', {}).get('subject') or
                        []
                    )
                    if isinstance(tags, str):
                        tags = [tags]

                    context_chunks.append(f"[Video: \"{title}\"]\n{text}")

                    if video_id not in seen_ids:
                        sources.append({
                            "video_title": title,
                            "url": url,
                            "tags": tags,
                        })
                        seen_ids.add(video_id)

                # Step 4: Build prompt
                context_section = "\n\n".join(context_chunks) if context_chunks else "No relevant content found."
                video_titles_list = "\n".join([f"- {s['video_title']}" for s in sources])

                augmented_prompt = f"""You are Mentat, an AI assistant with access to video transcripts.

Context from videos:
{context_section}

---
Available videos to cite:
{video_titles_list}

---
User question: {message}

Instructions:
1. Answer based on the video context when relevant
2. Cite video titles naturally in your response (no quotes around titles)
3. If the context doesn't help, say so and answer from general knowledge
4. Be concise and helpful"""

                # Step 5: Stream response
                stream = await openrouter_client.chat.completions.create(
                    model=model,
                    messages=[{"role": "user", "content": augmented_prompt}],
                    stream=True,
                )

                async for chunk in stream:
                    if chunk.choices[0].delta.content:
                        await websocket.send_json({
                            "type": "token",
                            "content": chunk.choices[0].delta.content
                        })

                await websocket.send_json({"type": "done", "sources": sources})

            except Exception as e:
                print(f"RAG error: {e}")
                await websocket.send_json({"type": "error", "content": f"RAG error: {e}"})

    except WebSocketDisconnect:
        print(f"RAG WebSocket disconnected: {websocket.client}")
    except Exception as e:
        print(f"RAG WebSocket error: {e}")
