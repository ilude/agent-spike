#!/usr/bin/env python3
"""
Copy Brave browser history to local data/ directory.

This script copies the Brave history SQLite database to a local data/ directory
for analysis. The actual History file is gitignored - only this script is tracked.
"""

import shutil
import sys
from datetime import datetime
from pathlib import Path


def get_brave_history_path() -> Path:
    """Get the path to the Brave browser history file."""
    if sys.platform == "win32":
        # Windows path
        brave_path = Path.home() / "AppData" / "Local" / "BraveSoftware" / "Brave-Browser" / "User Data" / "Default" / "History"
    elif sys.platform == "darwin":
        # macOS path
        brave_path = Path.home() / "Library" / "Application Support" / "BraveSoftware" / "Brave-Browser" / "Default" / "History"
    elif sys.platform == "linux":
        # Linux path
        brave_path = Path.home() / ".config" / "BraveSoftware" / "Brave-Browser" / "Default" / "History"
    else:
        raise OSError(f"Unsupported operating system: {sys.platform}")

    return brave_path


def copy_brave_history(dest_dir: Path | str = "data") -> None:
    """
    Copy Brave history file to the specified destination directory.

    Args:
        dest_dir: Destination directory (default: "data" in current directory)
    """
    dest_dir = Path(dest_dir)
    dest_dir.mkdir(exist_ok=True)

    source = get_brave_history_path()
    today = datetime.now().strftime("%Y-%m-%d")
    destination = dest_dir / f"brave_history.{today}.sqlite"

    if not source.exists():
        print(f"Error: Brave history file not found at {source}")
        sys.exit(1)

    try:
        print(f"Copying Brave history...")
        print(f"  From: {source}")
        print(f"  To:   {destination}")

        # Remove existing file if it exists
        if destination.exists():
            destination.unlink()

        # Copy the file
        shutil.copy2(source, destination)

        # Get file info
        size_mb = destination.stat().st_size / (1024 * 1024)
        print(f"[OK] Success! Copied {size_mb:.1f} MB")

    except PermissionError:
        print(f"Error: Permission denied. Make sure Brave browser is closed.")
        sys.exit(1)
    except Exception as e:
        print(f"Error: Failed to copy file: {e}")
        sys.exit(1)


if __name__ == "__main__":
    copy_brave_history()
