"""
Fetch YouTube channel videos and export to CSV.

This script fetches video information from a YouTube channel using the YouTube Data API v3
and exports the results to a CSV file.
"""

import csv
import os
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

from tools.env_loader import load_root_env

# Load environment variables from .env file
load_root_env()


def get_channel_id(youtube: Any, channel_url: str) -> str | None:
    """
    Extract channel ID from a channel URL.
    
    Args:
        youtube: YouTube API client
        channel_url: YouTube channel URL (e.g., https://www.youtube.com/@NateBJones)
    
    Returns:
        Channel ID or None if not found
    """
    # Extract username from URL
    if "@" in channel_url:
        username = channel_url.split("@")[1].split("/")[0]
    else:
        print(f"Could not extract username from URL: {channel_url}")
        return None
    
    try:
        # Search for the channel by username
        request = youtube.search().list(
            part="snippet",
            q=username,
            type="channel",
            maxResults=1
        )
        response = request.execute()
        
        if response.get("items"):
            return response["items"][0]["snippet"]["channelId"]
        else:
            print(f"No channel found for username: {username}")
            return None
    except HttpError as e:
        print(f"An HTTP error occurred: {e}")
        return None


def get_channel_videos(
    youtube: Any,
    channel_id: str,
    cutoff_date: datetime
) -> list[dict[str, Any]]:
    """
    Fetch all videos from a channel since the cutoff date.
    
    Args:
        youtube: YouTube API client
        channel_id: YouTube channel ID
        cutoff_date: Only fetch videos uploaded after this date
    
    Returns:
        List of video dictionaries with title, url, date, views, duration, description
    """
    videos = []
    next_page_token = None
    
    try:
        # First, get the uploads playlist ID
        request = youtube.channels().list(
            part="contentDetails",
            id=channel_id
        )
        response = request.execute()
        
        if not response.get("items"):
            print(f"No channel found with ID: {channel_id}")
            return videos
        
        uploads_playlist_id = response["items"][0]["contentDetails"]["relatedPlaylists"]["uploads"]
        
        # Fetch videos from the uploads playlist
        while True:
            playlist_request = youtube.playlistItems().list(
                part="snippet,contentDetails",
                playlistId=uploads_playlist_id,
                maxResults=50,
                pageToken=next_page_token
            )
            playlist_response = playlist_request.execute()
            
            video_ids = []
            video_dates = {}
            
            for item in playlist_response.get("items", []):
                video_id = item["contentDetails"]["videoId"]
                published_at = datetime.strptime(
                    item["snippet"]["publishedAt"],
                    "%Y-%m-%dT%H:%M:%SZ"
                )
                
                # Only include videos from the last 12 months
                if published_at >= cutoff_date:
                    video_ids.append(video_id)
                    video_dates[video_id] = published_at
                else:
                    # Since videos are ordered by date, we can stop here
                    break
            
            if not video_ids:
                break
            
            # Get detailed video information
            videos_request = youtube.videos().list(
                part="snippet,statistics,contentDetails",
                id=",".join(video_ids)
            )
            videos_response = videos_request.execute()
            
            for video in videos_response.get("items", []):
                video_id = video["id"]
                snippet = video["snippet"]
                statistics = video.get("statistics", {})
                content_details = video["contentDetails"]
                
                # Parse ISO 8601 duration (e.g., PT15M33S)
                duration = content_details["duration"]
                
                videos.append({
                    "title": snippet["title"],
                    "url": f"https://www.youtube.com/watch?v={video_id}",
                    "upload_date": video_dates[video_id].strftime("%Y-%m-%d"),
                    "view_count": statistics.get("viewCount", "0"),
                    "duration": duration,
                    "description": snippet.get("description", "")[:200]  # First 200 chars
                })
            
            next_page_token = playlist_response.get("nextPageToken")
            
            # If no more pages or we've gone past the cutoff date
            if not next_page_token or not video_ids:
                break
        
        # Sort by upload date (newest first)
        videos.sort(key=lambda x: x["upload_date"], reverse=True)
        
    except HttpError as e:
        print(f"An HTTP error occurred: {e}")
    
    return videos


def parse_duration(duration: str) -> str:
    """
    Convert ISO 8601 duration to human-readable format.
    
    Args:
        duration: ISO 8601 duration string (e.g., PT15M33S)
    
    Returns:
        Human-readable duration (e.g., 15:33)
    """
    import re
    
    match = re.match(r'PT(?:(\d+)H)?(?:(\d+)M)?(?:(\d+)S)?', duration)
    if not match:
        return duration
    
    hours, minutes, seconds = match.groups()
    hours = int(hours) if hours else 0
    minutes = int(minutes) if minutes else 0
    seconds = int(seconds) if seconds else 0
    
    if hours > 0:
        return f"{hours}:{minutes:02d}:{seconds:02d}"
    else:
        return f"{minutes}:{seconds:02d}"


def save_to_csv(videos: list[dict[str, Any]], filename: str) -> None:
    """
    Save videos to a CSV file.
    
    Args:
        videos: List of video dictionaries
        filename: Output CSV filename
    """
    if not videos:
        print("No videos to save.")
        return
    
    with open(filename, "w", newline="", encoding="utf-8") as csvfile:
        fieldnames = ["title", "url", "upload_date", "view_count", "duration", "description"]
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        
        writer.writeheader()
        for video in videos:
            # Parse duration to human-readable format
            video["duration"] = parse_duration(video["duration"])
            writer.writerow(video)
    
    print(f"Saved {len(videos)} videos to {filename}")


def main() -> None:
    """Main function to fetch and save YouTube videos."""
    import argparse

    # Parse command line arguments
    parser = argparse.ArgumentParser(
        description="Fetch YouTube channel videos and export to CSV queue"
    )
    parser.add_argument(
        "channel_url",
        nargs="?",
        default="https://www.youtube.com/@NateBJones/videos",
        help="YouTube channel URL (default: NateBJones)"
    )
    parser.add_argument(
        "-o", "--output",
        help="Output CSV filename (auto-generated from channel name if not provided)"
    )
    parser.add_argument(
        "-m", "--months",
        type=int,
        default=12,
        help="Number of months to look back (default: 12)"
    )

    args = parser.parse_args()

    # Load API key from environment
    api_key = os.getenv("YOUTUBE_API_KEY")
    if not api_key:
        print("Error: YOUTUBE_API_KEY environment variable not set.")
        print("Please create a .env file with your YouTube Data API v3 key:")
        print("  YOUTUBE_API_KEY=your_api_key_here")
        return

    # Determine output file
    if args.output:
        output_filename = args.output
    else:
        # Extract channel name from URL
        # @NateBJones -> nate_b_jones_videos.csv
        if "@" in args.channel_url:
            username = args.channel_url.split("@")[1].split("/")[0]
            output_filename = f"{username.lower().replace('-', '_')}_videos.csv"
        else:
            print("Error: Could not extract channel name from URL")
            print("Please use -o to specify output filename")
            return

    # Output to queue directory
    queue_dir = Path(__file__).parent.parent.parent / "projects" / "data" / "queues" / "pending"
    queue_dir.mkdir(parents=True, exist_ok=True)
    output_file = queue_dir / output_filename

    # Configuration
    channel_url = args.channel_url
    months_back = args.months

    # Calculate cutoff date
    cutoff_date = datetime.now() - timedelta(days=months_back * 30)

    print(f"Fetching videos from: {channel_url}")
    print(f"Cutoff date: {cutoff_date.strftime('%Y-%m-%d')}")

    # Build YouTube API client
    youtube = build("youtube", "v3", developerKey=api_key)

    # Get channel ID
    print("Looking up channel ID...")
    channel_id = get_channel_id(youtube, channel_url)
    if not channel_id:
        print("Could not find channel. Please check the URL.")
        return

    print(f"Found channel ID: {channel_id}")

    # Fetch videos
    print("Fetching videos...")
    videos = get_channel_videos(youtube, channel_id, cutoff_date)

    if not videos:
        print("No videos found in the specified time range.")
        return

    print(f"Found {len(videos)} videos from the last {months_back} months.")

    # Save to CSV
    save_to_csv(videos, str(output_file))
    print(f"\nDone! CSV queued at: {output_file}")
    print(f"Run the ingestion REPL to process: make ingest")


if __name__ == "__main__":
    main()
