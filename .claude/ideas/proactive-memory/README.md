# Proactive Memory Systems Research

**Created**: 2025-01-24
**Status**: Research & Planning
**Related**: [VISION.md](../../VISION.md), Lesson 006 (Memory), Lesson 007 (Cache Manager)

---

## Executive Summary

This document synthesizes research on **proactive memory systems** that automatically resurface relevant information at the right time. These systems go beyond simple retrieval—they anticipate what you need based on context, patterns, and intent.

**Key Finding**: Open-source alternatives (Mem0, MemOS) often **outperform commercial solutions** (Mem.ai) and provide full implementation details we can leverage.

**Primary Use Case for Agent-Spike**: Build a recommendation engine that proactively surfaces:
- Content relevant to current project work
- Techniques applicable to active challenges
- Patterns connecting past learnings to present needs
- Resurfaced insights from previously consumed content

---

## The Landscape

### 1. Commercial: Mem.ai "Mem 2.0"

**What They Do**:
- AI-powered note-taking and knowledge management
- Proactively surfaces related notes as you type
- "Brings content back exactly when needed"
- Funded by a16z + OpenAI Startup Fund ($28.6M)

**Team**:
- **Kevin Moody** (CEO) - Former Google PM, Stanford CS '17
- **Dennis Xu** (Co-founder) - Former Yelp PM, Stanford CS '17

**Technical Approach** (limited public details):
- Dual embeddings per document (OpenAI similarity + search models)
- Pinecone vector database for storage
- Proprietary re-ranking, clustering, and length normalization algorithms
- Real-time embedding updates as content changes
- Metadata filtering for access control

**Problem**: Closed-source, proprietary algorithms not published

**References**:
- [Building the Self-Organizing Workspace (Pinecone)](https://www.pinecone.io/learn/series/wild/mem-semantic-search/)
- [Why We Started Mem](https://newsletter.mem.ai/p/why-we-started-mem)
- [Investing in Mem (a16z)](https://a16z.com/announcement/investing-in-mem/)

---

### 2. Open Source: Mem0 (What We Already Use)

**Paper**: [Mem0: Building Production-Ready AI Agents with Scalable Long-Term Memory](https://arxiv.org/abs/2504.19413) (April 2025)

**Authors**: Chhikara, Prateek; Khant, Dev; Aryan, Saket; Singh, Taranjeet; Yadav, Deshraj

**Architecture**:

#### Two-Phase Processing Pipeline
1. **Extraction Phase**:
   - Processes new message pair + context (conversation summary + recent messages)
   - LLM extracts candidate memories from the exchange
   - Background module asynchronously refreshes long-term summary

2. **Update Phase**:
   - Evaluates each candidate fact against existing memories
   - Retrieves semantically similar memories via vector embeddings
   - LLM determines operation: ADD, UPDATE, DELETE, or NOOP
   - Ensures consistency and avoids redundancy

#### Hybrid Storage System
- **Vector Store**: Numerical representations for semantic search
- **Graph Store**: Relationships between entities, people, concepts
- **Key-Value Store**: Quick access to structured data (facts, preferences)

#### Smart Retrieval
- Semantic search enhanced with scoring layer
- Factors: relevance, importance, **recency**
- Multi-level memory: user, session, agent

#### Mem0g: Graph Enhancement
- Stores memories as directed labeled graph
- Nodes = entities (people, locations, objects)
- Edges = relationships with semantic types
- Captures complex relational structures

**Performance**:
- **26% better accuracy** than OpenAI Memory (LOCOMO benchmark)
- **91% lower p95 latency**
- **90% token cost savings**

**Source**: [github.com/mem0ai/mem0](https://github.com/mem0ai/mem0) (Apache 2.0 license)

**Current Status in Agent-Spike**: Used in Lesson 006, not yet integrated with SurrealDB cache

---

### 3. Open Source: MemOS (Superior Performance)

**Papers**:
- [MemOS: A Memory OS for AI System](https://arxiv.org/abs/2507.03724)
- [MemOS: An Operating System for Memory-Augmented Generation](https://arxiv.org/abs/2505.22101)

**Architecture: "MemCube"**

Three distinct memory types:

1. **Textual Memory**: Unstructured/structured knowledge retrieval
   - What we'd use for content storage (videos, blogs, papers)
   - Semantic search and relevance ranking

2. **Activation Memory**: KV-Cache pairs for fast LLM inference
   - Reuses context across similar queries
   - Massive speedup for repeated patterns

3. **Parametric Memory**: Model adaptation parameters (LoRA weights)
   - Fine-tuning without full retraining
   - Personalization at the model level

**Unified API**: Memory-Augmented Generation (MAG) with consistent operations across all memory types

**Performance vs Mem0**:

| Benchmark | Mem0 | MemOS | Improvement |
|-----------|------|-------|-------------|
| LOCOMO | 52.8 | 75.8 | **+43.7%** |
| LongMemEval | 55.4 | 77.8 | **+40.4%** |
| PrefEval-10 | 2.7 | 71.9 | **+2568%** (!!!) |
| PersonaMem | 43.5 | 61.2 | **+40.8%** |

**Key Insight**: The **PrefEval-10** score (personalized preference responses) is where MemOS dominates. This is exactly what we need for recommendation engines.

**Source**: [github.com/MemTensor/MemOS](https://github.com/MemTensor/MemOS)

---

### 4. Research Papers: Proactive Memory Strategies

These papers specifically address **when and how to resurface information**:

#### MemInsight: Autonomous Memory Augmentation (2025)
[arXiv:2503.21760](https://arxiv.org/abs/2503.21760)

**Key Contribution**: LLM agents **proactively identify critical information** during interactions

**Approach**:
- Autonomous proposal of effective memory attributes
- Self-directed memory enhancement (no manual curation)
- Learns what's important through agent's own experience
- Supports agent adaptability and self-evolution

**Relevance to Agent-Spike**:
- Auto-tag content with importance scores
- Learn which content types/sources are most useful
- Identify patterns in what gets referenced vs. ignored

---

#### PRINCIPLES: Synthetic Strategy Memory (2025)
[arXiv:2509.17459](https://arxiv.org/abs/2509.17459)

**Key Contribution**: Strategy memory derived from **offline self-play simulations**

**Approach**:
- Simulates interactions to build reusable knowledge
- Stores "principles" rather than raw facts
- Guides future strategy planning proactively
- Evaluated in emotional support and persuasion domains

**Relevance to Agent-Spike**:
- Build "principles" from consumed content (e.g., "Use batch APIs for cost optimization")
- Store generalized strategies, not just specific examples
- Proactively suggest strategies when patterns match

---

#### Proactive Conversational Agents with Inner Thoughts (2025)
[arXiv:2501.00383](https://arxiv.org/abs/2501.00383)

**Key Contribution**: Simulates **internal thought stream** parallel to external conversation

**Approach**:
- Ongoing "inner thoughts" that mirror human covert responses
- Self-initiated actions based on internal reasoning
- Proactive engagement without explicit prompting
- Distinguishes between internal deliberation and external action

**Relevance to Agent-Spike**:
- Agent maintains "awareness" of project context
- Proactively notices connections ("This video relates to your current challenge")
- Surfaces insights without explicit search queries
- Background processing that anticipates needs

---

#### MemGuide: Intent-Driven Memory Selection (2025)
[arXiv:2505.20231](https://arxiv.org/abs/2505.20231)

**Key Contribution**: **Two-stage intent-driven memory selection**

**Approach**:
- Stage 1: Infer user intent from context
- Stage 2: Select memories based on inferred intent
- Proactive strategy minimizes conversational turns
- Goal-oriented multi-session agent design

**Relevance to Agent-Spike**:
- Understand *why* user is searching (research? solve problem? learn technique?)
- Adjust retrieval strategy based on intent
- Minimize back-and-forth ("Here's what you probably need next")

---

#### ProAgent: Proactive Cooperative Agents (2024)
[arXiv:2308.11339](https://arxiv.org/abs/2308.11339)

**Key Contribution**: Framework for **coordination with novel agents**

**Modules**:
- **Planner**: Anticipates future states
- **Verificator**: Checks plan validity
- **Controller**: Executes actions
- **Memory**: Learns from past coordinations

**Relevance to Agent-Spike**:
- Multi-agent orchestration (Lesson 009)
- Proactive coordination between agents
- Memory-informed planning

---

## Application to Agent-Spike Vision

### Current Architecture (Lesson 006-007)

```
Content (SurrealDB) → Analysis (Agents) → Memory (Mem0)
                           ↓
                    User preferences
                    Project context
                    Learning history
```

**Gap**: No proactive resurfacing mechanism yet

---

### Proposed Enhancement: Proactive Recommendation Layer

```
┌─────────────────────────────────────────────────────────┐
│          Proactive Memory & Recommendation System        │
└─────────────────────────────────────────────────────────┘

┌─────────────────┐
│ Content Sources │
│  (SurrealDB)    │  Content embeddings (bge-m3)
│                 │  Metadata, tags, summaries
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ Memory Layer    │  Mem0 or MemOS
│                 │  User preferences, project context
│                 │  "Inner thoughts" context tracking
└────────┬────────┘
         │
         ▼
┌─────────────────────────────────────────────────────────┐
│            Proactive Resurfacing Engine                  │
├─────────────────────────────────────────────────────────┤
│                                                          │
│  1. Context Monitor (Inner Thoughts)                    │
│     - Track current project work (git commits, files)   │
│     - Monitor active challenges (STATUS.md, TODOs)      │
│     - Maintain "awareness" of user intent               │
│                                                          │
│  2. Intent Inference (MemGuide)                         │
│     - Why is user searching? (research, solve, learn)   │
│     - What project needs support?                       │
│     - What's the current bottleneck?                    │
│                                                          │
│  3. Strategy Memory (PRINCIPLES)                        │
│     - Extract "principles" from content                 │
│     - Match current situation to past strategies        │
│     - Suggest approaches, not just content              │
│                                                          │
│  4. Autonomous Memory Curation (MemInsight)             │
│     - Learn what content types are most useful          │
│     - Auto-tag importance and applicability             │
│     - Self-evolving relevance scores                    │
│                                                          │
│  5. Retrieval with Scoring                              │
│     - Semantic similarity (embeddings)                  │
│     - Recency weighting (recent content higher)         │
│     - Importance (user ratings + auto-learned)          │
│     - Context relevance (project match)                 │
│     - Application potential (solves active challenge)   │
│                                                          │
└─────────────────────────────────────────────────────────┘
         │
         ▼
┌─────────────────┐
│ User Interface  │
│                 │  Proactive suggestions
│                 │  "You learned X, could apply to Y"
│                 │  "This relates to your current work"
└─────────────────┘
```

---

### Specific Features to Build

#### Feature 1: Context-Aware Recommendations

**Scenario**: User is working on batch processing (lesson-008)

**Proactive Behavior**:
- Monitor file edits in `lessons/lesson-008/`
- Notice batch processing patterns
- Surface: "Video at 12:45 discusses OpenAI Batch API optimization"
- Surface: "You watched similar content 3 weeks ago (rating: 5)"

**Implementation**:
- File watcher on project directories
- Match current work to content via embeddings
- Weight by: semantic similarity + user rating + recency

**Relevant Research**: Inner Thoughts (context monitoring), MemGuide (intent inference)

---

#### Feature 2: Strategy Suggestion

**Scenario**: User adds TODO: "Reduce embedding costs"

**Proactive Behavior**:
- Detect new challenge via STATUS.md monitoring
- Search content for "cost optimization" + "embeddings"
- Extract strategies (not just content references):
  - "Use smaller models for less critical tasks"
  - "Batch requests to reduce API overhead"
  - "Cache embeddings aggressively"
- Present: "Found 3 strategies from your content library"

**Implementation**:
- Extract "principles" from content during analysis
- Store as structured knowledge (not just embeddings)
- Match problems to strategies via semantic + keyword

**Relevant Research**: PRINCIPLES (strategy memory), MemInsight (importance detection)

---

#### Feature 3: Application Mapper

**Scenario**: User watches video on "prompt caching"

**Proactive Behavior**:
- After analysis, agent thinks: "This relates to lesson-004 (observability) and lesson-007 (cache manager)"
- Suggests: "Could apply prompt caching to reduce costs in YouTube agent"
- Creates link: video → lesson-001 (application opportunity)

**Implementation**:
- Cross-reference new content with existing projects
- Maintain graph of content → projects → opportunities
- Background job: "What could I apply from recent content?"

**Relevant Research**: Mem0g (graph relationships), ProAgent (coordination)

---

#### Feature 4: Autonomous Importance Learning

**Scenario**: User rates videos, skips content, applies techniques

**Proactive Behavior**:
- Learns: "Videos from Nate Jones on multi-agent systems = high value"
- Learns: "Academic papers = low engagement, lower priority"
- Learns: "Content applied to projects = most valuable"
- Auto-adjusts future recommendations

**Implementation**:
- Track: views, ratings, applications, revisits
- Learn source/topic/format preferences
- Adjust retrieval scoring dynamically
- Periodic "calibration": compare predictions to outcomes

**Relevant Research**: MemInsight (autonomous learning), MemOS (PrefEval)

---

#### Feature 5: Temporal Resurfacing

**Scenario**: User worked on multi-agent coordination 2 months ago

**Proactive Behavior**:
- Detect: User starting new multi-agent work
- Resurface: "You solved similar in lesson-003, here's what you learned"
- Resurface: "3 videos you rated highly on this topic"
- Suggest: "Review these notes before starting"

**Implementation**:
- Vector search weighted by time decay (recent + distant past)
- Match current project phase to historical phases
- Explicitly surface "you did this before"

**Relevant Research**: Mem0 (recency scoring), MemGuide (multi-session)

---

## Technical Recommendations

### Short-Term (Lesson 008-009)

**Goal**: Get proactive recommendations working with existing infrastructure

1. **Extend Mem0 Integration** (Lesson 006 + 007)
   - Store user ratings in Mem0
   - Track content → project relationships
   - Add recency + importance scoring to retrieval

2. **Build Context Monitor**
   - Watch file changes in lessons/
   - Parse STATUS.md for active challenges
   - Detect patterns in git commits

3. **Simple Proactive Retrieval**
   - Background job: "What content relates to current work?"
   - Semantic search: current work context → content library
   - Weekly summary: "Based on your work, here's relevant content"

**Estimated Effort**: 1-2 weeks, builds on existing lessons

---

### Medium-Term (Lesson 010-011)

**Goal**: Add strategy memory and application mapping

1. **Extract Principles from Content**
   - During analysis (lesson-001, 002), extract:
     - Techniques ("use batch APIs")
     - Patterns ("dependency injection for testability")
     - Strategies ("cache expensive operations")
   - Store as structured knowledge graph

2. **Application Mapper Agent**
   - Background agent: "What could apply to active projects?"
   - Graph traversal: content → principles → projects
   - Proactive suggestions in daily/weekly digest

3. **Enhanced Preference Learning**
   - Track: what gets applied, what gets ignored
   - Learn: effective content characteristics
   - Auto-adjust importance scores

**Estimated Effort**: 2-3 weeks, new capabilities

---

### Long-Term (Post-Lesson 011)

**Goal**: Autonomous, self-improving proactive memory system

1. **Upgrade to MemOS**
   - Evaluate MemOS for superior preference handling
   - Implement MemCube architecture:
     - Textual: Content library (already have with SurrealDB)
     - Activation: Cache LLM contexts for similar queries
     - Parametric: Fine-tune models on user's domain

2. **Inner Thoughts Implementation**
   - Background agent with persistent context
   - Maintains "awareness" of project state
   - Self-initiated resurfacing (not query-driven)
   - Thinks: "User is stuck on X, here's relevant Y"

3. **Multi-Modal Proactive Surfacing**
   - Not just content recommendations
   - Proactive debugging: "Similar error solved in lesson-005"
   - Proactive refactoring: "Pattern from video X applies here"
   - Proactive learning: "Good time to learn Y given current knowledge"

4. **Calibration & Self-Improvement**
   - Track: predictions vs. outcomes
   - Measure: did suggestion help? was content applied?
   - Learn: improve scoring algorithms over time
   - Report: "Recommendation accuracy up 15% this month"

**Estimated Effort**: 1-2 months, research-grade system

---

## Integration with Existing VISION.md Components

### Memory Layer (Current: Mem0)

**Enhancements**:
- Add scoring layer: relevance + importance + recency + applicability
- Store content → project → application relationships
- Track temporal patterns (when was topic last relevant?)

**Consider**: Migrate to MemOS for superior preference handling

**References**: VISION.md lines 106-110, 255-307

---

### Cache Manager (Lesson 007)

**Enhancements**:
- Store not just content, but:
  - Extracted principles/strategies
  - Application opportunities
  - User engagement metrics (views, ratings, applications)

**Current**: SurrealDB with vector indexes
**Future**: Add graph edges for relationships

**References**: VISION.md lines 89-93, 328-333

---

### Recommendation Engine (Planned: Lesson 010+)

**Core Algorithm** (borrowing from research):

```python
def proactive_score(content, context):
    """
    Multi-factor scoring for proactive resurfacing

    Factors (weighted):
    - Semantic similarity to current work (MemGuide: intent-driven)
    - User rating/engagement (MemOS: PrefEval)
    - Recency (Mem0: time decay)
    - Application potential (PRINCIPLES: strategy match)
    - Importance (MemInsight: autonomous learning)
    """
    score = 0.0

    # 1. Semantic similarity (30%)
    score += 0.3 * cosine_similarity(
        content.embedding,
        context.current_work_embedding
    )

    # 2. User preference (25%)
    score += 0.25 * normalize(content.user_rating)

    # 3. Recency (15%)
    days_old = (now - content.watched_date).days
    score += 0.15 * exp(-days_old / 30)  # 30-day half-life

    # 4. Application potential (20%)
    if content.has_applicable_strategy(context.active_challenges):
        score += 0.2

    # 5. Learned importance (10%)
    score += 0.1 * content.auto_learned_importance

    return score
```

**References**: VISION.md lines 114-118, 456-500

---

### Application Suggester (Planned: Future)

**Implementation** (borrowing from research):

1. **Build Strategy Graph** (PRINCIPLES)
   - Extract: techniques, patterns, principles from content
   - Store: content → strategy → applicable_problems
   - Example: "Batch API" → "Cost reduction" → "Large-scale analysis"

2. **Match to Active Challenges** (MemGuide)
   - Parse: STATUS.md, TODOs, git commit messages
   - Infer: current bottlenecks and goals
   - Search: strategies that solve these problems

3. **Proactive Suggestions** (Inner Thoughts)
   - Background agent monitors project state
   - Self-initiates when match found
   - Presents: "Video X (15:30) covers solution to current challenge"

**References**: VISION.md lines 122-126, 502-515

---

## Comparison: Mem0 vs. MemOS for Agent-Spike

| Dimension | Mem0 (Current) | MemOS (Alternative) |
|-----------|----------------|---------------------|
| **License** | Apache 2.0 | Not specified in research |
| **Integration** | Already in Lesson 006 | Would require migration |
| **Performance** | Good (26% over OpenAI) | Excellent (40%+ over Mem0) |
| **Preference Learning** | Basic (facts + relationships) | **Superior** (PrefEval: +2568%) |
| **Architecture** | Vector + Graph + KV | **MemCube** (Textual + Activation + Parametric) |
| **Proactive Support** | Semantic search + scoring | **Unified MAG API** + caching |
| **Complexity** | Moderate | Higher (3 memory types) |
| **Maturity** | Production-ready | Research-grade (2025) |
| **Use Case Fit** | Good for facts + relationships | **Ideal for recommendations** |

**Recommendation**:
- **Short-term**: Enhance Mem0 with proactive scoring (easier, builds on existing)
- **Medium-term**: Evaluate MemOS for recommendation engine (better performance)
- **Long-term**: Hybrid approach (Mem0 for facts, MemOS for preferences/recommendations)

---

## Implementation Priorities

### Phase 1: Foundation (Now - Lesson 008)
**Goal**: Get basic proactive retrieval working

- [ ] **Context monitoring**: Watch file changes, parse STATUS.md
- [ ] **Enhanced Mem0 scoring**: Add recency + importance + applicability
- [ ] **Simple recommendations**: "Content related to current work"
- [ ] **User feedback loop**: Rating system, track applications

**Effort**: 1-2 weeks
**Risk**: Low (extends existing systems)
**Value**: High (immediate utility)

---

### Phase 2: Strategy Memory (Lesson 009-010)
**Goal**: Extract and apply principles

- [ ] **Principle extraction**: During content analysis, extract strategies
- [ ] **Strategy graph**: Link content → principles → problems
- [ ] **Application mapper**: Match strategies to active challenges
- [ ] **Proactive suggestions**: "You could apply X to Y"

**Effort**: 2-3 weeks
**Risk**: Medium (new agent capabilities)
**Value**: Very High (core vision feature)

---

### Phase 3: Autonomous Learning (Lesson 011+)
**Goal**: Self-improving system

- [ ] **MemInsight implementation**: Auto-learn importance
- [ ] **Calibration loop**: Track predictions vs. outcomes
- [ ] **Adaptive scoring**: Adjust weights based on feedback
- [ ] **Inner thoughts**: Background agent with persistent context

**Effort**: 3-4 weeks
**Risk**: Medium-High (research territory)
**Value**: Very High (differentiation)

---

### Phase 4: Advanced (Post-Lesson 011)
**Goal**: Research-grade proactive memory

- [ ] **Evaluate MemOS**: Test for preference learning
- [ ] **Multi-modal surfacing**: Debug, refactor, learn suggestions
- [ ] **Temporal reasoning**: "Good time to revisit X"
- [ ] **Cross-project**: Apply learnings across multiple projects

**Effort**: 1-2 months
**Risk**: High (cutting-edge research)
**Value**: Extreme (novel capabilities)

---

## Key Takeaways

### 1. Open Source > Commercial
- Mem.ai keeps algorithms proprietary
- Mem0, MemOS, and research papers provide full details
- Often better performance + complete transparency

### 2. Proactive = Multi-Factor Scoring
- Not just semantic similarity
- Combine: relevance + recency + importance + applicability + user preference
- Weight factors based on context (search vs. recommendation vs. application)

### 3. "Resurfaces Data Later" = Intent-Driven Retrieval
- Understand *why* user needs information (MemGuide)
- Maintain background context awareness (Inner Thoughts)
- Match current state to past learnings (PRINCIPLES)
- Autonomous importance detection (MemInsight)

### 4. Strategy > Content
- Store principles, not just references
- "Use batch APIs for cost optimization" > "Video X mentioned batch APIs"
- Enables proactive suggestion without explicit search

### 5. Self-Improvement is Key
- Track: what gets applied, what gets ignored
- Learn: effective content characteristics
- Calibrate: adjust scoring over time
- Report: measurable improvement

### 6. Graph + Vector = Powerful
- Vector: Semantic similarity, content retrieval
- Graph: Relationships, application mapping, strategy matching
- Together: "Content X → Strategy Y → Solves Problem Z in Project W"

---

## Next Steps

### Immediate (This Week)
1. **Review**: Share this document, discuss priorities
2. **Decide**: Enhance Mem0 or evaluate MemOS?
3. **Plan**: Which features in Phase 1 to implement first?

### Short-Term (Lesson 008-009)
1. **Implement**: Context monitoring (file watcher, STATUS.md parser)
2. **Extend**: Mem0 with proactive scoring algorithm
3. **Test**: Basic recommendations ("content related to current work")
4. **Gather**: User feedback to calibrate scoring

### Medium-Term (Lesson 010-011)
1. **Build**: Strategy extraction during content analysis
2. **Create**: Application mapper agent
3. **Integrate**: Proactive suggestions into workflow
4. **Evaluate**: MemOS for superior preference learning

### Long-Term (Post-Lesson 011)
1. **Implement**: Inner thoughts background agent
2. **Add**: Multi-modal proactive surfacing
3. **Build**: Calibration and self-improvement loops
4. **Research**: Novel proactive memory techniques

---

## References

### Papers
- [Mem0: Building Production-Ready AI Agents](https://arxiv.org/abs/2504.19413)
- [MemOS: A Memory OS for AI System](https://arxiv.org/abs/2507.03724)
- [MemInsight: Autonomous Memory Augmentation](https://arxiv.org/abs/2503.21760)
- [PRINCIPLES: Synthetic Strategy Memory](https://arxiv.org/abs/2509.17459)
- [Proactive Conversational Agents with Inner Thoughts](https://arxiv.org/abs/2501.00383)
- [MemGuide: Intent-Driven Memory Selection](https://arxiv.org/abs/2505.20231)
- [ProAgent: Building Proactive Cooperative Agents](https://arxiv.org/abs/2308.11339)

### Open Source
- [Mem0 GitHub](https://github.com/mem0ai/mem0)
- [MemOS GitHub](https://github.com/MemTensor/MemOS)
- [OpenMemory GitHub](https://github.com/CaviraOSS/OpenMemory)
- [Memori GitHub](https://github.com/GibsonAI/Memori)

### Commercial
- [Mem.ai Homepage](https://get.mem.ai/)
- [Building the Self-Organizing Workspace (Pinecone)](https://www.pinecone.io/learn/series/wild/mem-semantic-search/)
- [Why We Started Mem](https://newsletter.mem.ai/p/why-we-started-mem)
- [Investing in Mem (a16z)](https://a16z.com/announcement/investing-in-mem/)

### Related Agent-Spike Docs
- [VISION.md](../../VISION.md)
- [STATUS.md](../../STATUS.md)
- [Lesson 006: Memory (Mem0)](../../../lessons/lesson-006/)
- [Lesson 007: Cache Manager](../../../lessons/lesson-007/)
- [Judgment Integration](../orchestrator/JUDGMENT-INTEGRATION.md)

---

**Last Updated**: 2025-01-24
**Status**: Research complete, ready for implementation planning
