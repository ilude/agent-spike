# YouTube Video Fetcher

Fetches video information from a YouTube channel using the YouTube Data API v3.

## Setup

1. Get a YouTube Data API v3 key from Google Cloud Console
2. Copy `.env.example` to `.env` and add your API key
3. Install dependencies: `uv pip install google-api-python-client python-dotenv`
4. Run: `uv run python fetch_youtube_videos.py`

## Output

Creates `nate_jones_videos.csv` with:
- Title
- URL
- Upload date
- View count
- Duration
- Description (first 200 characters)
