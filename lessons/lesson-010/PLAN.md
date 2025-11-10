# Lesson 010: Semantic Tag Normalization System

## Learning Objective

Build a two-phase tagging system that creates consistent vocabulary across the content archive, with an evolving tag system that improves over time through usage and learning.

## Problem Statement

Current tagging system generates tags in isolation, leading to:
- Inconsistent vocabulary (e.g., "ai-agents" vs "artificial-intelligence-agents" vs "llm-agents")
- No reuse of existing tags
- Difficult to build knowledge graphs or relationships
- Poor search/recommendation quality due to fragmented tags

## Solution Architecture

### Two-Phase Tagging Approach

**Phase 1: Raw Tag Extraction**
- Generate structured metadata from transcript (independent)
- Extract: subject_matter, entities, techniques, tools, etc.
- Fast, cheap, unbiased by existing corpus
- Archive as `output_type: "structured_metadata"`

**Phase 2: Semantic Normalization**
- Query Qdrant for 5-10 semantically similar videos
- Extract their tags to understand existing vocabulary
- Normalize raw tags to match corpus vocabulary
- Archive as `output_type: "normalized_metadata_vN"`

### Evolving Vocabulary System

**Seed Vocabulary (v1)**
- Start with 30-50 core tags from archive analysis
- Group by category: AI concepts, tools, companies, techniques
- Include variation mappings (aliases → canonical form)

**Evolution Mechanism**
- Track tag usage frequency over time
- Monitor new tags appearing in normalized output
- Calculate confidence scores for tags
- Identify emerging patterns and consolidation opportunities
- Version vocabulary for rollback capability

**Re-tagging Triggers**
- Major vocabulary version bump (significant improvements)
- Confidence threshold reached (enough examples to consolidate)
- Manual trigger for specific improvements
- Scheduled periodic review (e.g., monthly)

## Technical Components

### 1. Archive Analyzer (`analyzer.py`)
- Load all archive JSON files
- Extract tags from old format (comma-separated) and new format (structured)
- Generate frequency statistics
- Identify variation patterns (hyphen vs underscore, singular vs plural, etc.)
- Output: Archive analysis report + seed vocabulary candidates

### 2. Vocabulary Manager (`vocabulary.py`)
- Load/save seed vocabulary with versioning
- Track canonical forms and aliases
- Store usage statistics (count, last seen, confidence)
- Version management (v1, v2, etc.)
- Consolidation rules (when to merge tags)

### 3. Semantic Retriever (`retriever.py`)
- Find similar videos using Qdrant semantic search
- Extract normalized tags from similar videos
- Calculate tag co-occurrence patterns
- Return relevant vocabulary subset for context

### 4. Tag Normalizer (`normalizer.py`)
- Phase 1: Extract raw structured metadata from transcript
- Phase 2: Normalize using semantic context from similar videos
- LLM-based normalization with Claude Haiku
- Feature flags for A/B testing
- Archive both raw and normalized output

### 5. Evolution Tracker (`evolution.py`)
- Monitor tag usage over time
- Identify emerging patterns
- Suggest vocabulary consolidation
- Track normalization success metrics
- Generate evolution reports

## Archive Storage Strategy

**Additive Only - Never Replace**

All tag versions stored in `llm_outputs` array:
```json
{
  "llm_outputs": [
    {
      "output_type": "tags",
      "output_value": "ai-agents, multi-agent, coordination",
      "model": "claude-3-5-haiku-20241022",
      "generated_at": "2024-11-09T..."
    },
    {
      "output_type": "structured_metadata",
      "output_value": {
        "subject_matter": ["ai-agents", "multi-agent-systems"],
        "entities": {...},
        ...
      },
      "model": "claude-3-5-haiku-20241022",
      "generated_at": "2025-01-10T..."
    },
    {
      "output_type": "normalized_metadata_v1",
      "output_value": {
        "subject_matter": ["ai-agents", "multi-agent-coordination"],
        "entities": {...},
        ...
      },
      "model": "claude-3-5-haiku-20241022",
      "vocabulary_version": "v1",
      "generated_at": "2025-01-10T..."
    }
  ]
}
```

## Implementation Plan

### Step 1: Analysis (30 min)
- [ ] Create `scripts/analyze_archive.py`
- [ ] Load all 470 video archives
- [ ] Count tag frequency and format distribution
- [ ] Generate initial seed vocabulary (30-50 tags)
- [ ] Output: `archive_tag_analysis_report.md`

### Step 2: Vocabulary System (1 hour)
- [ ] Create `vocabulary.py` with VocabularyManager class
- [ ] Load/save JSON format with versioning
- [ ] Track canonical forms, aliases, and statistics
- [ ] Implement consolidation logic
- [ ] Save initial seed as `data/seed_vocabulary_v1.json`

### Step 3: Semantic Retrieval (45 min)
- [ ] Create `retriever.py` with SemanticRetriever class
- [ ] Query Qdrant for similar videos
- [ ] Extract tags from results
- [ ] Build context for normalization prompt

### Step 4: Two-Phase Normalizer (1 hour)
- [ ] Create `normalizer.py` with TagNormalizer class
- [ ] Phase 1: Extract raw structured metadata
- [ ] Phase 2: Normalize using semantic context
- [ ] Feature flag for enabling/disabling normalization
- [ ] Archive writer integration

### Step 5: Evolution Tracking (30 min)
- [ ] Create `evolution.py` with EvolutionTracker class
- [ ] Track tag usage over time
- [ ] Calculate confidence scores
- [ ] Suggest vocabulary updates
- [ ] Generate evolution reports

### Step 6: CLI & Testing (1 hour)
- [ ] Create `cli.py` with Typer CLI
- [ ] Commands: analyze, normalize, evolve, retag
- [ ] Test on 20-30 sample videos
- [ ] Validate normalization quality
- [ ] Measure before/after consistency

### Step 7: Documentation (30 min)
- [ ] Document learnings in COMPLETE.md
- [ ] Create README.md with usage examples
- [ ] Update STATUS.md

## Expected Outcomes

1. **Archive analysis report** showing current tag state
2. **Seed vocabulary v1** (30-50 core normalized tags)
3. **Working two-phase normalization** system with feature flag
4. **Evolution mechanism** that improves vocabulary over time
5. **Re-tagging capability** for batch processing
6. **Metrics** showing normalization effectiveness

## Key Learnings to Document

- How to build evolving vocabularies without over-fitting
- Balancing canonical forms vs. organic tag discovery
- When to trigger re-tagging (cost vs. benefit)
- Semantic similarity for tag context (effectiveness)
- Two-phase approach benefits (raw vs. normalized)

## Future Integration

Once lesson-010 proves the concept:
1. Extract to `tools/services/tagger/` for production use
2. Integrate with `tools/scripts/ingest_youtube.py`
3. Add to `reingest_from_archive.py` for batch processing
4. Build vocabulary management CLI in `tools/scripts/`
5. Use normalized tags for knowledge graph construction

## Dependencies

Add to `pyproject.toml`:
```toml
[project.optional-dependencies]
lesson-010 = [
    "pydantic-ai",
    "qdrant-client",
    "sentence-transformers",
    "python-dotenv",
    "rich",
    "typer",
]
```

Reuses existing dependencies from lessons 001, 007.

## Timeline

- **Analysis & seed vocabulary**: 30 min
- **Core implementation**: 3 hours
- **Testing & refinement**: 1 hour
- **Documentation**: 30 min
- **Total**: ~5 hours
