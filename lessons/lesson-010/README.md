# Lesson 010: Semantic Tag Normalization System

Build a two-phase tagging system that creates consistent vocabulary across your content archive, with an evolving tag system that improves over time.

## Problem

Current tagging generates inconsistent vocabulary:
- "ai-agents" vs "artificial-intelligence-agents" vs "llm-agents"
- No reuse of existing tags
- Difficult to build knowledge graphs
- Poor search quality due to fragmentation

## Solution

**Two-Phase Tagging:**
1. **Phase 1**: Extract raw structured metadata (independent)
2. **Phase 2**: Normalize using semantic similarity to existing corpus

**Evolving Vocabulary:**
- Start with seed vocabulary from archive analysis
- Track usage and confidence over time
- Consolidate variations as patterns emerge
- Version vocabulary for rollback
- Re-tag when vocabulary significantly improves

## Quick Start

### 1. Analyze Archive
```bash
cd lessons/lesson-010
uv run python scripts/analyze_archive.py
```

Generates:
- `archive_tag_analysis_report.md` - Statistics and insights
- `data/seed_vocabulary_v1.json` - Initial vocabulary

### 2. Test Normalization
```bash
# Normalize a single video
uv run python -m tag_normalizer.cli normalize "VIDEO_ID"

# Test on sample batch
uv run python scripts/test_normalization.py
```

### 3. Re-tag Archive
```bash
# Re-tag all videos with new vocabulary
uv run python scripts/retag_archive.py --vocabulary-version v1
```

## CLI Commands

```bash
# Analyze archive and generate seed vocabulary
uv run python -m tag_normalizer.cli analyze

# Normalize a single video
uv run python -m tag_normalizer.cli normalize VIDEO_ID

# Check vocabulary evolution
uv run python -m tag_normalizer.cli evolve

# Re-tag specific videos
uv run python -m tag_normalizer.cli retag VIDEO_ID1 VIDEO_ID2 ...

# Show vocabulary stats
uv run python -m tag_normalizer.cli vocab-stats
```

## Architecture

```
tag_normalizer/
├── analyzer.py       # Archive analysis & stats
├── vocabulary.py     # Vocabulary management with versioning
├── retriever.py      # Semantic similarity search
├── normalizer.py     # Two-phase normalization agent
├── evolution.py      # Vocabulary evolution tracking
└── cli.py           # CLI interface
```

## How It Works

### Phase 1: Raw Extraction
```python
# Extract structured metadata from transcript
raw_metadata = await extract_raw_metadata(transcript)
# Archive as: output_type="structured_metadata"
```

### Phase 2: Normalization
```python
# Find similar videos
similar_videos = retriever.find_similar(transcript, limit=5)
context_tags = extract_tags(similar_videos)

# Normalize with context
normalized = await normalize_tags(
    raw_tags=raw_metadata,
    context_tags=context_tags,
    vocabulary_version="v1"
)
# Archive as: output_type="normalized_metadata_v1"
```

### Evolution
```python
# Track usage
tracker.record_tag_usage(video_id, normalized_tags)

# Check for evolution opportunities
suggestions = tracker.suggest_consolidation()

# Update vocabulary when ready
vocabulary.bump_version(suggestions)
```

## Configuration

```python
config = {
    "use_semantic_context": False,  # Feature flag
    "vocabulary_version": "v1",
    "confidence_threshold": 0.7,
    "min_occurrences_for_canonical": 3,
    "evolution_enabled": True,
    "similar_videos_limit": 5,
}
```

## Archive Format

All versions stored in `llm_outputs` (additive only):

```json
{
  "llm_outputs": [
    {
      "output_type": "structured_metadata",
      "output_value": {"subject_matter": [...], ...},
      "model": "claude-3-5-haiku-20241022",
      "generated_at": "2025-01-10T..."
    },
    {
      "output_type": "normalized_metadata_v1",
      "output_value": {"subject_matter": [...], ...},
      "model": "claude-3-5-haiku-20241022",
      "vocabulary_version": "v1",
      "generated_at": "2025-01-10T..."
    }
  ]
}
```

## Dependencies

```bash
uv sync --group lesson-010
```

Reuses dependencies from lessons 001 and 007:
- pydantic-ai (agents)
- qdrant-client (semantic search)
- sentence-transformers (embeddings)
- rich, typer (CLI)

## Key Learnings

- Two-phase approach balances independence vs. consistency
- Semantic similarity provides better context than frequency alone
- Versioning enables safe experimentation and rollback
- Evolution tracking prevents vocabulary drift
- Archive-first pattern enables iterative improvement

## Next Steps

After lesson-010 proves the concept:
1. Extract to `tools/services/tagger/` for production
2. Integrate with `ingest_youtube.py` pipeline
3. Add batch re-tagging to `reingest_from_archive.py`
4. Build knowledge graph from normalized tags

## Files

- `PLAN.md` - Detailed implementation plan
- `README.md` - This file
- `COMPLETE.md` - Learnings after completion (TBD)
