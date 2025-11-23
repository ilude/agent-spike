"""Chat router with WebSocket streaming and RAG support."""

import json
import os
import random
from datetime import datetime, timezone
from typing import Any

import httpx
from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from openai import AsyncOpenAI
from pydantic import BaseModel

from compose.services.conversations import get_conversation_service
from compose.services.memory import get_memory_service
from compose.services.projects import get_project_service
from compose.services.styles import get_styles_service
from compose.services.surrealdb import semantic_search

# Configuration (read at import - no side effects)
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY")
OLLAMA_URL = os.getenv("OLLAMA_URL", "http://192.168.16.241:11434")
INFINITY_URL = os.getenv("INFINITY_URL", "http://localhost:7997")
INFINITY_MODEL = os.getenv("INFINITY_MODEL", "Alibaba-NLP/gte-large-en-v1.5")

# Lazy-initialized clients (no network calls at import time)
_openrouter_client: AsyncOpenAI | None = None
_openai_client: AsyncOpenAI | None = None
_ollama_client: AsyncOpenAI | None = None


def get_openrouter_client() -> AsyncOpenAI | None:
    """Get OpenRouter client, creating it on first use."""
    global _openrouter_client
    if _openrouter_client is None and OPENROUTER_API_KEY:
        _openrouter_client = AsyncOpenAI(
            base_url="https://openrouter.ai/api/v1",
            api_key=OPENROUTER_API_KEY,
        )
    return _openrouter_client


def get_openai_client() -> AsyncOpenAI | None:
    """Get direct OpenAI client, creating it on first use."""
    global _openai_client
    if _openai_client is None and OPENAI_API_KEY:
        _openai_client = AsyncOpenAI(api_key=OPENAI_API_KEY)
    return _openai_client


def get_ollama_client() -> AsyncOpenAI:
    """Get Ollama client, creating it on first use."""
    global _ollama_client
    if _ollama_client is None:
        _ollama_client = AsyncOpenAI(
            base_url=f"{OLLAMA_URL}/v1",
            api_key="ollama",  # Ollama doesn't need a real key
        )
    return _ollama_client


def reset_clients() -> None:
    """Reset all clients to None. For testing only."""
    global _openrouter_client, _openai_client, _ollama_client
    _openrouter_client = None
    _openai_client = None
    _ollama_client = None


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


async def fetch_ollama_models() -> list[dict]:
    """Fetch available models from Ollama API."""
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            response = await client.get(f"{OLLAMA_URL}/api/tags")
            response.raise_for_status()
            data = response.json()

            models = []
            for model in data.get("models", []):
                name = model.get("name", "")
                # Format display name nicely
                display_name = name.replace(":", " ").replace("-", " ").title()
                models.append({
                    "id": f"ollama:{name}",
                    "name": f"{display_name} (Local)",
                    "context_length": 32000,  # Default, varies by model
                    "provider": "ollama",
                })
            return models
    except Exception as e:
        print(f"Failed to fetch Ollama models: {e}")
        return []


@router.get("/models", response_model=ModelsResponse)
async def list_models():
    """
    Fetch available models from OpenRouter API and local Ollama.

    Returns local Ollama models (dynamically fetched) plus OpenRouter free models,
    GPT-5 and Claude 4.5 models.
    Results cached for 5 minutes.
    """
    now = datetime.now(timezone.utc).timestamp()

    # Check cache
    if (
        models_cache["data"] is not None
        and models_cache["timestamp"] is not None
        and (now - models_cache["timestamp"]) < models_cache["ttl"]
    ):
        return models_cache["data"]

    # Fetch Ollama models dynamically
    ollama_models = await fetch_ollama_models()

    # Add direct OpenAI models if API key available
    openai_models = []
    if OPENAI_API_KEY:
        openai_models = [
            # GPT-4o family (current production)
            {"id": "openai:gpt-4o", "name": "GPT-4o", "context_length": 128000, "provider": "openai"},
            {"id": "openai:gpt-4o-mini", "name": "GPT-4o Mini", "context_length": 128000, "provider": "openai"},
            # Reasoning models
            {"id": "openai:o1", "name": "o1 Reasoning", "context_length": 200000, "provider": "openai"},
            {"id": "openai:o1-mini", "name": "o1 Mini", "context_length": 128000, "provider": "openai"},
            {"id": "openai:o1-preview", "name": "o1 Preview", "context_length": 128000, "provider": "openai"},
        ]

    # Add Claude models if API key available
    claude_models = []
    if ANTHROPIC_API_KEY:
        claude_models = [
            {"id": "anthropic:claude-sonnet-4-20250514", "name": "Claude Sonnet 4", "context_length": 200000, "provider": "anthropic"},
            {"id": "anthropic:claude-3-5-sonnet-20241022", "name": "Claude 3.5 Sonnet", "context_length": 200000, "provider": "anthropic"},
            {"id": "anthropic:claude-3-5-haiku-20241022", "name": "Claude 3.5 Haiku", "context_length": 200000, "provider": "anthropic"},
            {"id": "anthropic:claude-3-opus-20240229", "name": "Claude 3 Opus", "context_length": 200000, "provider": "anthropic"},
        ]

    if not OPENROUTER_API_KEY:
        return _fallback_models(ollama_models, openai_models, claude_models)

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

            # Only include free models from OpenRouter (paid models use direct API)
            is_free = (
                model_id.endswith(":free") and
                pricing.get("prompt") == "0" and
                pricing.get("completion") == "0"
            )

            if is_free:
                name = model.get("name", model_id)
                name = name.replace(" (free)", "").replace("(free)", "")
                filtered_models.append({
                    "id": model_id,
                    "name": name,
                    "context_length": model.get("context_length", 0),
                    "provider": "openrouter",
                })

        filtered_models.sort(key=lambda m: m["name"])

        # Order: Ollama > Claude > OpenAI > OpenRouter
        result = {"models": ollama_models + claude_models + openai_models + filtered_models}

        models_cache["data"] = result
        models_cache["timestamp"] = now
        return result

    except Exception as e:
        print(f"Error fetching models: {e}")
        return _fallback_models(ollama_models, openai_models, claude_models)


def _fallback_models(
    ollama_models: list[dict] | None = None,
    openai_models: list[dict] | None = None,
    claude_models: list[dict] | None = None
) -> dict[str, Any]:
    """Return fallback model list with dynamic Ollama, Claude, and OpenAI models."""
    openrouter_fallback = [
        {"id": "moonshotai/kimi-k2:free", "name": "Moonshot Kimi K2", "context_length": 128000, "provider": "openrouter"},
        {"id": "google/gemini-2.5-pro-exp-03-25:free", "name": "Gemini 2.5 Pro", "context_length": 1000000, "provider": "openrouter"},
        {"id": "deepseek/deepseek-chat-v3-0324:free", "name": "DeepSeek V3", "context_length": 64000, "provider": "openrouter"}
    ]
    return {"models": (ollama_models or []) + (claude_models or []) + (openai_models or []) + openrouter_fallback}


@router.get("/random-question")
async def get_random_question():
    """Generate a random question based on indexed video content."""
    try:
        qdrant = get_qdrant_client()
        collection_info = qdrant.get_collection(COLLECTION_NAME)
        points_count = collection_info.points_count

        if points_count == 0:
            return {"question": "What are the best practices for building AI agents?"}

        random_offset = random.randint(0, max(0, points_count - 10))
        scroll_result = qdrant.scroll(
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
            # Also check value.title (fast_reingest stores here)
            if 'value' in payload and payload['value'].get('title'):
                video_titles.add(payload['value']['title'])

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

    Client sends: {"message": "...", "model": "model-id", "conversation_id": "..."}
    Server streams: {"type": "token", "content": "..."}
    Server finishes: {"type": "done", "sources": []}
    """
    await websocket.accept()
    print(f"Chat WebSocket connected: {websocket.client}")

    openrouter = get_openrouter_client()
    if not openrouter:
        await websocket.send_json({"type": "error", "content": "OpenRouter API key not configured"})
        await websocket.close()
        return

    conversation_service = get_conversation_service()
    project_service = get_project_service()
    styles_service = get_styles_service()
    memory_service = get_memory_service()

    try:
        while True:
            data = await websocket.receive_text()
            request = json.loads(data)
            message = request.get("message", "")
            model = request.get("model", "moonshotai/kimi-k2:free")
            conversation_id = request.get("conversation_id")
            project_id = request.get("project_id")
            style_id = request.get("style", "default")
            use_memory = request.get("use_memory", True)

            if not message:
                await websocket.send_json({"type": "error", "content": "Message cannot be empty"})
                continue

            if len(message) > 10000:
                await websocket.send_json({"type": "error", "content": "Message too long (max 10,000 chars)"})
                continue

            # Save user message to conversation
            if conversation_id:
                await conversation_service.add_message(conversation_id, "user", message)

            try:
                # Build system message from project instructions, style, and memory
                system_parts = []

                # Apply style modifier (if not default)
                style_modifier = styles_service.get_system_prompt_modifier(style_id)
                if style_modifier:
                    system_parts.append(style_modifier)

                # Add memory context if enabled
                if use_memory:
                    memory_context = memory_service.build_memory_context(message)
                    if memory_context:
                        system_parts.append(memory_context)

                # Get project custom instructions if project_id provided
                if project_id:
                    project = project_service.get_project(project_id)
                    if project and project.custom_instructions:
                        system_parts.append(project.custom_instructions)

                system_message = "\n\n".join(system_parts) if system_parts else None

                # Route to Ollama, OpenAI, or OpenRouter
                if model.startswith("ollama:"):
                    actual_model = model.replace("ollama:", "")
                    client = get_ollama_client()
                elif model.startswith("openai:"):
                    actual_model = model.replace("openai:", "")
                    client = get_openai_client()
                    if not client:
                        await websocket.send_json({"type": "error", "content": "OpenAI API key not configured"})
                        continue
                else:
                    client = openrouter
                    actual_model = model

                # Build messages list
                messages = []
                if system_message:
                    messages.append({"role": "system", "content": system_message})
                messages.append({"role": "user", "content": message})

                stream = await client.chat.completions.create(
                    model=actual_model,
                    messages=messages,
                    stream=True,
                )

                full_response = ""
                async for chunk in stream:
                    if chunk.choices[0].delta.content:
                        content = chunk.choices[0].delta.content
                        full_response += content
                        await websocket.send_json({
                            "type": "token",
                            "content": content
                        })

                # Save assistant message to conversation
                if conversation_id and full_response.strip():
                    await conversation_service.add_message(
                        conversation_id, "assistant", full_response.strip()
                    )

                # Extract memories from conversation (async, non-blocking)
                if use_memory and full_response.strip():
                    try:
                        await memory_service.extract_memories_from_conversation(
                            message, full_response.strip(), conversation_id
                        )
                    except Exception as mem_err:
                        print(f"Memory extraction failed: {mem_err}")

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

    openrouter = get_openrouter_client()
    if not openrouter:
        await websocket.send_json({"type": "error", "content": "API keys not configured"})
        await websocket.close()
        return

    conversation_service = get_conversation_service()
    project_service = get_project_service()
    styles_service = get_styles_service()
    memory_service = get_memory_service()

    try:
        while True:
            data = await websocket.receive_text()
            request = json.loads(data)
            message = request.get("message", "")
            model = request.get("model", "moonshotai/kimi-k2:free")
            conversation_id = request.get("conversation_id")
            project_id = request.get("project_id")
            style_id = request.get("style", "default")
            use_memory = request.get("use_memory", True)

            if not message:
                await websocket.send_json({"type": "error", "content": "Message cannot be empty"})
                continue

            # Save user message to conversation
            if conversation_id:
                await conversation_service.add_message(conversation_id, "user", message)

            # Build custom instructions from project, style, and memory
            custom_parts = []

            # Apply style modifier (if not default)
            style_modifier = styles_service.get_system_prompt_modifier(style_id)
            if style_modifier:
                custom_parts.append(style_modifier)

            # Add memory context if enabled
            if use_memory:
                memory_context = memory_service.build_memory_context(message)
                if memory_context:
                    custom_parts.append(memory_context)

            # Get project custom instructions if project_id provided
            if project_id:
                project = project_service.get_project(project_id)
                if project and project.custom_instructions:
                    custom_parts.append(project.custom_instructions)

            custom_instructions = "\n\n".join(custom_parts) if custom_parts else None

            try:
                # Try RAG search, but gracefully fall back if it fails
                context_chunks = []
                sources = []
                rag_available = True

                try:
                    # Step 1: Embed the query using Infinity
                    query_vector = await get_embedding(message)

                    # Step 2: Search SurrealDB
                    search_results = await semantic_search(query_vector, limit=5)

                    # Step 3: Build context from SurrealDB results
                    seen_ids = set()

                    for result in search_results:
                        video_id = result.video_id
                        title = result.title or 'Unknown Video'
                        channel = result.channel_name or 'Unknown Channel'
                        url = result.url or f"https://youtube.com/watch?v={video_id}"

                        # Include channel info so LLM can filter by author
                        context_chunks.append(
                            f"[Video: \"{title}\"]\n"
                            f"Channel: {channel}\n"
                            f"Relevance: {result.similarity_score:.3f}"
                        )

                        if video_id not in seen_ids:
                            sources.append({
                                "video_title": title,
                                "channel": channel,
                                "url": url,
                                "tags": [],  # Tags stored separately in SurrealDB
                            })
                            seen_ids.add(video_id)

                except Exception as rag_error:
                    print(f"RAG search failed (falling back to direct chat): {rag_error}")
                    rag_available = False

                # Step 4: Build prompt (with or without RAG context)
                # Start with custom instructions if available
                system_prefix = ""
                if custom_instructions:
                    system_prefix = f"{custom_instructions}\n\n---\n\n"

                if rag_available and context_chunks:
                    context_section = "\n\n".join(context_chunks)
                    video_list = "\n".join([f"- {s['video_title']} (by {s.get('channel', 'Unknown')})" for s in sources])

                    augmented_prompt = f"""{system_prefix}You are Mentat, an AI assistant with access to video transcripts.

Context from videos:
{context_section}

---
Available videos to cite:
{video_list}

---
User question: {message}

Instructions:
1. Answer based on the video context when relevant
2. If the user asks about a specific person/channel, filter results to only show their videos
3. IMPORTANT: When citing videos, use the EXACT full title from the list above - do not shorten or paraphrase titles
4. Include the channel/author name when relevant to the question
5. If the context doesn't help, say so and answer from general knowledge
6. Be concise and helpful"""
                else:
                    # Fallback: no RAG context available
                    augmented_prompt = f"""{system_prefix}You are Mentat, a helpful AI assistant.

User: {message}

Respond helpfully and concisely."""

                # Step 5: Stream response (route to Ollama, OpenAI, or OpenRouter)
                if model.startswith("ollama:"):
                    # Use local Ollama server
                    actual_model = model.replace("ollama:", "")
                    client = get_ollama_client()
                elif model.startswith("openai:"):
                    # Use direct OpenAI API
                    actual_model = model.replace("openai:", "")
                    client = get_openai_client()
                    if not client:
                        await websocket.send_json({"type": "error", "content": "OpenAI API key not configured"})
                        continue
                else:
                    # Use OpenRouter
                    client = openrouter
                    actual_model = model

                stream = await client.chat.completions.create(
                    model=actual_model,
                    messages=[{"role": "user", "content": augmented_prompt}],
                    stream=True,
                )

                full_response = ""
                async for chunk in stream:
                    if chunk.choices[0].delta.content:
                        content = chunk.choices[0].delta.content
                        full_response += content
                        await websocket.send_json({
                            "type": "token",
                            "content": content
                        })

                # Save assistant message to conversation
                if conversation_id and full_response.strip():
                    # Convert sources to serializable format
                    sources_for_storage = [
                        {
                            "video_title": s.get("video_title", ""),
                            "url": s.get("url", ""),
                            "tags": s.get("tags", []),
                        }
                        for s in sources
                    ]
                    await conversation_service.add_message(
                        conversation_id, "assistant", full_response.strip(), sources_for_storage
                    )

                # Extract memories from conversation (async, non-blocking)
                if use_memory and full_response.strip():
                    try:
                        await memory_service.extract_memories_from_conversation(
                            message, full_response.strip(), conversation_id
                        )
                    except Exception as mem_err:
                        print(f"Memory extraction failed: {mem_err}")

                await websocket.send_json({"type": "done", "sources": sources})

            except Exception as e:
                print(f"Chat error: {e}")
                await websocket.send_json({"type": "error", "content": f"Error: {e}"})

    except WebSocketDisconnect:
        print(f"RAG WebSocket disconnected: {websocket.client}")
    except Exception as e:
        print(f"RAG WebSocket error: {e}")
