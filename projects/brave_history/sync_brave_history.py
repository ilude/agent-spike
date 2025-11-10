#!/usr/bin/env python3
"""
Wrapper script for incremental Brave history sync.

This script is called by git hooks to perform fast incremental syncs.
"""

from pathlib import Path
from copy_brave_history import safe_incremental_sync

if __name__ == "__main__":
    # Run incremental sync from the data directory
    safe_incremental_sync(Path("data"))
