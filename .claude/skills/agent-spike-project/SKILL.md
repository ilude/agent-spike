# Agent-Spike Project Patterns

**Auto-activates when**: Working with `tools/` directory, `projects/mentat/scripts/`, importing from `tools.services.*`, or creating new Python scripts for the project.

## Overview

This skill documents agent-spike-specific patterns for using the `tools/` library, mentat project structure, and common gotchas. For general Python/testing/philosophy patterns, see:
- `python-workflow` skill - UV package management, virtual environments
- `testing-workflow` skill - Pytest patterns, TDD practices
- `development-philosophy` skill - Experiment-driven, fail-fast approach

## Tools Directory Structure

The `tools/` directory contains shared utilities and services:

```
tools/
├── env_loader.py              # Environment variable loading
├── dotenv.py                  # Alternative: load_root_env() helper
├── services/
│   ├── youtube/
│   │   ├── __init__.py       # Exports YouTubeTranscriptService
│   │   └── transcript_service.py
│   └── archive/
│       ├── models.py         # Archive data models
│       └── local_writer.py   # LocalArchiveWriter service
└── ...
```

## Environment Loading Patterns

**CRITICAL**: Always load environment variables BEFORE instantiating services that need API keys.

### Pattern 1: Using `dotenv` directly (Recommended for scripts)

```python
from pathlib import Path
from dotenv import load_dotenv

# Add project root to path
project_root = Path(__file__).parent.parent.parent  # Adjust depth as needed
sys.path.insert(0, str(project_root))

# Load .env BEFORE importing services
env_path = project_root / ".env"
load_dotenv(env_path)

# NOW import services that need env vars
from tools.services.youtube import YouTubeTranscriptService
```

### Pattern 2: Using `tools/dotenv.py` helper

```python
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

# Load environment using helper (finds git root automatically)
from tools.dotenv import load_root_env
load_root_env()

# NOW import services
from tools.services.youtube import YouTubeTranscriptService
```

### Pattern 3: Using `tools/env_loader.py` (Legacy)

```python
# This pattern is older but still works
from tools.env_loader import load_env
load_env()

from tools.services.youtube import YouTubeTranscriptService
```

**Order matters**: Load environment → Import services → Use services

## YouTube Transcript Service

### Proxy Configuration

The `YouTubeTranscriptService` automatically configures Webshare proxy from environment variables:

**Required environment variables** (in `.env`):
```bash
WEBSHARE_PROXY_USERNAME=your_username
WEBSHARE_PROXY_PASSWORD=your_password
YOUTUBE_TRANSCRIPT_USE_PROXY=true  # Optional, defaults to true
```

**GOTCHA**: If you create a `YouTubeTranscriptService()` instance BEFORE loading the `.env` file, the proxy will NOT be configured, and you'll get rate limited by YouTube when making bulk requests.

### Basic Usage

```python
from dotenv import load_dotenv
from pathlib import Path

# MUST load .env first!
project_root = Path(__file__).parent.parent.parent.parent
load_dotenv(project_root / ".env")

from tools.services.youtube import YouTubeTranscriptService

# Create service (proxy auto-configures from env vars)
service = YouTubeTranscriptService()

# Verify proxy is configured
proxy_info = service.get_proxy_info()
print(f"Proxy configured: {proxy_info['proxy_configured']}")

# Fetch plain text transcript
transcript = service.fetch_transcript("dQw4w9WgXcQ")

# Fetch timed transcript (with timestamps)
timed_transcript = service.fetch_timed_transcript("dQw4w9WgXcQ")
# Returns: [{"text": str, "start": float, "duration": float}, ...]
```

### Debugging Proxy Issues

If you're getting YouTube rate limits:
1. Check if proxy is configured: `service.get_proxy_info()`
2. Verify .env was loaded BEFORE service instantiation
3. Check environment variables are set:
   ```python
   import os
   print(os.getenv("WEBSHARE_PROXY_USERNAME"))
   print(os.getenv("WEBSHARE_PROXY_PASSWORD"))
   ```

## Archive Services

### LocalArchiveWriter

Archives expensive API calls (transcripts, LLM outputs) for reprocessing:

```python
from tools.services.archive import LocalArchiveWriter

archive = LocalArchiveWriter()

# Archive YouTube video with timed transcript
archive.archive_youtube_video(
    video_id="dQw4w9WgXcQ",
    url="https://www.youtube.com/watch?v=dQw4w9WgXcQ",
    transcript="plain text transcript",
    timed_transcript=[{"text": "...", "start": 0.0, "duration": 1.5}],
    metadata={"title": "Video Title", "channel": "Channel Name"},
)

# Archive LLM outputs (for cost tracking)
archive.add_llm_output(
    video_id="dQw4w9WgXcQ",
    output_type="tags",
    output_value=["tag1", "tag2"],
    model="claude-3-5-haiku-20241022",
    cost_usd=0.0012,
)

# Track processing versions
archive.add_processing_record(
    video_id="dQw4w9WgXcQ",
    version="v1_full_embed",
    collection_name="cached_content",
)
```

**Archive location**: `projects/data/archive/youtube/YYYY-MM/VIDEO_ID.json`

**Philosophy**: Archive BEFORE processing. Enables experimentation without re-fetching.

## Mentat Project Structure

The mentat project is a RAG-based chat application with video transcript search:

```
projects/mentat/
├── api/
│   └── main.py              # FastAPI backend
├── frontend/
│   └── src/routes/          # SvelteKit frontend
├── scripts/
│   ├── index_videos.py                    # SurrealDB indexing
│   └── update_archives_with_timestamps.py # Archive updates
└── docker-compose.yml       # Multi-service setup
```

### Common Script Patterns

**New mentat script template**:

```python
"""Script description."""

import sys
from pathlib import Path
from dotenv import load_dotenv

# Add project root to path
project_root = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(project_root))

# Load environment FIRST
env_path = project_root / ".env"
load_dotenv(env_path)

# NOW import project services
from tools.services.youtube import YouTubeTranscriptService
from tools.services.archive import LocalArchiveWriter

# Configuration
ARCHIVE_DIR = project_root / "projects" / "data" / "archive" / "youtube" / "2025-11"

def main():
    """Main function."""
    # Create services
    transcript_service = YouTubeTranscriptService()
    archive_service = LocalArchiveWriter()

    # Verify proxy
    proxy_info = transcript_service.get_proxy_info()
    print(f"Proxy configured: {proxy_info['proxy_configured']}")

    # Do work...

if __name__ == "__main__":
    main()
```

## Common Gotchas

### 1. YouTubeTranscriptService without .env loaded
**Symptom**: YouTube rate limiting on bulk operations
**Cause**: Service instantiated before loading .env, proxy not configured
**Fix**: Load .env BEFORE importing/creating service

### 2. Relative imports in scripts
**Symptom**: `ModuleNotFoundError` when running scripts
**Cause**: Project root not in sys.path
**Fix**: Add `sys.path.insert(0, str(project_root))` at top of script

### 3. Encrypted .env file
**Symptom**: API keys not loading even with dotenv
**Cause**: Repository uses git-crypt, .env is encrypted
**Fix**: Run `git-crypt unlock` or set environment variables manually

### 4. Running scripts from wrong directory
**Symptom**: Can't find .env or archive files
**Cause**: Script expects to run from its own directory
**Fix**: Use absolute paths with `project_root` or run from script directory

### 5. Archive files corrupted during updates
**Symptom**: `JSONDecodeError: Expecting value: line 1 column 1`
**Cause**: Script interrupted while writing to file
**Fix**: Re-fetch the video or restore from git if committed

## Testing Patterns

When testing scripts that use services:

```python
import pytest
from unittest.mock import Mock, patch

def test_script_with_proxy():
    """Test that script properly configures proxy."""
    with patch.dict(os.environ, {
        "WEBSHARE_PROXY_USERNAME": "testuser",
        "WEBSHARE_PROXY_PASSWORD": "testpass",
    }):
        service = YouTubeTranscriptService()
        assert service.is_proxy_configured() == True

def test_youtube_service_without_env():
    """Test that service works without proxy."""
    with patch.dict(os.environ, {}, clear=True):
        service = YouTubeTranscriptService()
        assert service.is_proxy_configured() == False
```

## Development Workflow

1. **Start with existing patterns** - Check `projects/mentat/scripts/` for similar scripts
2. **Test immediately** - Create test file alongside script
3. **Run with `uv run python`** - Handles virtual environment automatically
4. **Archive before processing** - Save API responses before transforming
5. **Handle mixed data gracefully** - Not all archives will have all fields

## References

- **`python-workflow` skill** - UV commands, virtual environment patterns
- **`testing-workflow` skill** - Pytest setup, mocking, coverage
- **`development-philosophy` skill** - Experiment-driven approach, KISS principle
- **`archive-reprocessing` skill** - Version-tracked archive transformations
- **Project CLAUDE.md** - Overall project structure and learning lessons

---

**Remember**: Load .env → Import services → Verify proxy → Do work
