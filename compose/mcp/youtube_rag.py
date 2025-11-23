#!/usr/bin/env python
"""MCP server for YouTube RAG access.

Provides Claude Code with access to search and retrieve YouTube video
transcripts and metadata from the local archive and Qdrant cache.

Usage:
    uv run python -m compose.mcp.youtube_rag

Tools provided:
    - search_videos: Semantic search through video transcripts
    - get_video: Get full video details by ID
    - list_channels: List all channels in the archive
    - get_video_links: Extract external links from video description
"""

import re
import sys
from pathlib import Path
from typing import Optional

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import Tool, TextContent

from compose.services.cache import create_qdrant_cache
from compose.services.archive import create_local_archive_reader


# Initialize server
server = Server("youtube-rag")

# Default configuration (uses Docker container URLs)
QDRANT_URL = "http://localhost:6335"
INFINITY_URL = "http://localhost:7997"
COLLECTION_NAME = "content"


def get_cache():
    """Create cache connection."""
    return create_qdrant_cache(
        collection_name=COLLECTION_NAME,
        qdrant_url=QDRANT_URL,
        infinity_url=INFINITY_URL,
    )


def get_archive():
    """Create archive reader."""
    return create_local_archive_reader()


def extract_links(text: str) -> list[dict]:
    """Extract URLs from text with context.

    Returns list of dicts with 'url' and 'context' (surrounding text).
    """
    if not text:
        return []

    # URL regex
    url_pattern = r'https?://[^\s<>"{}|\\^`\[\]]+'

    links = []
    for match in re.finditer(url_pattern, text):
        url = match.group()
        # Get context (text around URL)
        start = max(0, match.start() - 50)
        end = min(len(text), match.end() + 50)
        context = text[start:end].strip()

        # Categorize link
        link_type = "other"
        if "github.com" in url:
            link_type = "github"
        elif "arxiv.org" in url:
            link_type = "arxiv"
        elif "youtube.com" in url or "youtu.be" in url:
            link_type = "youtube"
        elif "twitter.com" in url or "x.com" in url:
            link_type = "twitter"

        links.append({
            "url": url,
            "type": link_type,
            "context": context
        })

    return links


@server.list_tools()
async def list_tools():
    """List available tools."""
    return [
        Tool(
            name="search_videos",
            description="Semantic search through YouTube video transcripts. Returns matching videos with relevance scores.",
            inputSchema={
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "Search query (natural language)"
                    },
                    "limit": {
                        "type": "integer",
                        "description": "Maximum results to return (default: 10)",
                        "default": 10
                    },
                    "channel": {
                        "type": "string",
                        "description": "Optional: Filter by channel name"
                    }
                },
                "required": ["query"]
            }
        ),
        Tool(
            name="get_video",
            description="Get full details for a specific video including transcript, metadata, and description.",
            inputSchema={
                "type": "object",
                "properties": {
                    "video_id": {
                        "type": "string",
                        "description": "YouTube video ID (e.g., 'dQw4w9WgXcQ')"
                    }
                },
                "required": ["video_id"]
            }
        ),
        Tool(
            name="get_video_links",
            description="Extract external links (GitHub repos, papers, etc.) from a video's description.",
            inputSchema={
                "type": "object",
                "properties": {
                    "video_id": {
                        "type": "string",
                        "description": "YouTube video ID"
                    }
                },
                "required": ["video_id"]
            }
        ),
        Tool(
            name="list_channels",
            description="List all YouTube channels in the archive with video counts.",
            inputSchema={
                "type": "object",
                "properties": {}
            }
        ),
        Tool(
            name="list_videos_by_channel",
            description="List all videos from a specific channel.",
            inputSchema={
                "type": "object",
                "properties": {
                    "channel_name": {
                        "type": "string",
                        "description": "Channel name to filter by"
                    },
                    "limit": {
                        "type": "integer",
                        "description": "Maximum results (default: 50)",
                        "default": 50
                    }
                },
                "required": ["channel_name"]
            }
        ),
        Tool(
            name="get_archive_stats",
            description="Get statistics about the video archive (total videos, channels, etc.).",
            inputSchema={
                "type": "object",
                "properties": {}
            }
        ),
    ]


@server.call_tool()
async def call_tool(name: str, arguments: dict):
    """Handle tool calls."""

    if name == "search_videos":
        query = arguments.get("query", "")
        limit = arguments.get("limit", 10)
        channel = arguments.get("channel")

        cache = get_cache()
        try:
            filters = {"type": "youtube_video"}
            if channel:
                filters["youtube_channel"] = channel

            results = cache.search(query, limit=limit, filters=filters)

            output = []
            for r in results:
                video_id = r.get("video_id", "unknown")
                metadata = r.get("_metadata", {})
                output.append({
                    "video_id": video_id,
                    "title": metadata.get("youtube_title", "Unknown"),
                    "channel": metadata.get("youtube_channel", "Unknown"),
                    "score": round(r.get("_score", 0), 3),
                    "transcript_preview": r.get("transcript", "")[:500] + "...",
                    "url": f"https://youtube.com/watch?v={video_id}"
                })

            return [TextContent(
                type="text",
                text=f"Found {len(output)} videos matching '{query}':\n\n" +
                     "\n\n".join([
                         f"**{i+1}. {v['title']}**\n"
                         f"   Channel: {v['channel']}\n"
                         f"   Score: {v['score']}\n"
                         f"   URL: {v['url']}\n"
                         f"   Preview: {v['transcript_preview']}"
                         for i, v in enumerate(output)
                     ])
            )]
        finally:
            cache.close()

    elif name == "get_video":
        video_id = arguments.get("video_id", "")

        # Try archive first (has full metadata)
        archive = get_archive()
        video = archive.get(video_id)

        if video:
            metadata = video.youtube_metadata or {}
            description = metadata.get("description", "")

            return [TextContent(
                type="text",
                text=f"**Video: {metadata.get('title', video_id)}**\n\n"
                     f"**Channel:** {metadata.get('channel_title', 'Unknown')}\n"
                     f"**Published:** {metadata.get('published_at', 'Unknown')}\n"
                     f"**Duration:** {metadata.get('duration', 'Unknown')}\n"
                     f"**Views:** {metadata.get('view_count', 'Unknown')}\n"
                     f"**URL:** https://youtube.com/watch?v={video_id}\n\n"
                     f"**Description:**\n{description}\n\n"
                     f"**Transcript ({len(video.transcript)} chars):**\n{video.transcript}"
            )]

        # Fallback to cache
        cache = get_cache()
        try:
            cache_key = f"youtube:video:{video_id}"
            data = cache.get(cache_key)

            if data:
                return [TextContent(
                    type="text",
                    text=f"**Video: {video_id}**\n\n"
                         f"**Transcript ({data.get('transcript_length', 0)} chars):**\n"
                         f"{data.get('transcript', 'No transcript')}"
                )]

            return [TextContent(type="text", text=f"Video {video_id} not found in archive or cache.")]
        finally:
            cache.close()

    elif name == "get_video_links":
        video_id = arguments.get("video_id", "")

        archive = get_archive()
        video = archive.get(video_id)

        if not video:
            return [TextContent(type="text", text=f"Video {video_id} not found.")]

        metadata = video.youtube_metadata or {}
        description = metadata.get("description", "")

        if not description:
            return [TextContent(type="text", text=f"No description available for video {video_id}.")]

        links = extract_links(description)

        if not links:
            return [TextContent(type="text", text=f"No external links found in video description.")]

        # Group by type
        github_links = [l for l in links if l["type"] == "github"]
        arxiv_links = [l for l in links if l["type"] == "arxiv"]
        other_links = [l for l in links if l["type"] not in ("github", "arxiv", "youtube")]

        output = f"**Links from: {metadata.get('title', video_id)}**\n\n"

        if github_links:
            output += "**GitHub Repositories:**\n"
            for l in github_links:
                output += f"  - {l['url']}\n    Context: ...{l['context']}...\n"
            output += "\n"

        if arxiv_links:
            output += "**Papers (arXiv):**\n"
            for l in arxiv_links:
                output += f"  - {l['url']}\n"
            output += "\n"

        if other_links:
            output += "**Other Links:**\n"
            for l in other_links:
                output += f"  - {l['url']}\n"

        return [TextContent(type="text", text=output)]

    elif name == "list_channels":
        archive = get_archive()
        channels = {}

        for video in archive.iter_youtube_videos():
            metadata = video.youtube_metadata or {}
            channel = metadata.get("channel_title", "Unknown")
            channels[channel] = channels.get(channel, 0) + 1

        # Sort by count
        sorted_channels = sorted(channels.items(), key=lambda x: x[1], reverse=True)

        output = f"**Channels in Archive ({len(sorted_channels)} total):**\n\n"
        for channel, count in sorted_channels:
            output += f"  - {channel}: {count} videos\n"

        return [TextContent(type="text", text=output)]

    elif name == "list_videos_by_channel":
        channel_name = arguments.get("channel_name", "")
        limit = arguments.get("limit", 50)

        cache = get_cache()
        try:
            results = cache.filter(
                {"youtube_channel": channel_name, "type": "youtube_video"},
                limit=limit
            )

            output = f"**Videos from {channel_name} ({len(results)} found):**\n\n"
            for r in results:
                video_id = r.get("video_id", "unknown")
                metadata = r.get("_metadata", {})
                output += f"  - {metadata.get('youtube_title', video_id)}\n"
                output += f"    ID: {video_id} | URL: https://youtube.com/watch?v={video_id}\n"

            return [TextContent(type="text", text=output)]
        finally:
            cache.close()

    elif name == "get_archive_stats":
        archive = get_archive()

        total = archive.count()
        month_counts = archive.get_month_counts()

        # Get channel counts from iteration
        channels = {}
        total_transcript_chars = 0
        videos_with_metadata = 0

        for video in archive.iter_youtube_videos():
            metadata = video.youtube_metadata or {}
            channel = metadata.get("channel_title", "Unknown")
            channels[channel] = channels.get(channel, 0) + 1
            total_transcript_chars += len(video.transcript)
            if metadata.get("title"):
                videos_with_metadata += 1

        output = f"**Archive Statistics:**\n\n"
        output += f"  - Total videos: {total}\n"
        output += f"  - Videos with metadata: {videos_with_metadata}\n"
        output += f"  - Unique channels: {len(channels)}\n"
        output += f"  - Total transcript chars: {total_transcript_chars:,}\n\n"
        output += f"**Videos by Month:**\n"
        for month, count in sorted(month_counts.items(), reverse=True):
            output += f"  - {month}: {count}\n"

        return [TextContent(type="text", text=output)]

    return [TextContent(type="text", text=f"Unknown tool: {name}")]


async def main():
    """Run the MCP server."""
    async with stdio_server() as (read_stream, write_stream):
        await server.run(read_stream, write_stream, server.create_initialization_options())


if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
