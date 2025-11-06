#!/usr/bin/env python3
"""
Generate tags for YouTube videos using OpenAI GPT API.

Tags videos based on their titles using OpenAI's GPT-4o mini model.
Stores tags in SQLite cache to avoid reprocessing.
Aggregates video tags into channel tags.
"""

import io
import json
import os
import sqlite3
import sys
from datetime import datetime
from pathlib import Path
from collections import defaultdict, Counter

from dotenv import load_dotenv
from openai import OpenAI

from youtube_cache import find_env_file, YouTubeCache

# Fix stdout encoding for Windows
if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')


# Tagging prompt from lesson-001
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


class VideoTagger:
    """Tags YouTube videos using OpenAI API with caching."""

    def __init__(self, cache_db_path: str = "channel_cache.db"):
        """Initialize the tagger with OpenAI client and database."""
        # Load .env from git root
        env_path = find_env_file()
        if env_path:
            load_dotenv(env_path)

        self.api_key = os.getenv("OPENAI_API_KEY")
        if not self.api_key:
            raise ValueError("OPENAI_API_KEY not found. Set it in .env or environment.")

        self.client = OpenAI(api_key=self.api_key)
        self.cache_db = Path(cache_db_path)

    def get_untagged_videos(self) -> list[dict]:
        """Get videos from cache that haven't been tagged yet."""
        conn = sqlite3.connect(self.cache_db)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        cursor.execute("""
            SELECT v.video_id, v.title, v.channel_id, v.channel_name
            FROM videos v
            LEFT JOIN video_tags vt ON v.video_id = vt.video_id
            WHERE vt.video_id IS NULL
            ORDER BY v.video_id
        """)

        videos = [dict(row) for row in cursor.fetchall()]
        conn.close()
        return videos

    def generate_tags(self, video_title: str) -> dict | None:
        """Generate tags for a video using OpenAI."""
        try:
            response = self.client.chat.completions.create(
                model="gpt-5-nano",
                messages=[
                    {"role": "system", "content": TAGGING_SYSTEM_PROMPT},
                    {"role": "user", "content": f"Video title: {video_title}"},
                ],
                temperature=0.7,
            )

            content = response.choices[0].message.content
            result = json.loads(content)

            return {
                "tags": result.get("tags", []),
                "summary": result.get("summary", ""),
            }

        except json.JSONDecodeError:
            print(f"Failed to parse JSON for: {video_title}")
            return None
        except Exception as e:
            print(f"Error tagging '{video_title}': {e}")
            return None

    def save_video_tags(self, video_id: str, tags: list[str], summary: str) -> None:
        """Save video tags to database."""
        conn = sqlite3.connect(self.cache_db)
        cursor = conn.cursor()

        cursor.execute("""
            INSERT OR REPLACE INTO video_tags
            (video_id, tags, summary, tagged_at)
            VALUES (?, ?, ?, ?)
        """, (
            video_id,
            json.dumps(tags),
            summary,
            datetime.now().isoformat(),
        ))

        conn.commit()
        conn.close()

    def aggregate_channel_tags(self) -> None:
        """Aggregate video tags into channel tags."""
        conn = sqlite3.connect(self.cache_db)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        # Get all videos with tags grouped by channel
        cursor.execute("""
            SELECT v.channel_id, v.channel_name, vt.tags
            FROM videos v
            JOIN video_tags vt ON v.video_id = vt.video_id
            WHERE vt.tags IS NOT NULL
            GROUP BY v.channel_id
        """)

        rows = cursor.fetchall()
        conn.close()

        # Aggregate tags by channel
        channel_tags = defaultdict(list)
        channel_names = {}

        for row in rows:
            channel_id = row["channel_id"]
            tags = json.loads(row["tags"])
            channel_names[channel_id] = row["channel_name"]
            channel_tags[channel_id].extend(tags)

        # Save aggregated tags for each channel
        for channel_id, tags in channel_tags.items():
            # Get top tags by frequency
            tag_counts = Counter(tags)
            top_tags = [tag for tag, count in tag_counts.most_common(10)]

            # Save to database
            conn = sqlite3.connect(self.cache_db)
            cursor = conn.cursor()

            cursor.execute("""
                INSERT OR REPLACE INTO channel_tags
                (channel_id, tags, tag_frequency, updated_at)
                VALUES (?, ?, ?, ?)
            """, (
                channel_id,
                json.dumps(top_tags),
                json.dumps(dict(tag_counts)),
                datetime.now().isoformat(),
            ))

            conn.commit()
            conn.close()

    def tag_videos(self, batch_size: int = 10) -> None:
        """Tag all untagged videos."""
        videos = self.get_untagged_videos()

        if not videos:
            print("No untagged videos found.")
            return

        print(f"Tagging {len(videos)} videos...")

        for i, video in enumerate(videos):
            video_id = video["video_id"]
            title = video["title"]

            print(f"  [{i + 1}/{len(videos)}] Tagging: {title[:60]}...")

            tag_result = self.generate_tags(title)
            if tag_result:
                self.save_video_tags(
                    video_id,
                    tag_result["tags"],
                    tag_result["summary"],
                )

        # Aggregate tags for all channels
        print("\nAggregating channel tags...")
        self.aggregate_channel_tags()

        print("Tagging complete!")


def main():
    """Main function."""
    try:
        cache_db = Path(__file__).parent / "channel_cache.db"
        tagger = VideoTagger(cache_db_path=str(cache_db))
        tagger.tag_videos()
    except ValueError as e:
        print(f"Error: {e}")
        print("Please add OPENAI_API_KEY to .env file")


if __name__ == "__main__":
    main()
