# EGO-Prompt: Self-Improving Knowledge Graphs for Agent Reasoning

**Created:** 2025-11-22
**Source Video:** https://www.youtube.com/watch?v=lZrhWGc2xJk
**Status:** Research / Future consideration

---

## The Problem

- Standard prompting (even Chain-of-Thought) relies only on what the LLM already knows
- RAG helps but just dumps plain text - doesn't improve reasoning structure
- Knowledge graphs are better but they're **static** - can't learn from mistakes or update themselves
- Expert knowledge is often partial, imperfect, and may contain errors

## The Solution: EGO-Prompt

**Evolutionary Graph Optimization for Prompting** - treats expert knowledge as evolvable, not fixed.

### How It Works (3-Stage Loop)

```
1. START with imperfect expert-made "Semantic Causal Graph" (SCG)
   - Nodes = concepts (e.g., "diabetes", "low blood sugar")
   - Edges = causal relationships in natural language

2. TWO-STAGE WORKFLOW per query:
   - Analyst model: filters graph to only relevant causal chains
   - Decision model: makes prediction using filtered context

3. SELF-CORRECTION (Text Gradient Mechanism):
   - Compare prediction to ground truth
   - If wrong → "mentor model" generates improvement report
   - System auto-updates graph (add/delete nodes, fix relationships)

4. REPEAT → graph gets cleaner and smarter each cycle
```

### Key Insight

The initial knowledge graph **doesn't need to be perfect** - the system corrects itself through iteration. This reduces demands on domain experts and allows starting from imperfect knowledge.

### Performance Results

- **7-12% F1 improvement** over strongest baselines
- GPT-4o-mini with EGO-Prompt **beats o1 and o4-mini** reasoning models
- 6-140x cheaper than reasoning models for same/better performance

---

## Paper Details

**Title:** How to Auto-optimize Prompts for Domain Tasks? Adaptive Prompting and Reasoning through Evolutionary Domain Knowledge Adaptation

**Authors:** Yang Zhao, Pu Wang, Hao Frank Yang (Johns Hopkins University)

**Venue:** NeurIPS 2025 (24.5% acceptance rate)

### Links

- **arXiv:** https://arxiv.org/abs/2510.21148
- **Full HTML:** https://arxiv.org/html/2510.21148
- **OpenReview:** https://openreview.net/forum?id=59n2g6RqjT
- **Project page:** https://miemieyanga.github.io/EGOPrompt/
- **PDF:** https://openreview.net/pdf?id=59n2g6RqjT

---

## Relevance to Agent-Spike

This pattern aligns with the **self-improving agent** goals in VISION.md:

1. **Preference Learning** - EGO-Prompt's feedback loop is similar to learning from user ratings
2. **Application Suggester** - The SCG structure could map learned techniques to project needs
3. **Judgment Integration** - The "mentor model" feedback mechanism is a form of calibration loop

### Potential Applications

- Evolving the recommendation engine's understanding of user preferences
- Building domain-specific reasoning for content analysis
- Self-correcting tagging/classification over time

### Implementation Considerations

- Requires ground truth data for the feedback loop
- Two-model architecture (analyst + decision maker) adds cost
- Mentor model for corrections adds more cost
- Best suited for domains where you can verify predictions

---

## Where AI Research News Gets Surfaced

### Primary Sources

| Source | Description | Link |
|--------|-------------|------|
| arXiv | Raw papers as posted | https://arxiv.org/list/cs.AI/recent |
| Arxiv Sanity | Karpathy's paper filter | arxiv-sanity-lite.com |
| alphaXiv | arXiv + discussions + trending | https://alphaxiv.org |

### Curated Newsletters

| Newsletter | Notes |
|------------|-------|
| **AI News** | "Best AI newsletter" per Karpathy, by swyx |
| **Alpha Signal** | Daily 5-min, 200k+ subscribers |
| **TLDR AI** | Quick daily digest |
| **Ben's Bites** | Friendly, accessible, 100k+ |
| **Import AI** | Jack Clark (Anthropic), policy/research depth |

### Aggregators

- **Deep Learning Monitor** (deeplearn.org) - arXiv + Twitter + Reddit
- **DAIR.AI ML Papers of the Week** - GitHub weekly highlights

### Communities

- r/machinelearning (Reddit)
- Hacker News
- Twitter/X (follow researchers directly)

---

## Next Steps

- [ ] Read full paper when time permits
- [ ] Evaluate if SCG pattern fits agent-spike's preference learning goals
- [ ] Consider lighter-weight version without mentor model overhead
- [ ] Check if official implementation is released

---

**Tags:** #research #self-improving #knowledge-graphs #prompt-optimization #neurips-2025
