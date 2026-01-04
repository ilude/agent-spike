# Applying Recursive Language Models to agent-spike

**Based on**: Zhang, Kraska, Khattab (2025) - Recursive Language Models (arXiv 2512.24601)

---

## TL;DR

The RLM paper provides **academic validation** for our planned orchestrator architecture. Our design (IPython kernel + `call_subagent()`) is essentially the same pattern they describe. The paper offers concrete implementation details we can adopt.

---

## Architecture Alignment

| RLM Paper | Our Orchestrator Design | Notes |
|-----------|------------------------|-------|
| Python REPL environment | IPython kernel | Same pattern |
| `context` variable (external to LLM) | Variables in kernel namespace | Same pattern |
| `llm_query(prompt)` function | `call_subagent(agent, task)` | Same pattern |
| `print()` to observe results | Execution output capture | Same pattern |
| `FINAL(answer)` termination | Task completion signal | We need this |
| Root LM + Sub-LM hierarchy | Orchestrator + specialist agents | Same pattern |

**Key insight**: We independently arrived at the same architecture. The paper validates our approach and provides benchmarks showing it works at scale (10M+ tokens).

---

## Concrete Implementation Ideas

### 1. Adopt FINAL/FINAL_VAR Termination Pattern

**Paper approach**:
```python
# Direct answer return
FINAL("The answer is 42")

# Return complex data from variable
results = aggregate_all_chunks()
FINAL_VAR(results)
```

**Our application**: Add explicit termination signals to orchestrator:
```python
# In orchestrator system prompt
"""
When you have the final answer:
- FINAL(answer) - return simple text answer
- FINAL_VAR(variable_name) - return complex data from kernel

This signals task completion and prevents unnecessary extra steps.
"""
```

**Benefit**: Cleaner task boundaries, prevents over-iteration.

---

### 2. Model Hierarchy for Cost Optimization

**Paper approach**:
- Root LM (GPT-5): Orchestrates, sees metadata only
- Sub-LM (GPT-5-mini): Processes chunks (~500K chars each)

**Our application**:
```
Orchestrator (Claude Opus/Sonnet)
├── YouTube Agent (Haiku) - transcript processing
├── Webpage Agent (Haiku) - content extraction
├── Embedding Agent (local/Infinity) - vector ops
└── Synthesis Agent (Sonnet) - complex reasoning
```

**Cost implications**:
- Route 90% of work to Haiku ($0.25/1M vs $3/1M for Sonnet)
- Reserve Sonnet/Opus for orchestration decisions and final synthesis
- Paper shows median RLM cost ≤ base model cost despite extra calls

---

### 3. Code-Based Filtering Without Reading Content

**Paper observation**: LLMs can filter context using priors (keywords, patterns) without actually reading the content:

```python
# Model writes this to search large context
keywords = ["machine learning", "neural network", "transformer"]
results = {kw: context.count(kw) for kw in keywords}
relevant_sections = find_snippets(context, keywords, window=500)
```

**Our application for video archive**:
```python
# Orchestrator filters 1000+ videos without loading transcripts
def find_relevant_videos(query: str) -> list[str]:
    # Use metadata search first
    candidates = search_titles_and_tags(query)  # Fast, no embeddings

    # Only load transcripts for top candidates
    if len(candidates) > 50:
        # Let LLM generate search terms from query
        search_terms = llm_query(f"Generate 5 search keywords for: {query}")
        candidates = filter_by_transcript_keywords(candidates, search_terms)

    return candidates[:20]  # Return top 20 for detailed analysis
```

**Benefit**: Massive cost reduction for large archive queries.

---

### 4. Chunking Strategies from Paper

**Paper shows three emergent patterns**:

1. **Uniform chunking** - Split by lines/chars for systematic processing
2. **Semantic chunking** - Split by structure (sections, paragraphs)
3. **Relevance-first chunking** - Filter then chunk (most efficient)

**Our application**:
```python
# For transcript processing
def process_long_transcript(transcript: str, query: str):
    # Relevance-first: filter to relevant sections
    relevant = keyword_filter(transcript, extract_keywords(query))

    # Then chunk remaining content
    chunks = split_by_natural_breaks(relevant, max_chars=50000)

    # Process each chunk with sub-LM
    results = []
    for chunk in chunks:
        result = llm_query(f"Extract info about '{query}' from:\n{chunk}")
        results.append(result)

    # Aggregate
    return synthesize(results)
```

---

### 5. Variable Storage for Multi-Step Tasks

**Paper pattern**: Use REPL variables to accumulate results across many steps:

```python
# Build answer incrementally
all_insights = []
for video_id in relevant_videos:
    transcript = load_transcript(video_id)
    insight = llm_query(f"Extract key insight: {transcript[:50000]}")
    all_insights.append({"video": video_id, "insight": insight})

# Return accumulated variable
FINAL_VAR(all_insights)
```

**Our application**: IPython kernel already supports this. Orchestrator should:
1. Create accumulator variables for multi-video queries
2. Populate incrementally via sub-agent calls
3. Use `FINAL_VAR` to return complex structures

---

### 6. Answer Verification Pattern

**Paper finding**: Sub-LMs can verify answers in fresh context (avoids "context rot"):

```python
# After finding candidate answer
answer = "The technique is called attention masking"
evidence = relevant_chunk[:5000]

# Verify with fresh sub-LM call (no accumulated context rot)
verification = llm_query(f"""
Verify this answer is correct:
Answer: {answer}
Evidence: {evidence}
Respond: CORRECT or INCORRECT with explanation
""")
```

**Our application**: Add verification step for high-stakes queries:
- Recommendation synthesis
- Multi-source aggregation
- Factual claims from transcripts

---

## Integration with Existing Plans

### Application Suggester (from PRD)

The RLM approach enhances our planned Application Suggester:

```
Current plan: Match YouTube insights → user's active projects
RLM enhancement:
1. Load project context as kernel variable (not in LLM context)
2. Stream video insights through keyword filter
3. Only invoke LLM for promising matches
4. Accumulate suggestions in variable
5. Final synthesis pass on top candidates
```

**Expected benefit**: 10x more videos scanned per query at same cost.

### Embedding Pipeline (from spec)

The paper complements our dual-model embedding strategy:

```
Global embeddings (gte-large): For initial filtering
Chunk embeddings (bge-m3): For detailed retrieval
RLM addition: Code-based filtering BEFORE embedding lookup
```

**Flow**:
1. User query → extract keywords (cheap)
2. Keyword filter on metadata (free)
3. Embedding search on filtered set (moderate cost)
4. RLM-style chunk processing on top results (targeted cost)

---

## What We Can Skip

The paper also shows what **doesn't** help:

1. **Deep recursion** (depth > 1): Paper only tested depth=1, no evidence deeper helps
2. **Async parallelism**: Paper notes this as future work, not implemented
3. **Training for RLM**: Paper uses off-the-shelf models, no fine-tuning needed

---

## Recommended Implementation Order

1. **Add FINAL/FINAL_VAR termination** to orchestrator system prompt
2. **Implement keyword pre-filtering** for archive queries
3. **Add verification step** for synthesis queries
4. **Test model hierarchy** (Haiku for chunks, Sonnet for orchestration)
5. **Measure cost vs accuracy** on real queries

---

## Key Metrics to Track (from paper)

- **Tokens processed per query** (target: 10M+ capability)
- **Cost per query** (target: ≤ base model cost)
- **Accuracy on information-dense tasks** (target: 50%+ improvement)
- **Sub-call count per query** (watch for runaway recursion)

---

## References

- Paper: `.claude/ideas/recursive-language-models/2512.24601.pdf`
- Summary: `.claude/ideas/recursive-language-models/SUMMARY.md`
- Our orchestrator design: `.claude/ideas/orchestrator/ARCHITECTURE.md`
- Embedding pipeline spec: `.claude/ideas/Recommendation Engine/embedding_pipeline_spec_for_coding_model.md`
