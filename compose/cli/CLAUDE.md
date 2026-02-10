# CLI Scripts

Reusable command-line scripts built on top of the service layer.

## Shared Infrastructure

| Script | Purpose |
|--------|---------|
| `base.py` | Shared setup utility. Configures `sys.path`, loads `.env`, eliminates boilerplate across all scripts. |

## Data Ingestion Pipeline

| Script | Purpose | Key Flags |
|--------|---------|-----------|
| `fetch_channel_videos.py` | Pulls all videos from a YouTube channel via Data API v3, exports CSV to `data/queues/pending/` for ingestion. | `-m` months back, `-o` output file |
| `update_video_metadata.py` | Backfills YouTube API metadata (title, duration, views, channel) for archives that are missing it. | `--all`, `--force`, `--dry-run` |
| `filter_description_urls.py` | Extracts URLs from video descriptions and classifies them as content vs marketing using heuristic rules + LLM. Self-improving pattern system learns from classifications over time. | `--heuristic-only`, `--reevaluate-low-confidence`, `--show-pattern-stats` |
| `url_filter_status.py` | Dashboard for the URL filter's learned pattern system. Shows pattern effectiveness, batch progress, and low-performing patterns. | `--summary`, `--detailed`, `--full` |

## Database Migration & Population

| Script | Purpose | Key Flags |
|--------|---------|-----------|
| `migrate_to_surrealdb.py` | Migrates file-based archives to SurrealDB + MinIO (metadata to DB, blobs to object storage). Also has a `stats` subcommand for archive analysis. | `--dry-run`, `--limit` |
| `populate_surrealdb_from_archive.py` | Reads archive JSON files, generates embeddings via Infinity API, and upserts full `VideoRecord` entries into SurrealDB. The "heavy" population script. | `--dry-run`, `--limit` |
| `backfill_embeddings.py` | Finds videos in SurrealDB missing embeddings, fetches transcripts from MinIO, generates embeddings via Infinity, stores them back. | `--dry-run`, `--limit` |
| `validate_data.py` | Validates migration integrity: compares archive file counts vs SurrealDB records, samples random videos to check embeddings (1024-dim) and metadata completeness. | `validate`, `quick`, `sample N` |

## Query & Management

| Script | Purpose | Key Flags |
|--------|---------|-----------|
| `list_videos.py` | Lists all videos in SurrealDB with pagination. Shows title, channel, views, URL. | `--limit`, `--offset` |
| `search_videos.py` | Semantic search over SurrealDB using Infinity embeddings. Finds videos by meaning, not just keywords. | `--limit`, `--channel` |
| `delete_video.py` | Deletes a single video from SurrealDB with confirmation prompt. Does not delete the archive file. | `--yes` to skip confirm |

## Data Flow

```
fetch_channel_videos  ->  CSV queue
                            |  (ingestion)
                       Archive JSON files
                            |
update_video_metadata  ->  Enriches archives
filter_description_urls -> Classifies URLs
                            |
migrate_to_surrealdb   ->  SurrealDB + MinIO
populate_surrealdb     ->  SurrealDB + embeddings
backfill_embeddings    ->  Fill embedding gaps
validate_data          ->  Verify integrity
                            |
list_videos / search_videos / delete_video  ->  Query & manage
```
