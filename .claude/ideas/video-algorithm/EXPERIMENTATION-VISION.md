# Experimentation Vision: Self-Improving Recommendations

**Status**: Future (post-MVP)
**Created**: 2025-11-24
**Context**: Captured during MVP planning discussion

## The Problem

MVP has parameters that are "reasonable guesses":
- Activity decay half-life: ~2 weeks
- Activity floor: 0.1
- Metadata multiplier ranges (0.5-2.0 for channel, 0.7-1.2 for view health, etc.)
- Number of personas (k=5-8)
- Scoring formula: `content × channel × view_health × recency`

These feel sensible but aren't validated. We're shooting from the hip.

**The real question**: What's the optimal way to model interest decay? Persona count? Scoring weights?

We don't know, and we're not data scientists. But we can build agents that are.

## The Vision

Build a meta-layer of agents that:

1. **Project Lead Agent**: Understands high-level goals ("maximize videos I actually want to watch"), creates experimentation plans
2. **Experiment Agents**: Execute specific experiments (A/B tests, parameter sweeps, alternative models)
3. **Validation Loop**: Tests hypotheses against the actual user (me)

### Example: Optimizing Decay Curves

**Current assumption**: Exponential decay with 2-week half-life

**What Project Lead might propose**:
- "Let's test if interest decay is actually exponential, or if it's more stepwise (active → dormant → forgotten)"
- "Let's find the optimal half-life by testing 1 week, 2 weeks, 1 month"
- "Let's see if different personas decay at different rates (hobbies vs professional interests)"

**What Experiment Agent would do**:
1. Design A/B test: Show 20 videos, half scored with current model, half with proposed
2. Collect user feedback (thumbs up/down)
3. Measure: Which model produces higher thumbs-up rate?
4. Report findings back to Project Lead

**Validation**:
- User (me) rates videos naturally
- System tracks which model's recommendations performed better
- Over time, parameters converge toward optimal values

## Architecture Sketch

```
┌─────────────────────────────────────────────────────────────┐
│                    Project Lead Agent                        │
│                                                              │
│  Inputs:                                                     │
│  - High-level goals ("find inspiring content")               │
│  - Current model performance metrics                         │
│  - Historical experiment results                             │
│                                                              │
│  Outputs:                                                    │
│  - Experiment proposals                                      │
│  - Prioritized backlog of hypotheses to test                 │
│  - Synthesis of learnings                                    │
└──────────────────────────┬──────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────────┐
│                   Experiment Registry                        │
│                                                              │
│  - Active experiments                                        │
│  - Historical results                                        │
│  - Parameter configurations                                  │
└──────────────────────────┬──────────────────────────────────┘
                           │
           ┌───────────────┼───────────────┐
           ▼               ▼               ▼
    ┌────────────┐  ┌────────────┐  ┌────────────┐
    │ Decay      │  │ Clustering │  │ Scoring    │
    │ Experiment │  │ Experiment │  │ Experiment │
    │            │  │            │  │            │
    │ Tests:     │  │ Tests:     │  │ Tests:     │
    │ - Half-life│  │ - k values │  │ - Formula  │
    │ - Curve    │  │ - Algorithm│  │ - Weights  │
    │   shape    │  │ - Hierarchy│  │ - Metadata │
    └─────┬──────┘  └─────┬──────┘  └─────┬──────┘
          │               │               │
          └───────────────┴───────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────────────┐
│                   Recommendation Engine                      │
│                                                              │
│  - Supports multiple concurrent "models" (experiment arms)   │
│  - Tracks which model produced each recommendation           │
│  - Collects feedback per model                               │
└──────────────────────────┬──────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────────┐
│                      User Feedback                           │
│                                                              │
│  - Thumbs up/down (explicit)                                 │
│  - Watch completion (implicit)                               │
│  - Time to decision (implicit)                               │
└─────────────────────────────────────────────────────────────┘
```

## Key Infrastructure Needed

### 1. Experiment Tracking
- Store multiple model configurations
- Track which model produced each recommendation
- Collect feedback attributed to model

### 2. A/B Testing Framework
- Randomly assign recommendations to models
- Statistical significance testing
- Automatic promotion of winners

### 3. Agent Communication Protocol
- Project Lead → Experiment Agent: "Test this hypothesis"
- Experiment Agent → Project Lead: "Results: X% improvement, confidence Y%"
- Project Lead → User (optional): "I found that Z works better, should I adopt it?"

### 4. Hypothesis Representation
- Structured format for "what we're testing"
- Parameterized models that can be instantiated with different configs
- Clear success metrics

## Example Hypotheses to Test

| Hypothesis | Test Method | Success Metric |
|------------|-------------|----------------|
| Interest decay is logarithmic, not exponential | A/B test decay curves | Thumbs-up rate |
| Different personas decay at different rates | Per-persona decay tracking | Persona accuracy over time |
| **Some interests are seasonal/cyclical** | Temporal pattern analysis | See below |
| View count sweet spot is 10k-100k | Vary view_health curve | Thumbs-up rate on recommended videos |
| Channel affinity matters more than content | Weight comparison | Prediction accuracy |
| Hierarchical clustering beats k-means | Algorithm comparison | Cluster coherence + recommendation quality |

### Concrete Example: Seasonal Interests

**Observation**: Some interests appear to be cyclical rather than decaying:
- **Mini painting**: More active in winter (more time indoors)
- **Koi ponds**: Spring/summer interest (outdoor activity)
- **Other interests**: May correlate with unknown factors (project deadlines, life events, etc.)

**Why simple decay fails**: If I stop watching koi pond videos in October, exponential decay says "this interest is dying." But it's not dying - it's seasonal. Come April, it should resurge.

**Visual comparison**:

Reality (seasonal):
```
Interest Level
     │
  1.0│      ╭──╮                    ╭──╮
     │     ╱    ╲                  ╱    ╲
  0.5│────╱      ╲────────────────╱      ╲────
     │
  0.0│
     └────┬──────┬──────┬──────┬──────┬──────
         Mar    Jun    Sep    Dec    Mar    Jun
                     (koi ponds)
```

MVP model (exponential decay):
```
Interest Level
     │
  1.0│╲
     │ ╲
  0.5│  ╲
     │   ╲
  0.0│────╲─────────────────────────────────
     └────┬──────┬──────┬──────┬──────┬──────
         Oct    Dec    Feb    Apr    Jun
         (assumes interest is dying)
```

**MVP approach**: Simple decay is *wrong*, but it's *simple wrong* that we can improve later. The key is collecting timestamped signals so future agents have data to analyze.

**What an agent could discover**:
1. Analyze historical watch patterns with timestamps
2. Detect cyclical patterns (yearly, monthly, weekly)
3. Correlate with external signals (weather? daylight hours? calendar events?)
4. Propose: "Mini painting shows 3x engagement Nov-Feb vs Jun-Aug"

**Possible model improvements**:
- Per-persona seasonality curves instead of uniform decay
- External signal integration (weather API, calendar)
- "Dormant but expected to return" vs "actually declining interest"

**The meta-point**: I (the user) *suspect* seasonality exists but can't prove it or quantify it. A data science agent could:
1. Test the hypothesis against my actual watch history
2. Find patterns I didn't know about
3. Discover correlations with factors I haven't considered

## Why This Matters

I'm not a data scientist. I can make educated guesses about decay curves and scoring formulas, but I don't actually know what's optimal.

The traditional approach: Hire a data scientist, run experiments manually, iterate slowly.

The agentic approach: Build infrastructure for agents to design and run experiments autonomously, surface findings to me for validation.

This shifts my role from "guess at parameters" to "approve experiments and validate results."

## Relationship to MVP

**MVP**: Get the recommendation system working with sensible defaults. Prove the persona clustering approach works at all.

**Post-MVP**: Build experimentation infrastructure. Let agents find optimal parameters.

**Don't need for MVP**:
- Multi-model support
- A/B testing framework
- Experiment registry
- Project Lead agent

**MVP lays groundwork**:
- Clean separation between scoring logic and parameters
- Feedback collection (thumbs up/down)
- Parameterized decay/scoring (easy to swap formulas)

## Open Questions

1. **How much autonomy?** Should agents run experiments automatically, or propose and wait for approval?

2. **Validation burden**: How many videos do I need to rate per experiment? Can we minimize while maintaining statistical significance?

3. **Multi-armed bandit vs A/B**: Should we use explore/exploit rather than fixed A/B tests?

4. **Meta-learning**: Can the Project Lead learn what kinds of experiments are worth running?

5. **Explainability**: When an experiment succeeds, can we understand *why* it worked?

---

## Related Context

- This aligns with the broader VISION.md goal of a "Personal AI Research Assistant"
- The lesson structure in this repo (lessons/) is already about learning agent patterns
- Lesson 009 (Agent Orchestrator) covers multi-agent coordination patterns

This experimentation vision is a natural evolution: use the agent patterns we're learning to improve the systems we're building.
