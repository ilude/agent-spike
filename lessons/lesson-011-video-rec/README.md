# Lesson 011: Video Recommendation - Persona Clustering Spike

**Status**: In Progress
**Goal**: Validate that user watch history clusters into coherent interest personas

## Overview

This lesson implements Phase 0 of the video recommendation system: proving that multi-persona embeddings work for our use case.

See `.claude/ideas/video-algorithm/` for full planning docs.

## Approach

1. Extract video IDs from Brave history (last 3 months) + Google Takeout (50 random historical)
2. Fetch transcripts for videos not in archive
3. Generate embeddings via Infinity
4. Cluster into personas using k-means
5. Validate: do clusters represent coherent interests?

## Scripts

| Script | Purpose |
|--------|---------|
| `extract_brave_history.py` | Extract YouTube video IDs from Brave SQLite |
| `extract_takeout_history.py` | Extract from Google Takeout watch-history.json |
| `merge_video_ids.py` | Dedupe, check archive, prepare processing list |
| `fetch_missing_transcripts.py` | Fetch and archive transcripts |
| `generate_embeddings.py` | Generate embeddings via Infinity |
| `cluster_personas.py` | k-means clustering, silhouette scoring |
| `inspect_clusters.py` | View cluster contents, manual labeling |

## Running

```bash
cd lessons/lesson-011-video-rec

# Step 1: Extract video IDs
uv run python extract_brave_history.py
uv run python extract_takeout_history.py

# Step 2: Merge and check archive
uv run python merge_video_ids.py

# Step 3: Fetch missing transcripts (may take time)
uv run python fetch_missing_transcripts.py

# Step 4: Generate embeddings
uv run python generate_embeddings.py

# Step 5: Cluster
uv run python cluster_personas.py

# Step 6: Inspect results
uv run python inspect_clusters.py
```

## Data Locations

- **Brave history**: `compose/data/browser_history/brave_history/*.sqlite`
- **Takeout**: `compose/data/google-takeout-20250723T204430Z-1-001.zip`
- **Archive**: `compose/data/archive/youtube/YYYY-MM/`
- **Output**: `output/` directory in this lesson

## Success Criteria

- Clusters are interpretable (can assign human-readable labels)
- At least 3-4 distinct interest areas emerge
- Silhouette score > 0.3 (decent cluster separation)
