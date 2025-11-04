"""YouTube API tools for fetching video data."""

import re
from typing import Any
from youtube_transcript_api import YouTubeTranscriptApi
from youtube_transcript_api._errors import TranscriptsDisabled, NoTranscriptFound


def extract_video_id(url: str) -> str:
    """Extract video ID from YouTube URL.

    Supports formats:
    - https://youtube.com/watch?v=VIDEO_ID
    - https://youtu.be/VIDEO_ID
    - https://www.youtube.com/watch?v=VIDEO_ID&other=params
    """
    patterns = [
        r'(?:v=|\/)([0-9A-Za-z_-]{11}).*',
        r'youtu\.be\/([0-9A-Za-z_-]{11})',
    ]

    for pattern in patterns:
        match = re.search(pattern, url)
        if match:
            return match.group(1)

    raise ValueError(f"Could not extract video ID from URL: {url}")


def get_video_info(url: str) -> dict[str, Any]:
    """Fetch YouTube video metadata.

    Note: youtube-transcript-api doesn't provide metadata directly.
    We extract what we can from the API and video ID.
    For a production app, you'd use the YouTube Data API v3.

    Args:
        url: YouTube video URL

    Returns:
        Dictionary with video_id and url
    """
    try:
        video_id = extract_video_id(url)
        return {
            "video_id": video_id,
            "url": url,
            "note": "Full metadata requires YouTube Data API - using transcript API only"
        }
    except Exception as e:
        return {"error": str(e)}


def get_transcript(url: str) -> str:
    """Fetch YouTube video transcript.

    Args:
        url: YouTube video URL

    Returns:
        Full transcript text as a single string
    """
    try:
        video_id = extract_video_id(url)

        # Create API instance and fetch transcript
        api = YouTubeTranscriptApi()
        fetched = api.fetch(video_id)

        # Combine all transcript snippets into single text
        full_text = " ".join(snippet.text for snippet in fetched.snippets)
        return full_text

    except TranscriptsDisabled:
        return "ERROR: Transcripts are disabled for this video"
    except NoTranscriptFound:
        return "ERROR: No transcript found for this video"
    except Exception as e:
        return f"ERROR: {str(e)}"
