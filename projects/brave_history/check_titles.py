#!/usr/bin/env python3
import sqlite3
from pathlib import Path

db_path = Path("../data/brave_history.2025-11-06.sqlite")
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
