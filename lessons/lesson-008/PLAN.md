# Lesson 008: Batch Processing with OpenAI

**Status**: Ready to Build
**Estimated Time**: 60-90 minutes
**Prerequisites**: Lesson 007 (Cache Manager with cached content)

---

## Learning Objectives

By the end of this lesson, you will understand:

1. **OpenAI Batch API** - How to process large datasets cost-effectively (50% savings)
2. **JSONL format** - Batch input file structure for OpenAI
3. **Asynchronous workflows** - Submit jobs, monitor status, retrieve results
4. **Result aggregation** - Processing batch outputs and storing in cache
5. **Cost optimization** - When to use batch vs real-time API

---

## What We're Building

### Core Components

1. **BatchProcessor** (`batch/processor.py`)
   - Prepare JSONL batch input files from cached content
   - Submit batch jobs to OpenAI
   - Monitor job status with polling
   - Download and parse results
   - Validate and store tagged content

2. **Batch Scripts** (`scripts/`)
   - `prepare_batch.py` - Create batch input from cache
   - `submit_batch.py` - Submit job to OpenAI
   - `check_status.py` - Monitor batch job progress
   - `process_results.py` - Download results and update cache

3. **Integration with Lesson 007**
   - Load transcripts from Qdrant cache
   - Tag content using batch API
   - Store tags back in cache with metadata

---

## Why OpenAI Batch API?

### Cost Comparison

**Real-time API pricing** (per 1M tokens):
- GPT-4o-mini input: $0.150
- GPT-4o-mini output: $0.600

**Batch API pricing** (per 1M tokens):
- GPT-4o-mini input: $0.075 (50% off)
- GPT-4o-mini output: $0.300 (50% off)

**Example**: Tagging 169 videos with ~150k input tokens + 10k output tokens
- Real-time cost: ~$28.50
- Batch cost: ~$14.25
- **Savings: $14.25 (50%)**

### Trade-offs

**Batch API Pros:**
- ✅ 50% cost reduction
- ✅ Automatic rate limiting
- ✅ 24-hour processing window
- ✅ Perfect for non-urgent analysis
- ✅ No manual batching logic needed

**Batch API Cons:**
- ❌ Slower (24-48 hours typical, can be faster)
- ❌ No streaming responses
- ❌ Results come all at once
- ❌ Less immediate feedback

**When to use Batch API:**
- Large datasets (100+ items)
- Non-urgent analysis
- Cost is a primary concern
- Don't need real-time results

**When to use Real-time API:**
- Interactive applications
- Need immediate results
- Small datasets (<10 items)
- Streaming required

---

## OpenAI Batch API Workflow

```
1. PREPARE
   ├─ Load content from cache
   ├─ Generate batch input (JSONL)
   └─ Validate format

2. SUBMIT
   ├─ Upload input file to OpenAI
   ├─ Create batch job
   └─ Get batch_id

3. MONITOR
   ├─ Poll batch status
   ├─ Wait for completion
   └─ Handle errors/cancellations

4. RETRIEVE
   ├─ Download result file
   ├─ Parse JSONL output
   └─ Validate responses

5. PROCESS
   ├─ Extract tags from results
   ├─ Update cache with tags
   └─ Generate summary report
```

---

## JSONL Format for Batch API

### Input File Format

Each line is a separate JSON request:

```jsonl
{"custom_id": "youtube:GTEz5WWbfiw", "method": "POST", "url": "/v1/chat/completions", "body": {"model": "gpt-4o-mini", "messages": [{"role": "system", "content": "..."}, {"role": "user", "content": "..."}]}}
{"custom_id": "youtube:uR7sC68Eazk", "method": "POST", "url": "/v1/chat/completions", "body": {"model": "gpt-4o-mini", "messages": [{"role": "system", "content": "..."}, {"role": "user", "content": "..."}]}}
```

### Output File Format

Each line is a response:

```jsonl
{"id": "batch_req_...", "custom_id": "youtube:GTEz5WWbfiw", "response": {"status_code": 200, "body": {"choices": [{"message": {"content": "..."}}]}}}
{"id": "batch_req_...", "custom_id": "youtube:uR7sC68Eazk", "response": {"status_code": 200, "body": {"choices": [{"message": {"content": "..."}}]}}}
```

---

## Implementation Steps

### Step 1: Create BatchProcessor Class (30 min)

Core functionality for batch operations:

```python
class BatchProcessor:
    def __init__(self, cache: QdrantCache, api_key: str):
        self.cache = cache
        self.client = OpenAI(api_key=api_key)

    def prepare_batch_input(
        self,
        filters: dict,
        system_prompt: str,
        output_file: Path
    ) -> int:
        """Create JSONL batch input from cached content."""
        ...

    def submit_batch(self, input_file: Path) -> str:
        """Upload file and create batch job. Returns batch_id."""
        ...

    def check_status(self, batch_id: str) -> dict:
        """Check batch job status."""
        ...

    def download_results(self, batch_id: str, output_file: Path):
        """Download completed batch results."""
        ...

    def process_results(self, results_file: Path) -> dict:
        """Parse results and update cache with tags."""
        ...
```

### Step 2: Build CLI Scripts (30 min)

Create user-friendly scripts for each workflow step:

1. **prepare_batch.py** - Interactive batch preparation
2. **submit_batch.py** - Submit job with confirmation
3. **check_status.py** - Status monitoring with auto-refresh
4. **process_results.py** - Download and store results

### Step 3: Testing & Integration (30 min)

1. Test with small batch (5 videos)
2. Verify tagging quality
3. Run full batch (all cached videos)
4. Validate results

---

## Usage Examples

### Example 1: Full Workflow

```bash
# Step 1: Prepare batch input from cached videos
cd lessons/lesson-008/scripts
uv run python prepare_batch.py \
  --collection nate_content \
  --output batch_input.jsonl

# Output: Created batch_input.jsonl with 169 requests

# Step 2: Submit to OpenAI
uv run python submit_batch.py --input batch_input.jsonl

# Output:
# Uploaded file: file-abc123
# Created batch: batch_xyz789
# Status: validating
# Estimated completion: 24 hours

# Step 3: Monitor status (run periodically)
uv run python check_status.py --batch-id batch_xyz789

# Output:
# Status: in_progress
# Completed: 45/169 (27%)
# Estimated time remaining: 18 hours

# Step 4: Process results (when complete)
uv run python process_results.py --batch-id batch_xyz789

# Output:
# Downloaded results: 169 items
# Updated cache with tags: 169 items
# Total cost: $14.25
```

### Example 2: Python Integration

```python
from batch import BatchProcessor
from cache import QdrantCache

# Initialize
cache = QdrantCache(collection_name="nate_content")
processor = BatchProcessor(cache, api_key=os.getenv("OPENAI_API_KEY"))

# Prepare batch
system_prompt = "You are a tagging assistant..."
num_items = processor.prepare_batch_input(
    filters={"type": "youtube_video"},
    system_prompt=system_prompt,
    output_file=Path("batch_input.jsonl")
)

print(f"Prepared {num_items} items for batch processing")

# Submit
batch_id = processor.submit_batch(Path("batch_input.jsonl"))
print(f"Batch submitted: {batch_id}")

# Monitor (poll until complete)
while True:
    status = processor.check_status(batch_id)
    if status["status"] == "completed":
        break
    time.sleep(60)  # Check every minute

# Process results
results = processor.process_results(batch_id)
print(f"Tagged {results['successful']} videos")
```

---

## Key Concepts

### 1. JSONL (JSON Lines)

**Format**: One JSON object per line (no commas between objects)

```jsonl
{"id": 1, "name": "Alice"}
{"id": 2, "name": "Bob"}
{"id": 3, "name": "Charlie"}
```

**Why JSONL for batch processing?**
- Easy to stream (process line-by-line)
- Append-only (can add new requests)
- Partial processing (can restart from line N)
- Standard format for batch APIs

### 2. Batch Job Lifecycle

```
queued → validating → in_progress → finalizing → completed
                                 ↓
                              failed
                              expired
                              cancelled
```

**Typical timeline:**
- Upload: <1 minute
- Validation: 1-5 minutes
- Processing: 2-24 hours (depends on queue)
- Finalization: 1-5 minutes

### 3. Custom IDs for Result Matching

Each request needs a `custom_id` to match results:

```python
custom_id = f"youtube:{video_id}"  # Unique identifier

# Later, match results:
result = next(r for r in results if r["custom_id"] == custom_id)
```

### 4. Error Handling

Batch API can have partial failures:

```json
{
  "custom_id": "youtube:xyz",
  "response": {
    "status_code": 400,
    "body": {
      "error": {
        "message": "Invalid request"
      }
    }
  }
}
```

Always check `status_code` and handle errors gracefully.

---

## System Prompt for Tagging

We'll use a structured prompt for consistent tagging:

```python
TAGGING_SYSTEM_PROMPT = """You are a content tagging assistant for AI and technology videos.

Your task: Analyze the video transcript and generate 3-5 relevant tags.

Guidelines:
- Tags should be specific and descriptive
- Use lowercase, hyphenated format (e.g., "multi-agent-systems")
- Focus on key concepts, techniques, and topics
- Include both broad categories and specific details
- Prioritize actionable/technical tags over generic ones

Examples of good tags:
- "pydantic-ai", "prompt-engineering", "cost-optimization"
- "batch-processing", "semantic-search", "vector-databases"

Examples of bad tags:
- "video", "content", "information" (too generic)
- "AI Video Tutorial" (not hyphenated, capitalized)

Return ONLY a JSON object with this structure:
{
  "tags": ["tag1", "tag2", "tag3"],
  "summary": "One-sentence summary of the video content"
}
"""
```

---

## Data Models

### BatchRequest

```python
class BatchRequest(BaseModel):
    custom_id: str
    method: str = "POST"
    url: str = "/v1/chat/completions"
    body: dict

class BatchRequestBody(BaseModel):
    model: str = "gpt-4o-mini"
    messages: list[dict]
    temperature: float = 0.7
    max_tokens: int = 500
```

### BatchResult

```python
class BatchResult(BaseModel):
    custom_id: str
    response: BatchResponse

class BatchResponse(BaseModel):
    status_code: int
    body: dict

class TaggingOutput(BaseModel):
    tags: list[str]
    summary: str
```

---

## Testing Plan

### Unit Tests

1. **JSONL Generation**
   - Test format validity
   - Test with empty cache
   - Test with filters

2. **Batch Submission**
   - Mock OpenAI API
   - Test error handling
   - Test file upload

3. **Result Processing**
   - Test successful responses
   - Test partial failures
   - Test cache updates

### Integration Tests

1. **Small Batch (5 videos)**
   - End-to-end workflow
   - Verify tagging quality
   - Check cost calculation

2. **Full Batch (All cached videos)**
   - Performance testing
   - Error recovery
   - Final results validation

---

## Cost Estimation

### Input Tokens

**Per video transcript** (~1000 words avg):
- System prompt: ~200 tokens
- Transcript: ~1300 tokens
- Total input: ~1500 tokens/video

**For 169 videos**:
- Total input: ~253,500 tokens
- Cost: $0.075 / 1M = $0.019

### Output Tokens

**Per response** (~50 tokens for tags + summary):
- Tags: ~30 tokens
- Summary: ~20 tokens
- Total output: ~50 tokens/video

**For 169 videos**:
- Total output: ~8,450 tokens
- Cost: $0.300 / 1M = $0.0025

### Total Cost

- Input: $0.019
- Output: $0.0025
- **Total: ~$0.02** for 169 videos with gpt-4o-mini

*(Much cheaper than expected! Original estimate was based on larger transcripts)*

---

## Success Criteria

✅ Can prepare batch input from cached content
✅ Can submit batch to OpenAI successfully
✅ Can monitor batch status programmatically
✅ Can download and parse results
✅ Tags are stored in cache with metadata
✅ Cost is 50% less than real-time API
✅ Error handling works for partial failures
✅ Can resume from interruptions

---

## Next Steps

After completing this lesson:

1. **Analyze tagged content** - Search by tags, find patterns
2. **Build recommendation engine** - Use tags for content discovery
3. **Experiment with prompts** - Use `/optimize-prompt` for better tagging
4. **Scale to more content** - Add blogs, papers, podcasts

---

## Notes

### Design Decisions

1. **Why gpt-4o-mini?**
   - Cost-effective ($0.075 input vs $3.00 for gpt-4o)
   - Fast enough for tagging
   - Good quality for structured outputs

2. **Why separate scripts?**
   - Each step is independent
   - Can resume workflow
   - Easier to debug
   - Clear separation of concerns

3. **Why store in cache?**
   - Centralized data storage
   - Enables semantic search on tags
   - Metadata filtering
   - Versioning (can re-tag with new prompts)

### Common Pitfalls

1. **Batch limits** - OpenAI has quotas (check your account tier)
2. **File expiration** - Result files expire after 30 days
3. **Format errors** - Invalid JSONL causes entire batch to fail
4. **Token limits** - Individual requests can't exceed model limits
5. **Cost tracking** - Monitor spending in OpenAI dashboard

---

**Estimated completion time: 60-90 minutes**

Ready to process content at scale with 50% cost savings! 🚀
