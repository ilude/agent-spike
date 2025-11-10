# Lesson 008: Batch Processing with OpenAI

**Quick Reference Guide**

## What This Lesson Teaches

- OpenAI Batch API for 50% cost savings
- JSONL format for batch processing
- Asynchronous workflows (submit, monitor, retrieve)
- Cost-effective content tagging at scale

## Quick Start

### 1. Install Dependencies

```bash
uv sync --group lesson-008
```

### 2. Set Up Environment

```bash
# Copy API keys from lesson-001
cp ../lesson-001/.env .
```

### 3. Prepare Batch Input

```bash
cd scripts
uv run python prepare_batch.py \
  --collection nate_content \
  --output batch_input.jsonl
```

### 4. Submit Batch

```bash
uv run python submit_batch.py --input batch_input.jsonl
# Note the batch_id from output
```

### 5. Monitor Status

```bash
uv run python check_status.py --batch-id batch_xyz789
```

### 6. Process Results (when complete)

```bash
uv run python process_results.py --batch-id batch_xyz789
```

## Core Components

### BatchProcessor

Main class for batch operations:

```python
from batch import BatchProcessor
from cache import QdrantCache

cache = QdrantCache(collection_name="nate_content")
processor = BatchProcessor(cache, api_key=os.getenv("OPENAI_API_KEY"))

# Prepare batch
processor.prepare_batch_input(
    filters={"type": "youtube_video"},
    system_prompt="Tag this content...",
    output_file=Path("batch.jsonl")
)

# Submit
batch_id = processor.submit_batch(Path("batch.jsonl"))

# Monitor
status = processor.check_status(batch_id)

# Process
results = processor.process_results(batch_id)
```

## CLI Scripts

All scripts in `scripts/` directory:

### prepare_batch.py
Generate JSONL batch input from cached content

```bash
uv run python prepare_batch.py \
  --collection content \
  --filters type=youtube_video \
  --output batch_input.jsonl \
  --limit 10  # Optional
```

### submit_batch.py
Upload and submit batch job to OpenAI

```bash
uv run python submit_batch.py --input batch_input.jsonl
```

### check_status.py
Monitor batch job progress

```bash
# Single check
uv run python check_status.py --batch-id batch_xyz

# Auto-refresh every 60 seconds
uv run python check_status.py --batch-id batch_xyz --watch
```

### process_results.py
Download results and update cache with tags

```bash
uv run python process_results.py --batch-id batch_xyz
```

## Usage Examples

### Example 1: Tag All Cached Videos

```bash
# Prepare batch for all YouTube videos
uv run python prepare_batch.py \
  --collection nate_content \
  --output nate_batch.jsonl

# Submit
uv run python submit_batch.py --input nate_batch.jsonl
# Output: Batch ID: batch_abc123

# Wait 24-48 hours, then check
uv run python check_status.py --batch-id batch_abc123

# When complete, process
uv run python process_results.py --batch-id batch_abc123
```

### Example 2: Test with Small Sample

```bash
# Prepare just 5 videos for testing
uv run python prepare_batch.py \
  --collection nate_content \
  --limit 5 \
  --output test_batch.jsonl

# Submit and monitor
uv run python submit_batch.py --input test_batch.jsonl
uv run python check_status.py --batch-id <batch_id> --watch
```

### Example 3: Python Integration

```python
from pathlib import Path
import os
import time
from batch import BatchProcessor
from cache import QdrantCache

# Setup
cache = QdrantCache(collection_name="nate_content")
processor = BatchProcessor(cache, api_key=os.getenv("OPENAI_API_KEY"))

# Prepare
count = processor.prepare_batch_input(
    filters={"type": "youtube_video"},
    system_prompt=processor.DEFAULT_TAGGING_PROMPT,
    output_file=Path("batch.jsonl")
)
print(f"Prepared {count} items")

# Submit
batch_id = processor.submit_batch(Path("batch.jsonl"))
print(f"Submitted: {batch_id}")

# Poll until complete
while True:
    status = processor.check_status(batch_id)
    print(f"Status: {status['status']} ({status.get('completed', 0)}/{status.get('total', 0)})")

    if status["status"] == "completed":
        break
    elif status["status"] in ["failed", "cancelled"]:
        raise Exception(f"Batch {status['status']}")

    time.sleep(300)  # Check every 5 minutes

# Download and process
results = processor.process_results(batch_id)
print(f"Success: {results['successful']}/{results['total']}")
print(f"Cost: ${results['total_cost']:.4f}")
```

## File Structure

```
lesson-008/
├── batch/
│   ├── __init__.py              # Module exports
│   ├── processor.py             # BatchProcessor class
│   ├── models.py                # Data models
│   └── prompts.py               # System prompts
├── scripts/
│   ├── prepare_batch.py         # Create batch input
│   ├── submit_batch.py          # Submit to OpenAI
│   ├── check_status.py          # Monitor progress
│   └── process_results.py       # Download & process results
├── PLAN.md                      # Detailed learning plan
├── README.md                    # This file
└── .env                         # API keys (gitignored)
```

## Common Commands

```bash
# Full workflow
cd lessons/lesson-008/scripts

# Step 1: Prepare
uv run python prepare_batch.py --collection nate_content --output batch.jsonl

# Step 2: Submit
uv run python submit_batch.py --input batch.jsonl

# Step 3: Monitor (returns batch_id)
uv run python check_status.py --batch-id <id> --watch

# Step 4: Process
uv run python process_results.py --batch-id <id>
```

## Cost Savings

### Real-time API vs Batch API

| Model | Real-time Input | Real-time Output | Batch Input | Batch Output | Savings |
|-------|----------------|------------------|-------------|--------------|---------|
| gpt-4o-mini | $0.150/1M | $0.600/1M | $0.075/1M | $0.300/1M | **50%** |
| gpt-4o | $3.00/1M | $15.00/1M | $1.50/1M | $7.50/1M | **50%** |

### Example Calculation (169 videos)

**Assumptions:**
- 1500 tokens input per video (system prompt + transcript)
- 50 tokens output per video (tags + summary)

**Real-time cost:**
- Input: 253,500 tokens × $0.150 / 1M = $0.038
- Output: 8,450 tokens × $0.600 / 1M = $0.005
- **Total: $0.043**

**Batch cost:**
- Input: 253,500 tokens × $0.075 / 1M = $0.019
- Output: 8,450 tokens × $0.300 / 1M = $0.0025
- **Total: $0.022**

**Savings: $0.021 (49% reduction)**

## Key Concepts

**JSONL (JSON Lines)**: One JSON object per line

**custom_id**: Unique identifier to match requests with results

**Batch lifecycle**: queued → validating → in_progress → completed

**Partial failures**: Individual requests can fail; handle gracefully

**File expiration**: Result files expire after 30 days

## Troubleshooting

**"Batch failed during validation"**
→ Check JSONL format (one object per line, valid JSON)

**"File not found"**
→ Result files expire after 30 days. Re-run if needed.

**"Rate limit exceeded"**
→ Batch API has separate quotas. Check OpenAI dashboard.

**"Cost higher than expected"**
→ Verify model (should be gpt-4o-mini). Check token usage in results.

## Next Steps

After completing this lesson:

1. Review `PLAN.md` for detailed implementation
2. Run test batch with 5 videos
3. Process full dataset (169+ videos)
4. Explore tagged content with semantic search
5. Move to Lesson 009: Recommendation engine

## Dependencies

- `openai` - OpenAI Python client
- `python-dotenv` - Environment variables
- `tqdm` - Progress bars
- `rich` - Console output
- Lesson 007 cache (Qdrant)

(All installed via `uv sync --group lesson-008`)

---

For detailed learning objectives and implementation, see `PLAN.md`.
