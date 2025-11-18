# Shared Utilities for Lessons

This directory contains standalone utilities that lessons can use without creating dependencies on other parts of the codebase.

## Purpose

**Lessons should be self-contained and independent.** They should not depend on:
- `compose/` - Production service code
- `src/` - Future production application code
- `tools/` - Build and development scripts

However, lessons often need common functionality (like loading environment variables). This `shared/` directory provides that without breaking lesson independence.

## Current Utilities

### `env_loader.py`

Helps lessons find and load `.env` files from the git repository root.

**Usage:**

```python
from lessons.shared.env_loader import load_root_env

# Load environment variables from git root/.env
load_root_env()

# Now you can access environment variables
import os
api_key = os.getenv("ANTHROPIC_API_KEY")
```

**Functions:**

- `find_git_root(start_path=None)` - Walks up directory tree to find `.git/` folder
- `load_root_env()` - Loads `.env` from git root directory

## Design Philosophy

These utilities are:

1. **Standalone** - No dependencies on compose/, src/, or tools/
2. **Simple** - Single-purpose, easy to understand
3. **Copied** - Duplicated from other locations rather than imported (avoids coupling)
4. **Lesson-focused** - Designed specifically for lesson needs

## Adding New Utilities

Only add utilities that:

1. Are needed by **multiple lessons** (not just one)
2. Are **truly generic** (not lesson-specific logic)
3. Keep lessons **self-contained** (don't create new dependencies)
4. Are **simple and stable** (unlikely to change frequently)

Examples of good additions:
- Common test fixtures
- Generic data loaders
- Simple validation utilities

Examples of bad additions:
- Business logic
- Agent implementations
- Lesson-specific helpers
