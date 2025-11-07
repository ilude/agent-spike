#!/usr/bin/env python3
"""
Copy Brave browser history to local data/ directory and consolidate.

This script:
1. Copies the Brave history SQLite database to data/brave_history.HOSTNAME.sqlite
2. Consolidates all machine-specific files into data/brave_history.sqlite
3. Removes duplicates based on URL and visit timestamp
4. Only the consolidated brave_history.sqlite is committed (machine files are gitignored)
"""

import shutil
import sys
import platform
import sqlite3
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
    Files are named using the machine hostname.

    Args:
        dest_dir: Destination directory (default: "data" in current directory)
    """
    dest_dir = Path(dest_dir)
    dest_dir.mkdir(exist_ok=True)

    source = get_brave_history_path()
    machine_name = platform.node()  # Get hostname/machine name
    destination = dest_dir / f"brave_history.{machine_name}.sqlite"

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


def consolidate_history_files(data_dir: Path) -> None:
    """
    Consolidate all history files (including existing brave_history.sqlite) into a new file.
    Uses brave_history.tmp.sqlite during consolidation, then replaces brave_history.sqlite.
    Removes duplicates based on URL and visit timestamp.
    
    Args:
        data_dir: Directory containing the history files
    """
    # Find all history files including the consolidated one and machine-specific ones
    all_files = list(data_dir.glob("brave_history*.sqlite"))
    # Exclude any existing .tmp file
    all_files = [f for f in all_files if not f.name.endswith(".tmp.sqlite")]
    
    if not all_files:
        print("No history files to consolidate")
        return
    
    temp_path = data_dir / "brave_history.tmp.sqlite"
    final_path = data_dir / "brave_history.sqlite"
    
    # Remove any existing temp file
    if temp_path.exists():
        temp_path.unlink()
    
    print(f"\nConsolidating {len(all_files)} history file(s)...")
    for f in all_files:
        print(f"  - {f.name}")
    
    # Create temporary consolidated database
    temp_conn = sqlite3.connect(temp_path)
    temp_cursor = temp_conn.cursor()
    
    # Get schema from first file
    first_file = all_files[0]
    source_conn = sqlite3.connect(first_file)
    source_cursor = source_conn.cursor()
    
    # Copy schema for main tables
    source_cursor.execute("""
        SELECT sql FROM sqlite_master 
        WHERE type='table' AND name IN ('urls', 'visits')
        ORDER BY name
    """)
    
    for (sql,) in source_cursor.fetchall():
        if sql:
            temp_cursor.execute(sql)
    
    source_conn.close()
    
    # Track statistics
    total_processed = 0
    
    # Process each file
    for history_file in all_files:
        print(f"  Processing: {history_file.name}")
        
        source_conn = sqlite3.connect(history_file)
        source_cursor = source_conn.cursor()
        
        # Insert URLs (ignore duplicates by URL text)
        source_cursor.execute("SELECT id, url, title, visit_count, last_visit_time FROM urls")
        urls = source_cursor.fetchall()
        
        for url_data in urls:
            try:
                temp_cursor.execute("""
                    INSERT OR IGNORE INTO urls (url, title, visit_count, last_visit_time)
                    VALUES (?, ?, ?, ?)
                """, url_data[1:])  # Skip the source id
            except sqlite3.Error:
                pass  # Skip on error
        
        # Get URL ID mappings (old ID -> new ID)
        source_cursor.execute("SELECT id, url FROM urls")
        url_mapping = {}
        for old_id, url in source_cursor.fetchall():
            temp_cursor.execute("SELECT id FROM urls WHERE url = ?", (url,))
            result = temp_cursor.fetchone()
            if result:
                url_mapping[old_id] = result[0]
        
        # Insert visits (ignore duplicates by URL and timestamp)
        source_cursor.execute("SELECT id, url, visit_time, from_visit, transition FROM visits")
        visits = source_cursor.fetchall()
        
        for visit_data in visits:
            old_url_id = visit_data[1]
            if old_url_id in url_mapping:
                new_url_id = url_mapping[old_url_id]
                try:
                    temp_cursor.execute("""
                        INSERT OR IGNORE INTO visits (url, visit_time, from_visit, transition)
                        VALUES (?, ?, ?, ?)
                    """, (new_url_id, visit_data[2], visit_data[3], visit_data[4]))
                    total_processed += temp_cursor.rowcount
                except sqlite3.Error:
                    pass  # Skip on error
        
        source_conn.close()
    
    # Commit and get final statistics
    temp_conn.commit()
    
    temp_cursor.execute("SELECT COUNT(*) FROM urls")
    final_urls = temp_cursor.fetchone()[0]
    
    temp_cursor.execute("SELECT COUNT(*) FROM visits")
    final_visits = temp_cursor.fetchone()[0]
    
    temp_conn.close()
    
    # Replace the old file with the new consolidated one
    if final_path.exists():
        final_path.unlink()
    
    temp_path.rename(final_path)
    
    print(f"\n[OK] Consolidated database created:")
    print(f"  Total URLs: {final_urls:,}")
    print(f"  Total visits: {final_visits:,}")
    print(f"  Saved to: {final_path.name}")


if __name__ == "__main__":
    copy_brave_history()
    
    # Consolidate all machine files into single database
    data_dir = Path("data")
    if data_dir.exists():
        consolidate_history_files(data_dir)
