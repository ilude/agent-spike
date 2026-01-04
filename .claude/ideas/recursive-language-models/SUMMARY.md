# Recursive Language Models - Paper Summary

**Paper**: Recursive Language Models
**Authors**: Alex L. Zhang, Tim Kraska, Omar Khattab (MIT CSAIL)
**arXiv**: 2512.24601 (December 31, 2025)
**PDF**: [2512.24601.pdf](./2512.24601.pdf)

---

## Core Insight

Long prompts should NOT be fed directly into the neural network. Instead, treat them as **part of the external environment** that the LLM can symbolically interact with.

## How It Works

```
┌─────────────────────────────────────────────────────────────┐
│                    RLM (root / depth=0)                     │
├─────────────────────────────────────────────────────────────┤
│  Environment E (Python REPL)                                │
│  ├── context = "<very long document>"   # NOT in LLM ctx   │
│  ├── llm_query(prompt) → str            # recursive calls  │
│  └── print() → observe results                              │
│                                                             │
│  Model writes code to:                                      │
│  1. Peek at context (print(context[:1000]))                │
│  2. Decompose (chunks = context.split('\n'))               │
│  3. Filter (regex, keyword search)                         │
│  4. Recursively invoke self on chunks                      │
│  5. Store results in variables                             │
│  6. Return FINAL(answer) or FINAL_VAR(variable)            │
└─────────────────────────────────────────────────────────────┘
```

## Key Implementation Details

### REPL Environment
- Context loaded as string variable (not in LLM context window)
- `llm_query(prompt)` function available for recursive sub-calls
- Variables persist across code executions
- `print()` outputs truncated results back to root LLM

### Model Hierarchy
- **Root LM** (e.g., GPT-5): Orchestrates, sees metadata only
- **Sub-LM** (e.g., GPT-5-mini): Handles ~500K character chunks
- Max recursion depth = 1 in experiments (sub-calls are plain LMs, not RLMs)

### Termination
- `FINAL(answer)` - return answer directly
- `FINAL_VAR(variable_name)` - return variable from REPL as output

## Results

### Performance (Table 1)

| Task | Base GPT-5 | RLM(GPT-5) | Improvement |
|------|------------|------------|-------------|
| CodeQA (23K-4.2M tokens) | 24%* | 62% | +158% |
| BrowseComp+ (6-11M tokens) | 0%* | 91.33% | N/A (can't fit) |
| OOLONG (131K tokens) | 44% | 56.50% | +28% |
| OOLONG-Pairs (32K tokens) | 0.04% | 58.00% | +144,900% |

*asterisk = ran into context limits

### Cost Analysis
- **Median RLM cost ≤ base model cost** (often cheaper due to selective viewing)
- **High variance** - some trajectories 3x more expensive due to long explorations
- At 10M+ tokens: RLM costs ~$0.99/query vs theoretical $1.50-$2.75 for full context

### Scaling Behavior
- Base models degrade quickly as context grows (context rot)
- RLMs maintain performance up to 1M+ tokens
- More complex tasks (quadratic vs linear) show larger RLM advantage

## Emergent Patterns Observed

### 1. Code-Based Filtering Without Seeing Content
```python
# Model uses priors to search for relevant sections
keywords = ["festival", "La Union", "beauty pageant"]
results = {kw: find_snippets(kw, window=400) for kw in keywords}
```

### 2. Chunking and Recursive Sub-Calling
```python
# Uniform chunking for semantic transformation
for i in range(0, len(lines), batch_size):
    batch = lines[i:i+batch_size]
    classification = llm_query(f"Classify: {batch}")
    results.append(classification)
```

### 3. Answer Verification via Sub-Calls
```python
# Use sub-LM to verify answer in fresh context (avoids context rot)
confirm = llm_query(f"Verify this answer: {answer}\nEvidence: {chunk}")
```

### 4. Variable Storage for Long Outputs
```python
# Build answer incrementally in variables
for pair in pairs:
    result = llm_query(f"Process: {pair}")
    formatted_pairs.append(result)
FINAL_VAR(formatted_pairs)  # Return variable, not string
```

## Comparison to Alternatives

| Method | Can Scale Beyond Context? | Performance | Cost |
|--------|---------------------------|-------------|------|
| Base LLM | No | Degrades with length | Baseline |
| Summary Agent | Yes (lossy) | Loses fine-grained info | High |
| CodeAct + BM25 | Somewhat | Good for retrieval tasks | Medium |
| **RLM** | **Yes (100x)** | **Best on dense tasks** | **Comparable** |

## Limitations & Future Work

1. **Synchronous sub-calls are slow** - async would significantly reduce runtime
2. **No deep recursion tested** - only depth=1 (sub-calls are LMs, not RLMs)
3. **Model-dependent behavior** - Qwen3-Coder makes 1000s of sub-calls where GPT-5 makes 10
4. **Not trained for RLM** - current models are "inefficient decision makers over their context"
5. **High variance** - some trajectories explode in cost due to redundant verification

## System Prompt (Simplified)

```
You are tasked with answering a query with associated context.
You can access this context in a REPL environment.

Your context is a {type} with {length} characters.

The REPL environment has:
1. A 'context' variable with your data (NOT in your context window)
2. A 'llm_query(prompt)' function for recursive LLM calls (~500K chars)
3. print() to observe results

Strategy:
1. Peek at context structure
2. Chunk intelligently
3. Query sub-LM per chunk
4. Aggregate results
5. Return FINAL(answer) or FINAL_VAR(variable)

Sub-LLMs are powerful - they handle ~500K chars. Batch aggressively!
```

## Key Takeaways

1. **Separation of concerns**: Symbolic manipulation (code) vs semantic reasoning (LLM calls)
2. **Context as environment**: Data stays outside neural network until explicitly examined
3. **Recursive decomposition**: Break problems into sub-problems, delegate to sub-LMs
4. **Variable persistence**: REPL state bridges multiple reasoning steps
5. **Model priors help**: LLMs can filter context without seeing it (keyword search, regex)

---

**Related Work Cited**:
- Claude Code subagents (Anthropic, 2025)
- MemGPT (Packer et al., 2024)
- THREAD recursive spawning (Schroeder et al., 2025)
- Context Folding (Sun et al., 2025)
- ReSum summarization (Wu et al., 2025)
