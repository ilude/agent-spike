# EverMemOS vs Agent-Spike VISION Comparison

**Created**: 2025-11-22

---

## Architecture Overview

### EverMemOS: Two Cognitive Tracks

```
┌─────────────────────────────────────┐
│       Memory Construction           │
├─────────────────────────────────────┤
│ • MemCell extraction (atomic units) │
│ • Multi-level hierarchical org      │
│ • 7 memory types                    │
│ • Theme + participant grouping      │
└─────────────────────────────────────┘
                 │
                 ▼
┌─────────────────────────────────────┐
│        Memory Perception            │
├─────────────────────────────────────┤
│ • Hybrid retrieval (RRF fusion)     │
│ • Intelligent reranking             │
│ • LLM-guided multi-round recall     │
│ • Lightweight fast mode             │
└─────────────────────────────────────┘
```

### Agent-Spike VISION: Content Pipeline

```
┌─────────────────────────────────────┐
│       Content Ingestion             │
├─────────────────────────────────────┤
│ • YouTube transcripts               │
│ • Webpages via Docling              │
│ • Archive-first preservation        │
│ • Semantic embeddings               │
└─────────────────────────────────────┘
                 │
                 ▼
┌─────────────────────────────────────┐
│       Analysis Layer                │
├─────────────────────────────────────┤
│ • Tagging                           │
│ • Summarization                     │
│ • Concept extraction                │
└─────────────────────────────────────┘
                 │
                 ▼
┌─────────────────────────────────────┐
│    Recommendation + Application     │
├─────────────────────────────────────┤
│ • Preference learning               │
│ • Semantic search                   │
│ • Application suggester             │
└─────────────────────────────────────┘
```

---

## Feature-by-Feature Comparison

| Feature | EverMemOS | Agent-Spike VISION |
|---------|-----------|-------------------|
| **Primary Focus** | Conversation memory | Content knowledge |
| **Memory Types** | 7 distinct types | 2 collections (content + preferences) |
| **Atomic Units** | MemCells from conversations | None yet (tags only) |
| **Organization** | Hierarchical by theme/participant | Flat with metadata tags |
| **Retrieval** | Hybrid RRF + LLM reranking | Semantic + metadata filters |
| **Profile Model** | Living profiles (continuous update) | Static preferences |
| **Proactive Recall** | Evidence-based perception | Application Suggester (planned) |
| **Data Preservation** | Not emphasized | Archive-first (core principle) |
| **Embedding Strategy** | Single vector | Dual (global + chunk) |
| **Persona Modeling** | Structured profiles | Embedding vectors (taste dimensions) |

---

## Where EverMemOS Excels

### 1. Memory Type Taxonomy
Their 7 types provide semantic structure:
- **Episodes**: Time-bound events/experiences
- **Profiles**: Entity descriptions
- **Preferences**: Likes, dislikes, interests
- **Relationships**: Connections between entities
- **Semantic Knowledge**: Concepts and understanding
- **Facts**: Discrete true statements
- **Core Memories**: Foundational, high-importance items

### 2. MemCell Extraction
Atomic memory units extracted from conversations:
- Each MemCell is independently searchable
- Maintains back-reference to source
- Enables fine-grained retrieval

### 3. Hierarchical Organization
Memories grouped by:
- Theme (what it's about)
- Participants (who's involved)
- Temporal relationship (when it happened)

### 4. LLM-Guided Recall
When initial retrieval is insufficient:
- LLM analyzes gaps
- Generates refined queries
- Multi-round search until satisfied

---

## Where Agent-Spike Excels

### 1. Archive-First Pipeline
```
Fetch expensive data → Archive immediately → Then process
```
- Never lose raw data (API changes, rate limits)
- Enables reprocessing with different strategies
- Tracks costs over time

### 2. Dual Embedding Strategy
```
Global embeddings (whole document) → content collection
Chunk embeddings (passages)       → content_chunks collection
```
- Better for long-form content (videos, articles)
- Enables both document-level and passage-level search

### 3. Persona Vector Modeling
```python
# Taste dimensions as embeddings, not structured fields
persona_vector = embed([
    rated_content_1,
    rated_content_2,
    ...
])
```
- More nuanced than structured preferences
- Enables semantic similarity matching

### 4. Content-Centric Design
- Focus on external knowledge (videos, blogs, papers)
- Not conversation memory
- Better for research assistant use case

### 5. IPython Orchestrator (Planned)
- Code generation instead of tool calling
- More flexible than their traditional agentic_layer
- 98%+ token reduction vs MCP

---

## Stack Comparison

| Component | EverMemOS | Agent-Spike |
|-----------|-----------|-------------|
| **Vector DB** | Milvus | SurrealDB (native HNSW) |
| **Keyword Search** | Elasticsearch | SurrealDB (hybrid) |
| **Primary Storage** | MongoDB | SurrealDB records |
| **Cache** | Redis | None (SurrealDB is fast) |
| **Memory Layer** | Custom | Mem0 |
| **Embeddings** | Not specified | Infinity (bge-m3) |
| **API** | FastAPI | FastAPI |
| **Package Manager** | uv | uv |

**Verdict**: Their stack is more complex (4 databases). SurrealDB can handle vector + records + hybrid search in one system. Keep it simple.

---

## Summary

| Aspect | Winner | Why |
|--------|--------|-----|
| Memory taxonomy | EverMemOS | 7 types vs 2 |
| Atomic extraction | EverMemOS | MemCells are powerful |
| Data preservation | Agent-Spike | Archive-first is safer |
| Embedding strategy | Agent-Spike | Dual embeddings for content |
| Retrieval sophistication | EverMemOS | RRF + reranking |
| Stack simplicity | Agent-Spike | Single DB vs 4 |
| Use case fit | Agent-Spike | Content vs conversations |
