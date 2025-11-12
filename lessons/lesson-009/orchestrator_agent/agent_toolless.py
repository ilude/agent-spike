"""
Orchestrator Agent - Option 2: Tool-less Sub-Agents

Architecture:
- Coordinator has ALL tools (data fetching)
- Sub-agents are pure reasoning modules (no tools)
- No nested agent-with-tools calls = no deadlocks
"""

from pydantic_ai import Agent, RunContext
from typing import Dict, Any
import sys
import os
from pathlib import Path

# Bootstrap to import lesson_base
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from lessons.lesson_base import setup_lesson_environment
setup_lesson_environment(lessons=["lesson-001", "lesson-002"])

# Import tool functions (NOT agents)
from youtube_agent.tools import get_video_info, get_transcript
from webpage_agent.tools import fetch_webpage
from youtube_agent.prompts import TAGGING_SYSTEM_PROMPT as YOUTUBE_PROMPT
from webpage_agent.prompts import TAGGING_SYSTEM_PROMPT as WEBPAGE_PROMPT

# Tool-less sub-agents (pure reasoning, no tools)
youtube_reasoner = Agent(
    model=os.getenv("DEFAULT_MODEL", "openai:gpt-5-nano"),
    system_prompt=YOUTUBE_PROMPT,
)

webpage_reasoner = Agent(
    model=os.getenv("DEFAULT_MODEL", "openai:gpt-5-nano"),
    system_prompt=WEBPAGE_PROMPT,
)

# Coordinator system prompt
COORDINATOR_PROMPT = """You are an orchestrator that coordinates data fetching and specialized reasoning.

Available tools:
- fetch_youtube_data(url): Fetch YouTube video info and transcript
- fetch_webpage_data(url): Fetch webpage content
- reason_youtube(data): Get YouTube tags from transcript data
- reason_webpage(data): Get webpage tags from content data

Workflow:
1. Identify URL types
2. Fetch data with appropriate tool
3. Reason about data with appropriate tool
4. Organize results

Be efficient: fetch and reason in logical order."""

# Create coordinator with ALL tools
coordinator = Agent(
    model="openai:gpt-5-mini",
    system_prompt=COORDINATOR_PROMPT,
)


@coordinator.tool
async def fetch_youtube_data(ctx: RunContext, url: str) -> Dict[str, Any]:
    """Fetch YouTube video info and transcript"""
    print(f">>> FETCHING YouTube data: {url}", flush=True)

    video_info = get_video_info(url)
    transcript = get_transcript(url)[:5000]

    return {
        "url": url,
        "title": video_info.get("title", "Unknown"),
        "description": video_info.get("description", "")[:500],
        "transcript": transcript,
    }


@coordinator.tool
async def fetch_webpage_data(ctx: RunContext, url: str) -> Dict[str, Any]:
    """Fetch webpage content"""
    print(f">>> FETCHING webpage data: {url}", flush=True)

    content = fetch_webpage(url)[:5000]

    return {
        "url": url,
        "content": content,
    }


@coordinator.tool
async def reason_youtube(ctx: RunContext, data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Use YouTube reasoner to generate tags from video data.

    This is a tool-less agent - just LLM reasoning, no nested tools.
    """
    print(f">>> REASONING about YouTube video: {data['title']}", flush=True)

    # Call tool-less sub-agent (no deadlock risk)
    result = await youtube_reasoner.run(
        f"""Analyze this YouTube video and generate 3-5 relevant tags:

Title: {data['title']}
Description: {data['description']}

Transcript (first 5000 chars):
{data['transcript']}

Return just the tags as a simple list.""",
        usage=ctx.usage,  # Track usage
    )

    # Parse output
    output_text = str(result.output)
    import re
    tags = []

    # Try different formats
    if "tags:" in output_text.lower():
        tags_section = output_text.split("tags:", 1)[1] if "tags:" in output_text.lower() else output_text.split("Tags:", 1)[1]
        tag_lines = re.findall(r'[-*•]\s*(.+)', tags_section)
        if tag_lines:
            tags = [tag.strip() for tag in tag_lines[:5]]
        else:
            tags = [tag.strip() for tag in tags_section.split(',')[:5] if tag.strip()]
    elif any(marker in output_text for marker in ['1.', '2.', '3.']):
        tags = re.findall(r'\d+\.\s*(.+)', output_text)[:5]
    else:
        tags = [line.strip() for line in output_text.split('\n') if line.strip()][:5]

    return {
        "url": data["url"],
        "title": data["title"],
        "tags": tags,
        "agent": "youtube_reasoner",
    }


@coordinator.tool
async def reason_webpage(ctx: RunContext, data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Use webpage reasoner to generate tags from webpage data.

    This is a tool-less agent - just LLM reasoning, no nested tools.
    """
    print(f">>> REASONING about webpage: {data['url']}", flush=True)

    # Call tool-less sub-agent (no deadlock risk)
    result = await webpage_reasoner.run(
        f"""Analyze this webpage and generate 3-5 relevant tags:

URL: {data['url']}

Content (first 5000 chars):
{data['content']}

Return just the tags as a simple list.""",
        usage=ctx.usage,  # Track usage
    )

    # Parse output
    output_text = str(result.output)
    import re
    tags = []

    if "tags:" in output_text.lower():
        tags_section = output_text.split("tags:", 1)[1] if "tags:" in output_text.lower() else output_text.split("Tags:", 1)[1]
        tag_lines = re.findall(r'[-*•]\s*(.+)', tags_section)
        if tag_lines:
            tags = [tag.strip() for tag in tag_lines[:5]]
        else:
            tags = [tag.strip() for tag in tags_section.split(',')[:5] if tag.strip()]
    elif any(marker in output_text for marker in ['1.', '2.', '3.']):
        tags = re.findall(r'\d+\.\s*(.+)', output_text)[:5]
    else:
        tags = [line.strip() for line in output_text.split('\n') if line.strip()][:5]

    return {
        "url": data["url"],
        "tags": tags,
        "agent": "webpage_reasoner",
    }
