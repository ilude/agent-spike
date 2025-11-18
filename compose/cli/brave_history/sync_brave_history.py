#!/usr/bin/env python3
"""
Wrapper script for incremental Brave history sync.

This script is called by git hooks to perform fast incremental syncs.
"""

from pathlib import Path
from copy_brave_history import safe_incremental_sync

if __name__ == "__main__":
    # Run incremental sync from the data directory
    # Path from tools/scripts/brave_history/ to project root, then to data
    # __file__.parent = tools/scripts/brave_history/
    # __file__.parent.parent.parent.parent = project root
    project_root = Path(__file__).parent.parent.parent.parent
    data_dir = project_root / "projects" / "data" / "brave_history"
    safe_incremental_sync(data_dir)
