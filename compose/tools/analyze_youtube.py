#!/usr/bin/env python3
"""
Analyze YouTube video watching patterns from Brave browser history.

Generates statistics on YouTube video visits including:
- Average videos watched per month
- Min/max videos watched in a month
- Standard deviation
- Trends across different time periods (all time, 12mo, 6mo, 3mo)
- Top channels by visit count
"""

import json
import sqlite3
import statistics
from datetime import datetime, timedelta, timezone
from pathlib import Path
from urllib.parse import urlparse, parse_qs
from collections import defaultdict

from compose.services.youtube_cache import YouTubeCache


# Chrome/WebKit timestamp constants
CHROME_EPOCH_OFFSET = 11644473600  # Seconds between 1601-01-01 and 1970-01-01
CHROME_MICROSECONDS_PER_SECOND = 1_000_000


def chrome_timestamp_to_datetime(chrome_timestamp: int) -> datetime:
    """Convert Chrome timestamp (microseconds since 1601-01-01) to datetime."""
    unix_timestamp = (chrome_timestamp / CHROME_MICROSECONDS_PER_SECOND) - CHROME_EPOCH_OFFSET
    return datetime.fromtimestamp(unix_timestamp, tz=timezone.utc).replace(tzinfo=None)


def find_latest_brave_history() -> Path:
    """Find the latest brave_history file in the data directory."""
    data_dir = Path(__file__).parent.parent / "data" / "brave_history"

    history_files = sorted(data_dir.glob("brave_history.*.sqlite"), reverse=True)

    if not history_files:
        raise FileNotFoundError(f"No brave_history files found in {data_dir}")

    return history_files[0]


def extract_video_id(url: str) -> str | None:
    """Extract YouTube video ID from URL."""
    parsed = urlparse(url)
    if "youtube.com" not in parsed.netloc:
        return None

    params = parse_qs(parsed.query)
    video_ids = params.get("v", [])

    return video_ids[0] if video_ids else None


def get_youtube_visits(db_path: Path) -> list[tuple[datetime, str]]:
    """
    Query YouTube visits from the Brave history database.

    Returns:
        List of tuples: (visit_datetime, video_url)
    """
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # Query YouTube visits
    cursor.execute("""
        SELECT v.visit_time, u.url
        FROM visits v
        JOIN urls u ON v.url = u.id
        WHERE u.url LIKE '%youtube.com/watch%'
        ORDER BY v.visit_time ASC
    """)

    visits = []
    for chrome_timestamp, url in cursor.fetchall():
        visit_datetime = chrome_timestamp_to_datetime(chrome_timestamp)
        visits.append((visit_datetime, url))

    conn.close()
    return visits


def group_visits_by_month(visits: list[tuple[datetime, str]]) -> dict[str, int]:
    """
    Group visits by year-month and count videos per month.

    Returns:
        Dict mapping "YYYY-MM" to video count
    """
    monthly_counts = defaultdict(int)

    for visit_datetime, url in visits:
        month_key = visit_datetime.strftime("%Y-%m")
        monthly_counts[month_key] += 1

    return dict(sorted(monthly_counts.items()))


def filter_months_by_range(monthly_counts: dict[str, int], months_back: int | None) -> dict[str, int]:
    """
    Filter monthly counts to only include recent months.

    Args:
        monthly_counts: Dict mapping "YYYY-MM" to video count
        months_back: Only include last N months (None = all months)

    Returns:
        Filtered monthly counts
    """
    if months_back is None:
        return monthly_counts

    now = datetime.now()
    cutoff = now - timedelta(days=30 * months_back)

    filtered = {}
    for month_str, count in monthly_counts.items():
        month_date = datetime.strptime(month_str, "%Y-%m")
        if month_date >= cutoff:
            filtered[month_str] = count

    return filtered


def calculate_statistics(counts: list[int]) -> dict:
    """Calculate statistics from a list of counts."""
    if not counts:
        return {
            "average": 0,
            "min": 0,
            "max": 0,
            "stddev": 0,
            "total_months": 0,
        }

    return {
        "average": statistics.mean(counts),
        "min": min(counts),
        "max": max(counts),
        "stddev": statistics.stdev(counts) if len(counts) > 1 else 0,
        "total_months": len(counts),
    }


def format_stats_output(period_name: str, monthly_counts: dict[str, int], stats: dict) -> str:
    """Format statistics for console output."""
    lines = [
        f"\n{'='*60}",
        f"{period_name}",
        f"{'='*60}",
    ]

    if monthly_counts:
        first_month = min(monthly_counts.keys())
        last_month = max(monthly_counts.keys())
        lines.append(f"Date Range: {first_month} to {last_month}")
        lines.append(f"Total Months Analyzed: {stats['total_months']}")
    else:
        lines.append("No data available for this period")
        return "\n".join(lines)

    lines.extend([
        "",
        f"Average Videos/Month: {stats['average']:.1f}",
        f"Min Videos in a Month: {stats['min']}",
        f"Max Videos in a Month: {stats['max']}",
        f"Standard Deviation: {stats['stddev']:.1f}",
    ])

    return "\n".join(lines)


def get_channel_visits(visits: list[tuple[datetime, str]], cache: YouTubeCache) -> dict[str, int]:
    """
    Group visits by channel using cached YouTube data.

    Returns:
        Dict mapping channel_name to visit count
    """
    channel_counts = defaultdict(int)
    api_calls = 0
    cached_hits = 0

    print("\nFetching channel information (this may take a moment)...")
    for i, (visit_datetime, url) in enumerate(visits):
        video_id = extract_video_id(url)
        if not video_id:
            continue

        channel_info = cache.get_channel_info(video_id)
        if channel_info:
            channel_name = channel_info.get("channel_name", "Unknown")
            channel_counts[channel_name] += 1

            if channel_info.get("cached"):
                cached_hits += 1
            else:
                api_calls += 1

        # Progress indicator
        if (i + 1) % 50 == 0:
            print(f"  Processed {i + 1}/{len(visits)} visits...")

    print(f"Channel data retrieved: {api_calls} API calls, {cached_hits} cached hits")
    return dict(sorted(channel_counts.items(), key=lambda x: x[1], reverse=True))


def get_channel_tags(cache_db: Path, channel_name: str) -> list[str] | None:
    """Get tags for a channel from the database."""
    conn = sqlite3.connect(cache_db)
    cursor = conn.cursor()

    cursor.execute("""
        SELECT tags FROM channel_tags
        WHERE channel_id IN (
            SELECT DISTINCT channel_id FROM videos WHERE channel_name = ?
        )
        LIMIT 1
    """, (channel_name,))

    row = cursor.fetchone()
    conn.close()

    if row:
        try:
            return json.loads(row[0])
        except json.JSONDecodeError:
            return None

    return None


def format_top_channels_output(
    channel_counts: dict[str, int],
    cache_db: Path,
    top_n: int = 15,
) -> str:
    """Format top channels for console output with tags."""
    lines = [
        f"\n{'='*60}",
        f"Top Channels by Visit Count",
        f"{'='*60}",
    ]

    if not channel_counts:
        lines.append("No channel data available")
        return "\n".join(lines)

    total_visits = sum(channel_counts.values())
    lines.append(f"Total Unique Channels: {len(channel_counts)}")
    lines.append(f"Total Visits: {total_visits}")
    lines.append("")

    for i, (channel, count) in enumerate(list(channel_counts.items())[:top_n], 1):
        percentage = (count / total_visits) * 100
        line = f"{i:2}. {channel:40} {count:4} visits ({percentage:5.1f}%)"

        # Get and append tags if available
        tags = get_channel_tags(cache_db, channel)
        if tags:
            tags_str = ", ".join(tags[:5])  # Show top 5 tags
            line += f"\n    Tags: {tags_str}"

        lines.append(line)

    return "\n".join(lines)


def main():
    """Main analysis function."""
    print("YouTube History Analysis")
    print("Analyzing Brave browser history for YouTube video visits...")

    # Find and connect to database
    try:
        db_path = find_latest_brave_history()
        print(f"Using database: {db_path.name}")
    except FileNotFoundError as e:
        print(f"Error: {e}")
        return

    # Initialize YouTube cache
    try:
        cache_db = Path(__file__).parent.parent / "data" / "brave_history" / "channel_cache.db"
        cache = YouTubeCache(cache_db_path=str(cache_db))
    except ValueError as e:
        print(f"Error: {e}")
        print("Please add YOUTUBE_API_KEY to .env file")
        return

    # Get YouTube visits
    print("Querying YouTube visits...")
    visits = get_youtube_visits(db_path)

    if not visits:
        print("No YouTube visits found in history.")
        return

    print(f"Found {len(visits)} YouTube visits")

    # Group by month
    monthly_counts = group_visits_by_month(visits)
    counts = list(monthly_counts.values())

    # Calculate statistics for different time periods
    time_periods = [
        (None, "All Time History"),
        (12, "Last 12 Months"),
        (6, "Last 6 Months"),
        (3, "Last 3 Months"),
    ]

    for months_back, period_name in time_periods:
        filtered_monthly = filter_months_by_range(monthly_counts, months_back)
        filtered_counts = list(filtered_monthly.values())
        stats = calculate_statistics(filtered_counts)
        output = format_stats_output(period_name, filtered_monthly, stats)
        print(output)

    # Analyze channels
    channel_counts = get_channel_visits(visits, cache)
    cache_db_path = Path(__file__).parent / "channel_cache.db"
    channel_output = format_top_channels_output(channel_counts, cache_db_path)
    print(channel_output)

    # Show cache statistics
    cache_stats = cache.get_cache_stats()
    print(f"\n{'='*60}")
    print("Cache Statistics")
    print(f"{'='*60}")
    print(f"Cached Videos: {cache_stats['cached_videos']}")
    print(f"Cached Channels: {cache_stats['cached_channels']}")

    print(f"\n{'='*60}")
    print("Analysis Complete")
    print(f"{'='*60}\n")


if __name__ == "__main__":
    main()
