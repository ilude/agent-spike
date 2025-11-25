# Agent Spike - Long-Term Vision

**Created**: 2025-11-05
**Last Updated**: 2025-11-05
**Status**: Planning & Early Development

---

## Executive Summary

Transform the agent-spike learning project into a **Personal AI Research Assistant and Recommendation Engine** that:

1. **Monitors** news, blogs, videos for topics aligned with user interests
2. **Analyzes** content to understand relevance to user's projects and problems
3. **Recommends** content based on preferences and current work
4. **Suggests applications** of learned concepts to active projects
5. **Tracks memories** of what was learned, liked, and applied

---

## The Problem

**Information overload**: Too much content (videos, blogs, papers) to manually review.

**Lost connections**: Valuable insights from content aren't systematically connected to active projects or problems.

**Manual curation**: No automated way to filter content by personal preferences and relevance.

**Application gap**: Learning happens, but applying it to existing projects requires manual effort.

---

## The Solution

A multi-agent system that acts as a **personal research assistant**:

### Core Capabilities

1. **Content Ingestion**
   - Fetch transcripts from YouTube videos
   - Extract text from blog posts and articles
   - Parse academic papers and documentation
   - Store with semantic embeddings for search

2. **Intelligent Analysis**
   - Tag content with relevant topics
   - Extract key concepts and techniques
   - Summarize main points
   - Rate quality and relevance

3. **Preference Learning**
   - Track user ratings and feedback
   - Learn topics of high interest
   - Understand learning style preferences
   - Model project goals and challenges

4. **Recommendation Engine**
   - Semantic search: "Find content about X"
   - Filter by preferences: "Only highly-rated content"
   - Context-aware: "Relevant to my current project"
   - Trend detection: "What's Nate Jones focusing on lately?"

5. **Application Suggester**
   - "You learned X from video Y, could apply to project Z"
   - "Technique from blog A solves problem in feature B"
   - "Similar to what you built in lesson C"

---

## System Architecture

```
┌─────────────────────────────────────────────────────────┐
│          Personal Research Assistant System              │
└─────────────────────────────────────────────────────────┘

┌─────────────────┐
│ Content Sources │
├─────────────────┤
│ • YouTube       │──┐
│ • Blogs         │  │
│ • News          │  │ Ingestion Layer (Lesson 007)
│ • Papers        │  │
│ • Podcasts      │──┘
└─────────────────┘
         │
         ▼
┌─────────────────┐
│ Cache Manager   │
│ (Qdrant)        │──── Content storage with embeddings
│                 │     • Semantic search
│                 │     • Metadata filtering
└─────────────────┘
         │
         ▼
┌─────────────────┐
│ Analysis Layer  │
├─────────────────┤
│ • Tagging       │──── Using existing agents (lessons 001-003)
│ • Summarization │     + Batch processing (Lesson 008)
│ • Extraction    │
└─────────────────┘
         │
         ▼
┌─────────────────┐
│ Memory Layer    │
│ (Mem0/Qdrant)   │──── User preferences, project context
│                 │     • Ratings and feedback
│                 │     • Learning history
└─────────────────┘
         │
         ▼
┌─────────────────┐
│ Recommendation  │
│ Engine          │──── Match content to interests/needs
│                 │     • Preference-based ranking
│                 │     • Context-aware filtering
└─────────────────┘
         │
         ▼
┌─────────────────┐
│ Application     │
│ Suggester       │──── Connect learnings to projects
│                 │     • Pattern matching
│                 │     • Problem-solution mapping
└─────────────────┘
```

---

## Technical Stack

### Core Infrastructure
- **Vector Database**: Qdrant (semantic search, metadata filtering)
- **Memory System**: Mem0 (user preferences, conversation history)
- **Agents**: Pydantic AI (analysis, tagging, summarization)
- **Batch Processing**: OpenAI Batch API (cost-effective large-scale analysis)
- **Embedding Service**: Infinity (CPU-based embedding server, no PyTorch/CUDA in API)
- **Document Processing**: Docling-serve (containerized document conversion)

### Microservices Architecture

The system uses a **microservices pattern** with Docker containers:

```
┌─────────────────────────────────────────────────────────────┐
│                  Microservices Architecture                  │
└─────────────────────────────────────────────────────────────┘

┌───────────────┐
│   API Service │  (FastAPI, lightweight - NO ML dependencies)
│   Port: 8000  │  Build time: ~49 seconds, ~63 packages
└───────┬───────┘
        │
        ├──────────────────────────────────────────┐
        │                                          │
        ▼                                          ▼
┌──────────────┐  HTTP API               ┌──────────────┐
│   Docling    │  (Document conversion)  │   Infinity   │  (Embeddings)
│  Port: 5001  │  4.4 GB image           │ Port: 7997   │  CPU-only, bge-m3
└──────────────┘                         └──────┬───────┘
                                                │
                                                ▼ Vectors (1024-dim)
                                         ┌──────────────┐
                                         │   Qdrant     │  (Vector database)
                                         │ Port: 6335   │  Web UI, persistence
                                         └──────────────┘
```

**Benefits**:
- **Separation of concerns**: Heavy ML workloads isolated from API
- **Independent scaling**: Can scale embedding service separately
- **Fast builds**: API builds in 49s (no PyTorch/CUDA)
- **Portability**: Models stored in Docker volumes, transferable between dev machines

### Embedding Architecture

**Dual-Model Strategy** (see [embedding_pipeline_spec_for_coding_model.md](ideas/Recommendation%20Engine/embedding_pipeline_spec_for_coding_model.md)):

#### Phase 1 (Current): Chunk Embeddings
- **Model**: `BAAI/bge-m3` via Infinity service
- **Context window**: 8,192 tokens (handles 97% of cached videos)
- **Dimension**: 1024
- **Purpose**: Semantic search, chunk-level relevance
- **Collection**: `content_chunks` (future)

#### Phase 2 (Planned): Global + Chunk Embeddings
- **Global model**: `Alibaba-NLP/gte-large-en-v1.5` (whole-document embeddings)
- **Chunk model**: `BAAI/bge-m3` (local semantic search)
- **Collections**: Dual collections in Qdrant
  - `content`: One vector per item (recommendations, preferences)
  - `content_chunks`: Multiple vectors per item (search, Q&A)

**Chunking Strategies**:
- **YouTube**: Time + token hybrid (2-3K tokens, natural pause detection)
- **Web content**: Docling hybrid chunking (respects headings, paragraphs, code blocks)

**Retrieval Modes**:
- **Search**: High chunk weight, find matching passages
- **Recommendation**: High persona weight, match user preferences
- **Application Suggester**: Balanced weights, help with projects

### Content Types
- **YouTube**: Transcripts via youtube-transcript-api
- **Webpages**: Markdown via Docling-serve (HTTP API)
- **PDFs**: (Future) Document parsing via Docling
- **Podcasts**: (Future) Audio transcription

### Analysis Capabilities
- **Tagging**: Multi-label classification
- **Summarization**: Key points extraction
- **Concept Extraction**: Identify techniques, patterns, frameworks
- **Relationship Mapping**: Connect content to projects/problems

---

## Data Models

### Content (Qdrant Collection: "content")

```python
{
    "id": "youtube:i5kwX7jeWL8",
    "vector": [...],  # Semantic embedding of content
    "payload": {
        # Content metadata
        "type": "youtube_video",
        "source": "Nate Jones",
        "title": "Learn 90% of AI Agents in 30 Minutes",
        "url": "https://youtube.com/watch?v=i5kwX7jeWL8",
        "upload_date": "2024-10-15",
        "duration_seconds": 1845,

        # Analyzed content
        "transcript": "...",
        "tags": ["ai", "agents", "pydantic", "multi-agent"],
        "summary": "...",
        "key_concepts": ["tool", "system-prompt", "memory", "llm"],

        # User-specific metadata
        "my_rating": 5,
        "watched_date": "2025-11-01",
        "notes": "Used to build agent-spike project",
        "importance": "high",

        # Relationships
        "inspired_projects": ["agent-spike"],
        "related_content": ["youtube:GTEz5WWbfiw"],
        "applied_techniques": ["dependency-injection", "caching"],
        "solved_problems": ["batch-processing-transcripts"]
    }
}
```

### Preferences (Mem0 or Separate Collection)

```python
{
    "user_id": "mglenn",
    "preferences": {
        "topics": {
            "multi-agent-systems": {"interest": 5, "expertise": 3},
            "python": {"interest": 5, "expertise": 4},
            "prompt-engineering": {"interest": 5, "expertise": 3},
            "caching-strategies": {"interest": 4, "expertise": 3}
        },
        "content_types": {
            "youtube": {"preference": 5},
            "technical_blogs": {"preference": 4},
            "academic_papers": {"preference": 2}
        },
        "sources": {
            "Nate Jones": {"trust": 5, "relevance": 5},
            "Anthropic Blog": {"trust": 5, "relevance": 4}
        },
        "learning_style": "hands-on, project-based"
    },
    "projects": {
        "agent-spike": {
            "status": "active",
            "goals": [
                "learn multi-agent systems",
                "build research assistant",
                "explore caching patterns"
            ],
            "tech_stack": ["python", "pydantic-ai", "qdrant", "mem0"],
            "current_challenges": [
                "batch processing 169 videos",
                "cost-effective analysis"
            ]
        }
    },
    "problems": {
        "scale-video-analysis": {
            "description": "Analyze 169 videos efficiently",
            "context": "Nate Jones corpus for research",
            "potential_solutions": [
                "batch-processing",
                "caching",
                "embeddings",
                "openai-batch-api"
            ],
            "status": "in_progress"
        }
    }
}
```

---

## Development Strategy

### Philosophy: **Evolve Organically + Build Piece by Piece**

Start with immediate needs (caching, batch processing), let the system grow naturally as requirements emerge.

### Planned Lessons

**✅ Lessons 001-006**: Foundation
- 001: YouTube tagging
- 002: Webpage tagging
- 003: Multi-agent coordinator
- 004: Observability
- 005: Security
- 006: Memory (Mem0)

**🚧 Lesson 007: Cache Manager & Content Ingestion** (In Progress)
- Dependency injection pattern
- CacheManager protocol
- Qdrant implementation
- Generic CSV ingestion (supports any URL list)
- Router integration for multi-source content

**📋 Lesson 008: Batch Processing with OpenAI** (Planned)
- OpenAI Batch API integration
- Cost optimization (50% savings)
- Batch job monitoring
- Result aggregation

**💡 Future Capabilities** (As needs emerge)
- Recommendation engine basics
- Preference learning & feedback loops
- Application suggester (connect learnings to projects)
- Streaming & real-time updates
- Cross-content analysis (themes, trends)

**🎯 Judgment & Self-Improvement** (Long-term)
- Outcome tracking for learned capabilities
- Non-goals enforcement (scope control)
- Bottleneck detection and optimization
- Strategic sequencing (thin-slice value)
- Calibration loops (learn from experience)
- Context profiling (recognize patterns)

**See**: [Judgment Integration](ideas/orchestrator/JUDGMENT-INTEGRATION.md) for detailed analysis

---

## Key Architectural Decisions

### 1. Qdrant for Content Storage
**Why**: Already installed (Mem0 dependency), excellent semantic search, flexible schema, local-first

**Alternatives considered**:
- ChromaDB (simpler but less mature, would duplicate vector DB)
- Neo4j (great for relationships but no native vector search)
- SQLite (no semantic search)

**Decision**: Single Qdrant collection "content" with type-based metadata

---

### 2. Dependency Injection for Cache
**Why**: Clean separation of concerns, testable, swappable backends

**Pattern**:
```python
def get_transcript(url: str, cache: Optional[CacheManager] = None) -> str:
    # Tool works with or without cache
    # No hard dependency on cache implementation
```

**Benefits**:
- Lessons work without cache (educational)
- Production gets caching via injection
- Easy to test (inject mock cache)
- Can swap backends without touching tools

---

### 3. Integrated Storage (Mem0 + Qdrant)
**Why**: Mem0 uses Qdrant as backend - leverage same infrastructure

**Model**:
- Mem0 → High-level user preferences and memories
- Direct Qdrant → Content storage with fine-grained control

**Future**: May consolidate to pure Qdrant if Mem0 abstraction becomes limiting

---

### 4. Generic CSV Ingestion
**Why**: Flexibility to process any content list

**Pattern**:
- Minimal required fields: `url` (and optionally `title`)
- Additional CSV columns → stored as metadata
- Router (lesson-003) determines content type
- Appropriate agent handles each URL

**Example**:
```bash
python ingest_csv.py --csv projects/video-lists/nate_jones_videos.csv
```

---

## Success Metrics

### Phase 1: Infrastructure (Lessons 007-008)
- ✅ Can ingest and cache 169+ videos
- ✅ Batch processing reduces cost by 50%
- ✅ Semantic search finds relevant content
- ✅ Metadata filtering works (by date, source, rating)

### Phase 2: Intelligence (Lessons 009-011)
- ✅ Recommendations match user preferences
- ✅ System learns from feedback
- ✅ Can suggest applications to active projects
- ✅ Identifies patterns across content

### Phase 3: Judgment Infrastructure (Post-011)
- ✅ Outcome tracking: Measure success rate, time/cost savings
- ✅ Non-goals registry: Explicit scope control during planning
- ✅ Bottleneck detection: Identify performance constraints
- ✅ Token efficiency: 98%+ reduction vs. traditional approaches

### Phase 4: Strategic Planning (Future)
- ✅ Thin-slice sequencing: MVP → Full feature progression
- ✅ Feasibility scoring: Estimate time/cost/risk before execution
- ✅ Context profiling: Recognize similar situations
- ✅ Planning accuracy: Within 30% of actual outcomes

### Phase 5: Self-Improvement (Long-term)
- ✅ Calibration loops: Adjust predictions based on outcomes
- ✅ Pattern recognition: "This is like X, which succeeded with Y"
- ✅ Compounding value: Track cumulative time/cost savings
- ✅ Measurable improvement: 15%+ success rate increase over 6 months

---

## Example Use Cases

### Use Case 1: Research a Topic
```
User: "Find content about multi-agent orchestration"

System:
1. Semantic search in Qdrant
2. Filter by user rating > 3
3. Rank by relevance + recency
4. Present top 10 with summaries

Output:
- Video: "Multi-Agent Coordination" (Nate Jones, 4.5★)
- Blog: "Agent Orchestration Patterns" (Anthropic, 5★)
- ...
```

### Use Case 2: Solve a Problem
```
User: "I need to coordinate 3 agents for parallel processing"

System:
1. Search content for "agent coordination" + "parallel"
2. Cross-reference with projects (agent-spike)
3. Check what was already applied

Output:
- "Video X covered this pattern (15:30 timestamp)"
- "You applied similar in lesson-003 coordinator"
- "Suggested approach: Use async/await + gather()"
- "Related: Lesson-008 batch processing"
```

### Use Case 3: Discover Patterns
```
User: "What has Nate Jones been focusing on lately?"

System:
1. Filter content by source="Nate Jones"
2. Sort by upload_date DESC
3. Aggregate tags from recent videos
4. Compare to historical topics

Output:
- "Recent shift: More prompt engineering content"
- "Emerging topics: Tool-augmented AI, master prompters"
- "Consistent themes: Practical AI, business applications"
```

### Use Case 4: Apply Learning
```
User: "How can I improve the agent-spike project?"

System:
1. Load project goals and challenges
2. Search content for solutions
3. Match learned techniques to current needs

Output:
- "Video on streaming responses → Could add to lesson-007"
- "Blog on cost optimization → OpenAI batch API (lesson-008)"
- "Pattern: Dependency injection → Already applied in lesson-007!"
```

---

## Current Status

**Phase**: Foundation building (Lessons 007-008)

**Immediate Goal**:
- Build cache infrastructure (Lesson 007)
- Ingest Nate Jones videos (169 transcripts)
- Batch tag with OpenAI (Lesson 008)

**Next 30 Days**:
- Complete lesson-007 (CacheManager + ingestion)
- Complete lesson-008 (batch processing)
- Have searchable corpus of Nate's content
- Begin exploring recommendation patterns

**Long-Term** (3-6 months):
- Full recommendation engine
- Application suggester
- Multi-source monitoring
- Automated research assistant

---

## Open Questions

### Infrastructure & Architecture
1. **Memory integration**: How should Mem0 preferences relate to Qdrant content?
2. **Relationship modeling**: Do we need graph capabilities, or is metadata sufficient?
3. **Feedback loops**: How to capture user ratings and improve recommendations?
4. **Automation**: When/how should the system proactively fetch new content?
5. **Cross-project**: Should this system work across multiple projects, or just agent-spike?

### Judgment & Self-Improvement
6. **Judgment agent scope**: Separate agent for planning vs. integrated into coordinator?
7. **User approval**: Auto-execute judgment recommendations or require approval?
8. **Calibration data**: How many outcomes needed before predictions are reliable?
9. **Non-goal evolution**: Is changing non-goals failure (scope creep) or learning (priorities shifted)?
10. **Model selection**: Use Sonnet for judgment quality or Haiku for cost efficiency?

---

## References

### Inspiration
- **Nate Jones**: "Learn 90% of AI Agents in 30 Minutes" - Foundation for lessons 001-006
- **Nate Jones**: "The Mental Models of Master Prompters" - Inspired prompt engineering skill
- **Nate Jones**: "Judgment Merchants in the Age of AI" - Framework for self-improving systems (see [Judgment Integration](ideas/orchestrator/JUDGMENT-INTEGRATION.md))

### Technical Resources
- [Pydantic AI Documentation](https://ai.pydantic.dev/)
- [Qdrant Documentation](https://qdrant.tech/documentation/)
- [Mem0 Documentation](https://docs.mem0.ai/)
- [OpenAI Batch API](https://platform.openai.com/docs/guides/batch)

### Project Files
- **STATUS.md**: Current progress and lesson completions
- **CLAUDE.md**: Project-specific development guidelines
- **~/.claude/CLAUDE.md**: Personal preferences and patterns
- **ideas/orchestrator/**: Self-evolving orchestrator design documents
  - **JUDGMENT-INTEGRATION.md**: Framework for building self-improving systems with judgment principles

---

**Last Updated**: 2025-01-10 - Added judgment integration framework to long-term roadmap
