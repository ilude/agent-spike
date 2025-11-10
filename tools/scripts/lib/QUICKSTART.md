# Reprocessing System Quick Start

## TL;DR

Reprocess archives with new transformations without copy-paste code:

```bash
# Test Qdrant metadata reprocessing
uv run python tools/scripts/reprocess_qdrant_metadata.py --dry-run --limit 5

# Test lesson-010 tag normalization
uv run python tools/scripts/reprocess_normalized_tags.py --dry-run --limit 3

# Run for real (updates archives)
uv run python tools/scripts/reprocess_qdrant_metadata.py
```

## When to Use This

**Use the reprocessing system when:**
- You update transformation logic (flattening, weights, normalization)
- You bump vocabulary version (v1 → v2)
- You change models (claude-haiku → sonnet)
- You want to apply lesson-010 normalizer to all archives

**Don't use when:**
- Adding new videos (use ingest_youtube.py instead)
- Rebuilding Qdrant cache (use reingest_from_archive.py for now)

## How It Works

1. **Version tracking**: Each transformation has a version number
2. **Staleness detection**: Compare archive's stored version to current version
3. **Incremental processing**: Skip archives with up-to-date versions
4. **Archive updates**: Add derived_outputs with transformation results

## Bumping Versions

Edit `tools/scripts/lib/transform_versions.py`:

```python
VERSIONS = {
    "normalizer": "v1.1",  # Was v1.0, bump after changing normalization logic
    "vocabulary": "v2",    # Was v1, bump after updating vocabulary
}
```

Then run reprocessing script:

```bash
# All archives with old versions will be reprocessed
uv run python tools/scripts/reprocess_normalized_tags.py
```

## Common Tasks

### Test on Sample

```bash
# Test Qdrant metadata (fast, no LLM calls)
uv run python tools/scripts/reprocess_qdrant_metadata.py --dry-run --limit 10

# Test tag normalization (slow, calls LLM)
uv run python tools/scripts/reprocess_normalized_tags.py --dry-run --limit 3
```

### Reprocess Everything

```bash
# Qdrant metadata (~12 minutes for 470 videos)
uv run python tools/scripts/reprocess_qdrant_metadata.py

# Tag normalization (~2 hours for 470 videos, uses LLM)
uv run python tools/scripts/reprocess_normalized_tags.py
```

### Skip Semantic Context (Faster)

```bash
# Normalization without Qdrant context (faster, lower quality)
uv run python tools/scripts/reprocess_normalized_tags.py --no-context --limit 50
```

### Check What Would Change

```bash
# Dry run shows which archives would be processed
uv run python tools/scripts/reprocess_qdrant_metadata.py --dry-run
```

Output:
```
[1/470] -BJ11YziNwY - OK (0.00s)      # Would process
[2/470] -bugLOJjaow - SKIP (up-to-date)  # Would skip
```

## Archive Data After Reprocessing

Archives get a new `derived_outputs` entry:

```json
{
  "derived_outputs": [
    {
      "output_type": "qdrant_metadata",
      "output_value": "{\"type\": \"youtube_video\", ...}",
      "transformer_version": "v1.0+v1.0+v1",
      "transform_manifest": {
        "qdrant_flattener": "v1.0",
        "weight_calculator": "v1.0",
        "qdrant_schema": "v1",
        "created_at": "2025-11-10T12:34:56"
      },
      "source_outputs": ["tags"]
    }
  ]
}
```

## Performance

**First run** (all archives out-of-date):
- Qdrant metadata: ~12 minutes for 470 videos
- Tag normalization: ~2 hours for 470 videos (LLM calls)

**Subsequent runs** (all up-to-date):
- Both: ~5 seconds (skips everything)

**After version bump**:
- Only reprocesses affected archives

## Troubleshooting

**"No module named 'lessons.lesson_010'"**
- Fix: Import paths corrected in reprocess_normalized_tags.py

**"Field required [type=missing]"**
- Fix: LLM returning capitalized field names, normalizer handles this

**"Archive not found"**
- Fix: Make sure video exists in projects/data/archive/youtube/

**"Qdrant retriever failed"**
- Fix: Check Qdrant is running (lesson-010 semantic context)
- Workaround: Use --no-context flag

## Next Steps

- See `README.md` for full documentation
- See `tools/scripts/lib/transform_versions.py` for version registry
- See `tools/scripts/lib/metadata_transformers.py` for transformer pattern
- See `tools/scripts/lib/reprocessing_pipeline.py` for pipeline template
