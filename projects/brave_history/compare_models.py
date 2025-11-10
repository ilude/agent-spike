#!/usr/bin/env python3
"""
Compare tags from two OpenAI models on a sample of video titles.
Stores results in database with model metadata.
"""

import io
import json
import os
import random
import sqlite3
import sys
from datetime import datetime
from pathlib import Path

from openai import OpenAI

from tools.env_loader import load_root_env

# Fix stdout encoding for Windows
if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

# Tagging prompt
TAGGING_SYSTEM_PROMPT = """You are an expert whose responsibility is to help with automatic tagging for a read-it-later app.

You will receive YouTube video titles and metadata. Please analyze the content and suggest relevant tags that describe its key themes, topics, and main ideas.

## RULES
- Aim for a variety of tags, including broad categories, specific keywords, and potential sub-genres
- If the tag is not generic enough, don't include it
- The content can include promotional material, sponsor reads, or channel plugs - focus on the core content
- Aim for 3-5 tags
- If there are no good tags, return an empty array
- Tags should be lowercase and use hyphens for multi-word tags (e.g., "machine-learning")
- Focus on educational and informational value

## OUTPUT FORMAT
Return a JSON object with:
{
  "video_title": "string",
  "tags": ["tag1", "tag2", "tag3"],
  "summary": "Brief 1-sentence description of what the video covers"
}
"""


def get_random_videos(db_path: Path, sample_size: int = 10) -> list[dict]:
    """Get a random sample of videos from the database."""
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    # Get all videos with their tags
    cursor.execute("""
        SELECT v.video_id, v.title, vt.tags as existing_tags
        FROM videos v
        JOIN video_tags vt ON v.video_id = vt.video_id
        ORDER BY RANDOM()
        LIMIT ?
    """, (sample_size,))

    videos = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return videos


def get_tags_from_model(client: OpenAI, model: str, video_title: str) -> dict | None:
    """Get tags from the specified model."""
    try:
        # GPT-5 nano only supports temperature=1 (default)
        params = {
            "model": model,
            "messages": [
                {"role": "system", "content": TAGGING_SYSTEM_PROMPT},
                {"role": "user", "content": f"Video title: {video_title}"},
            ],
        }

        # Only add temperature if not using gpt-5
        if "gpt-5" not in model:
            params["temperature"] = 0.7

        response = client.chat.completions.create(**params)

        content = response.choices[0].message.content
        result = json.loads(content)

        return {
            "tags": result.get("tags", []),
            "summary": result.get("summary", ""),
        }

    except Exception as e:
        print(f"Error with {model}: {e}")
        return None


def init_comparison_table(db_path: Path) -> None:
    """Initialize model comparison table."""
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS model_comparisons (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            video_id TEXT,
            model_1 TEXT,
            model_1_tags TEXT,
            model_2 TEXT,
            model_2_tags TEXT,
            overlap_percentage REAL,
            comparison_date TIMESTAMP
        )
    """)

    conn.commit()
    conn.close()


def save_comparison(db_path: Path, video_id: str, model1: str, tags1: list, model2: str, tags2: list, overlap: float) -> None:
    """Save comparison results to database."""
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    cursor.execute("""
        INSERT INTO model_comparisons
        (video_id, model_1, model_1_tags, model_2, model_2_tags, overlap_percentage, comparison_date)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    """, (
        video_id,
        model1,
        json.dumps(tags1),
        model2,
        json.dumps(tags2),
        overlap,
        datetime.now().isoformat(),
    ))

    conn.commit()
    conn.close()


def main():
    """Main comparison function."""
    # Load .env
    load_root_env()

    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        print("Error: OPENAI_API_KEY not found")
        return

    client = OpenAI(api_key=api_key)
    db_path = Path(__file__).parent / "channel_cache.db"

    # Initialize comparison table
    init_comparison_table(db_path)

    # Get random sample
    sample_size = 25
    model_1 = "gpt-5-nano"
    model_2 = "gpt-5-mini"

    print(f"Fetching random sample of {sample_size} videos...\n")
    videos = get_random_videos(db_path, sample_size=sample_size)

    if not videos:
        print("No videos found in database")
        return

    print(f"Comparing: {model_1} vs {model_2}\n")
    print("=" * 80)

    overlaps = []

    for i, video in enumerate(videos, 1):
        video_id = video["video_id"]
        title = video["title"]

        print(f"\n[{i}/{sample_size}] {title[:70]}")
        print("-" * 80)

        # Get tags from both models
        print(f"Getting {model_1} tags...")
        nano_result = get_tags_from_model(client, model_1, title)

        print(f"Getting {model_2} tags...")
        mini_result = get_tags_from_model(client, model_2, title)

        if nano_result and mini_result:
            nano_tags = nano_result["tags"]
            mini_tags = mini_result["tags"]

            print(f"\n{model_1}: {nano_tags}")
            print(f"{model_2}: {mini_tags}")

            # Calculate differences
            nano_set = set(nano_tags)
            mini_set = set(mini_tags)

            added = nano_set - mini_set
            removed = mini_set - nano_set
            same = nano_set & mini_set

            print(f"\nComparison:")
            print(f"  Same tags:    {list(same) if same else 'none'}")
            if added:
                print(f"  {model_1} adds:  {list(added)}")
            if removed:
                print(f"  {model_2} adds:  {list(removed)}")

            overlap_pct = (len(same) / max(len(nano_set), len(mini_set)) * 100) if nano_set or mini_set else 0
            print(f"  Overlap:      {overlap_pct:.0f}%")
            overlaps.append(overlap_pct)

            # Save to database
            save_comparison(db_path, video_id, model_1, nano_tags, model_2, mini_tags, overlap_pct)

        print()

    # Summary
    if overlaps:
        avg_overlap = sum(overlaps) / len(overlaps)
        print("=" * 80)
        print(f"\nSUMMARY")
        print(f"Average Overlap: {avg_overlap:.1f}%")
        print(f"Min Overlap: {min(overlaps):.0f}%")
        print(f"Max Overlap: {max(overlaps):.0f}%")
        print(f"\nComparisons saved to database!")
        print("=" * 80)


if __name__ == "__main__":
    main()
