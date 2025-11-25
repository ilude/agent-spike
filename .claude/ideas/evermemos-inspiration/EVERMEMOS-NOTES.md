# EverMemOS Technical Notes

**Created**: 2025-11-22
**Source**: https://github.com/EverMind-AI/EverMemOS

---

## Repository Overview

- **Stars**: 578+
- **License**: Apache 2.0
- **Language**: Python 3.10+
- **Package Manager**: uv (same as agent-spike)
- **Framework**: FastAPI

---

## Architecture: Two Cognitive Tracks

### Memory Construction Layer
Builds structured, retrievable long-term memory:

1. **MemCell Extraction**
   - Atomic memory units from conversations
   - Each MemCell is independently searchable
   - Maintains back-reference to source

2. **Multi-Level Memory Organization**
   - Themed grouping (what it's about)
   - Participant grouping (who's involved)
   - Temporal relationships

3. **Seven Memory Types**
   - Episodes: Time-bound events
   - Profiles: Entity descriptions
   - Preferences: Likes/dislikes
   - Relationships: Entity connections
   - Semantic Knowledge: Concepts
   - Facts: Discrete statements
   - Core Memories: Foundational items

### Memory Perception Layer
Enables intelligent recall:

1. **Hybrid Retrieval**
   - Semantic search (vectors)
   - Keyword search (BM25)
   - RRF (Reciprocal Rank Fusion)

2. **Intelligent Reranking**
   - Batch concurrent processing
   - Priority scoring

3. **Retrieval Modes**
   - **Lightweight**: RRF fusion only (fast)
   - **Agentic**: LLM-guided multi-round (thorough)

---

## Technical Stack

| Component | Technology |
|-----------|------------|
| Primary Storage | MongoDB 7.0+ |
| Keyword Search | Elasticsearch 8.x |
| Vector Search | Milvus 2.4+ |
| Cache | Redis 7.x |
| API Framework | FastAPI |
| Package Manager | uv |

**Note**: This is a complex 4-database stack. Agent-spike uses SurrealDB alone, which handles vectors + records + hybrid search with native HNSW indexes.

---

## Code Structure

```
src/
├── agentic_layer/      # Agent-based autonomous operations
├── biz_layer/          # Business logic / domain
├── infra_layer/        # Infrastructure operations
├── memory_layer/       # Memory storage & retrieval
│   ├── cluster_manager/
│   ├── llm/
│   ├── memcell_extractor/
│   ├── memory_extractor/
│   ├── profile_manager/
│   ├── prompts/
│   ├── memory_manager.py  # Main orchestrator
│   └── types.py           # Data structures
├── common_utils/       # Shared utilities
├── component/          # Reusable components
├── config/             # Configuration
├── core/               # Framework foundation
└── devops_scripts/     # Deployment automation
```

---

## API Endpoints (V3)

### Store Memories
```
POST /api/v3/agentic/memorize
```
Store message memories from conversations.

### Fast Retrieval
```
POST /api/v3/agentic/retrieve_lightweight
```
Hybrid retrieval using RRF fusion. Low latency.

### Intelligent Retrieval
```
POST /api/v3/agentic/retrieve_agentic
```
LLM-directed multi-round recall. Higher latency, better coverage.

---

## Key Differentiators (Their Claims)

### 1. Coherent Narrative
> "Automatically linking conversation pieces to build clear thematic context"

Instead of isolated fragments, builds connected stories across multi-threaded discussions.

### 2. Evidence-Based Perception
> "Recognizes implicit connections between memories and current tasks"

Example: When recommending food, recalls "you had dental surgery two days ago" without explicit prompting.

### 3. Living Profiles
> "User understanding evolves continuously"

Learns "who you are" rather than just recording "what you said."

---

## Benchmark Results

**LoCoMo Benchmark**: 92.3% reasoning accuracy (LLM-Judge evaluation)

Supported evaluation datasets:
- LoCoMo
- LongMemEval
- PersonaMem

---

## Retrieval Algorithm: RRF

Reciprocal Rank Fusion combines multiple ranked lists:

```python
# For each item appearing in any list:
score = sum(1 / (k + rank_i) for each list where item appears)

# k is typically 60 (standard constant)
# Lower rank = higher contribution to score
```

Example:
- Item A: Rank 1 in semantic, Rank 5 in keyword
- Score = 1/(60+1) + 1/(60+5) = 0.0164 + 0.0154 = 0.0318

---

## LLM-Guided Recall Flow

```
1. Initial query → Hybrid retrieval
2. Check: Are results sufficient?
   - Yes → Return results
   - No → Continue
3. LLM analyzes gaps in results
4. LLM generates refined queries
5. Execute refined queries
6. Merge and dedupe results
7. Repeat until sufficient or max rounds
```

**When to use**: Complex queries, multi-concept searches, when simple retrieval returns poor results.

---

## Comparison to Mem0 (Agent-Spike's Current Memory)

| Feature | EverMemOS | Mem0 |
|---------|-----------|------|
| Memory types | 7 explicit types | Untyped |
| Extraction | MemCells | Automatic |
| Organization | Hierarchical | Flat |
| Retrieval | Hybrid + LLM | Vector only |
| Customization | High | Medium |
| Complexity | High | Low |

**Verdict**: EverMemOS is more sophisticated but complex. Mem0 is simpler and sufficient for basic memory needs. Agent-spike could adopt EverMemOS patterns (memory types, extraction) while keeping simpler infrastructure.

---

## Relevance to Agent-Spike VISION

| EverMemOS Feature | Maps To |
|-------------------|---------|
| MemCell extraction | Concept extraction from content |
| 7 memory types | Richer content taxonomy |
| Living profiles | Evolving persona vectors |
| Evidence-based perception | Application Suggester |
| Hybrid retrieval | Recommendation Engine |
| LLM-guided recall | Complex query handling |

---

## Open Questions

1. **MemCell granularity**: How fine-grained should insights be for content (vs conversations)?

2. **Memory type assignment**: Should this be LLM-classified or rule-based?

3. **Profile evolution rate**: How quickly should persona vectors change?

4. **LLM recall cost**: When is it worth the extra latency/cost?

5. **Hierarchical clustering**: Is automatic theme grouping valuable for content?

---

## Resources

- **Repository**: https://github.com/EverMind-AI/EverMemOS
- **Community**: r/EverMindAI, @EverMindAI (X)
- **Issues**: https://github.com/EverMind-AI/EverMemOS/issues
