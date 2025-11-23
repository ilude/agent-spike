#!/usr/bin/env python3
import sqlite3
from pathlib import Path

# Use relative data directory - finds the most recent history file
data_dir = Path(__file__).parent.parent / "data" / "queues" / "brave_history"
history_files = sorted(data_dir.glob("brave_history.*.sqlite"), reverse=True)
if not history_files:
    raise FileNotFoundError(f"No brave_history.*.sqlite files found in {data_dir}")
db_path = history_files[0]
print(f"Using history file: {db_path.name}\n")

conn = sqlite3.connect(db_path)
cursor = conn.cursor()

cursor.execute("""
    SELECT u.title
    FROM visits v
    JOIN urls u ON v.url = u.id
    WHERE u.url LIKE '%youtube.com/watch%'
    GROUP BY u.title
    LIMIT 15
""")

print("Sample YouTube video titles:\n")
for i, (title,) in enumerate(cursor.fetchall(), 1):
    print(f"{i}. {title}")

conn.close()
