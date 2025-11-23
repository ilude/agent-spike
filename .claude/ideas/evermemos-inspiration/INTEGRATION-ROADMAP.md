# Integration Roadmap: EverMemOS Ideas into Agent-Spike

**Created**: 2025-11-22

---

## Overview

This roadmap describes how to integrate the best ideas from EverMemOS into the agent-spike architecture without over-engineering.

---

## Phase 1: Schema Enhancement (Low Effort)

**Goal**: Add memory type taxonomy to existing Qdrant payloads.

### Changes

```python
# Current payload schema (content collection)
{
    "id": "youtube:i5kwX7jeWL8",
    "type": "youtube_video",
    "title": "...",
    "tags": [...],
    "summary": "...",
}

# Enhanced schema
{
    "id": "youtube:i5kwX7jeWL8",
    "type": "youtube_video",
    "memory_type": "episode",  # NEW: One of 7 types
    "title": "...",
    "tags": [...],
    "summary": "...",
    "importance": "normal",    # NEW: normal | high | foundational
    "connections": [],         # NEW: Related content/project IDs
}
```

### Memory Type Mapping for Content

| Content Type | Default Memory Type |
|--------------|-------------------|
| YouTube video (watched) | `episode` |
| Blog article (read) | `episode` |
| Source/channel profile | `profile` |
| User topic interest | `preference` |
| Content→Project link | `relationship` |
| Extracted insight | `semantic_knowledge` |
| Metadata (date, duration) | `fact` |
| Highly-rated foundational | `core_memory` |

### Implementation
1. Update `CacheManager.store()` to include `memory_type`
2. Add `importance` field for prioritization
3. Add `connections` array for relationship tracking

---

## Phase 2: Insight Extraction Pipeline Step

**Goal**: Extract atomic learnings from content (MemCell equivalent).

### Pipeline Enhancement

```
Current:  Fetch → Archive → Tag → Summarize → Embed → Store
Enhanced: Fetch → Archive → Tag → Summarize → Extract Insights → Embed → Store
```

### Insight Extractor Design

```python
from pydantic import BaseModel
from pydantic_ai import Agent

class Insight(BaseModel):
    content: str                    # The insight itself
    memory_type: str               # semantic_knowledge, fact, etc.
    confidence: float              # 0.0 - 1.0
    source_location: str | None    # Timestamp or section
    applicable_to: list[str]       # Topics/domains

class InsightExtractionResult(BaseModel):
    insights: list[Insight]

insight_extractor = Agent(
    "anthropic:claude-3-5-haiku-latest",
    result_type=InsightExtractionResult,
    system_prompt="""
    Extract discrete, actionable insights from the content.
    Each insight should be:
    - Self-contained (understandable without context)
    - Specific (not vague generalizations)
    - Applicable (can be used in other contexts)

    Classify each as:
    - semantic_knowledge: Concepts, patterns, understanding
    - fact: Discrete true statements
    - relationship: Connections between things
    """
)
```

### Storage Strategy

Option A: Separate collection
```python
# insights collection
{
    "id": "insight:youtube:i5kwX7jeWL8:001",
    "vector": [...],  # Embed the insight text
    "payload": {
        "source_content_id": "youtube:i5kwX7jeWL8",
        "insight": "Dependency injection enables testable code",
        "memory_type": "semantic_knowledge",
        "confidence": 0.92,
        "applicable_to": ["testing", "architecture"]
    }
}
```

Option B: Nested in content payload (simpler)
```python
# content collection - enhanced payload
{
    "id": "youtube:i5kwX7jeWL8",
    "insights": [
        {"text": "...", "type": "semantic_knowledge", "confidence": 0.92},
        {"text": "...", "type": "fact", "confidence": 0.95},
    ]
}
```

**Recommendation**: Start with Option B (simpler), migrate to Option A if search quality suffers.

---

## Phase 3: Hybrid Search with RRF

**Goal**: Combine semantic and keyword search in Qdrant.

### Current State
Qdrant supports hybrid search natively via:
- Dense vectors (semantic)
- Sparse vectors (BM25-like)

### Implementation

```python
from qdrant_client import QdrantClient
from qdrant_client.models import models

async def hybrid_search(
    query: str,
    query_vector: list[float],
    collection: str = "content",
    limit: int = 10
) -> list:
    """
    RRF-style hybrid search combining semantic + keyword.
    """
    client = QdrantClient(...)

    # Semantic search
    semantic_results = client.search(
        collection_name=collection,
        query_vector=query_vector,
        limit=limit * 2,  # Over-fetch for fusion
    )

    # Keyword filter (using Qdrant's payload search)
    keyword_results = client.scroll(
        collection_name=collection,
        scroll_filter=models.Filter(
            should=[
                models.FieldCondition(
                    key="title",
                    match=models.MatchText(text=query)
                ),
                models.FieldCondition(
                    key="tags",
                    match=models.MatchAny(any=query.lower().split())
                ),
            ]
        ),
        limit=limit * 2,
    )

    # RRF fusion
    return reciprocal_rank_fusion(
        semantic_results,
        keyword_results,
        k=60  # Standard RRF constant
    )

def reciprocal_rank_fusion(
    *result_lists: list,
    k: int = 60
) -> list:
    """
    Combine multiple ranked lists using RRF.
    Score = sum(1 / (k + rank_i)) for each list
    """
    scores = {}
    for results in result_lists:
        for rank, item in enumerate(results):
            item_id = item.id
            if item_id not in scores:
                scores[item_id] = {"item": item, "score": 0}
            scores[item_id]["score"] += 1 / (k + rank + 1)

    sorted_items = sorted(
        scores.values(),
        key=lambda x: x["score"],
        reverse=True
    )
    return [x["item"] for x in sorted_items]
```

---

## Phase 4: Persona Evolution

**Goal**: Update persona vectors incrementally on each rating.

### Current State
- `personas` collection stores user taste vectors
- Built from rated content (static)

### Enhancement

```python
async def evolve_persona_on_rating(
    user_id: str,
    content_id: str,
    rating: int  # 1-5
):
    """
    Incrementally update persona vector based on new rating.
    """
    # Get embeddings
    content = await get_content(content_id)
    persona = await get_persona(user_id)

    if persona is None:
        # First rating - initialize with content vector
        await create_persona(user_id, content.vector)
        return

    # Calculate influence weight
    # Rating 5 = +0.2, Rating 1 = -0.2
    weight = (rating - 3) / 10

    # Learning rate decay (older personas change less)
    num_ratings = persona.metadata.get("num_ratings", 0)
    learning_rate = 1 / (1 + num_ratings * 0.1)  # Decay over time

    # Update vector
    adjustment = weight * learning_rate
    new_vector = normalize(
        np.array(persona.vector) + adjustment * np.array(content.vector)
    )

    # Store updated persona
    await update_persona(
        user_id,
        vector=new_vector.tolist(),
        metadata={
            "num_ratings": num_ratings + 1,
            "last_updated": datetime.now().isoformat()
        }
    )
```

### Considerations
- **Cold start**: First few ratings have high influence
- **Decay**: Older personas stabilize over time
- **Negative influence**: Low ratings push persona away from content

---

## Phase 5: Conditional LLM-Guided Recall

**Goal**: Use LLM to refine search only when initial results are poor.

### Implementation

```python
async def smart_search(
    query: str,
    min_results: int = 5,
    min_relevance: float = 0.7
) -> list:
    """
    Search with optional LLM refinement for complex queries.
    """
    # Round 1: Standard hybrid search
    results = await hybrid_search(query)

    # Check quality
    good_results = [r for r in results if r.score >= min_relevance]

    if len(good_results) >= min_results:
        return good_results  # Fast path

    # Round 2: LLM refinement (expensive path)
    refined_queries = await refine_search_query(
        original_query=query,
        current_results=results,
    )

    all_results = list(results)
    for refined in refined_queries[:3]:  # Max 3 refinements
        more = await hybrid_search(refined)
        all_results.extend(more)

    # Dedupe and return
    return dedupe_by_id(all_results)[:min_results * 2]

async def refine_search_query(
    original_query: str,
    current_results: list
) -> list[str]:
    """
    Use LLM to generate alternative search queries.
    """
    result_summaries = [r.payload.get("title", "") for r in current_results[:5]]

    response = await llm.complete(
        f"""
        Original search: "{original_query}"
        Current results: {result_summaries}

        The results seem incomplete. Generate 3 alternative search queries
        that might find relevant content we missed. Consider:
        - Synonyms and related terms
        - More specific sub-topics
        - Broader category terms

        Return as JSON array of strings.
        """
    )
    return json.loads(response)
```

### When to Enable
- Application Suggester queries
- Complex multi-concept searches
- User explicitly requests "deep search"

**NOT for**: Simple lookups, browsing, recent content

---

## Timeline Summary

| Phase | Effort | Dependencies | Value |
|-------|--------|--------------|-------|
| 1. Schema enhancement | 1-2 hours | None | Foundation |
| 2. Insight extraction | 4-8 hours | Phase 1 | High |
| 3. Hybrid search | 2-4 hours | None | Medium |
| 4. Persona evolution | 2-4 hours | Rating system | Medium |
| 5. LLM-guided recall | 4-6 hours | Phases 1-3 | Medium |

**Total estimated effort**: 13-24 hours

**Recommended order**: 1 → 3 → 2 → 4 → 5

Start with schema (foundation) and hybrid search (quick win), then add insight extraction (high value), persona evolution (improves over time), and finally LLM recall (complex queries).
