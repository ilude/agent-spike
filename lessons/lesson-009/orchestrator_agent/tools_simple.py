"""
Simplified tools for orchestrator - direct API calls instead of nested agents
"""

from pydantic_ai import RunContext, Agent
from typing import Dict, Any
import sys
import os
from pathlib import Path

# Add project root for imports
lessons_dir = Path(__file__).parent.parent.parent
sys.path.insert(0, str(lessons_dir))
sys.path.insert(0, str(lessons_dir / "lesson-001"))
sys.path.insert(0, str(lessons_dir / "lesson-002"))

from tools.dotenv import load_root_env
load_root_env()


async def call_subagent_simple(ctx: RunContext, agent_name: str, url: str) -> Dict[str, Any]:
    """
    Simplified subagent call - direct LLM call instead of nested agent

    This avoids the nested agent/tool complexity that causes hangs.
    """
    print(f"\n>>> CALLING SIMPLE SUBAGENT: {agent_name} with URL: {url}", flush=True)

    model = os.getenv("DEFAULT_MODEL", "openai:gpt-5-nano")

    if agent_name == "youtube_tagger":
        # Import YouTube tools directly
        from youtube_agent.tools import get_video_info, get_transcript
        from youtube_agent.prompts import TAGGING_SYSTEM_PROMPT

        # Get video info and transcript
        video_info = get_video_info(url)
        transcript = get_transcript(url)[:5000]  # Limit transcript length

        # Create a simple agent just for this request (no tools, no structured output)
        simple_agent = Agent(
            model=model,
            system_prompt=TAGGING_SYSTEM_PROMPT,
            instrument=False
        )

        # Make the LLM call
        result = await simple_agent.run(
            f"""Analyze this YouTube video and generate tags:

URL: {url}
Title: {video_info.get('title', 'Unknown')}
Description: {video_info.get('description', '')}[:500]

Transcript (first 5000 chars):
{transcript}

Generate 3-5 relevant tags for this video. Return them as a simple list.""",
            usage=ctx.usage  # Pass usage for tracking
        )

        # Parse tags from the text output
        output_text = str(result.output)
        # Simple extraction - look for list items or comma-separated values
        import re
        tags = []
        # Try to extract tags from various formats
        if "tags:" in output_text.lower():
            tags_section = output_text.split("tags:", 1)[1] if "tags:" in output_text.lower() else output_text.split("Tags:", 1)[1]
            # Extract bullet points or numbered lists
            tag_lines = re.findall(r'[-*•]\s*(.+)', tags_section)
            if tag_lines:
                tags = [tag.strip() for tag in tag_lines[:5]]
            else:
                # Try comma-separated
                tags = [tag.strip() for tag in tags_section.split(',')[:5] if tag.strip()]
        elif any(marker in output_text for marker in ['1.', '2.', '3.']):
            # Numbered list
            tags = re.findall(r'\d+\.\s*(.+)', output_text)[:5]
        else:
            # Fall back to first 5 lines
            tags = [line.strip() for line in output_text.split('\n') if line.strip()][:5]

        response = {
            "agent": "youtube_tagger",
            "url": url,
            "tags": tags,
            "title": video_info.get('title', 'Unknown'),
            "success": True
        }
        print(f"<<< YOUTUBE RESULT: {response}", flush=True)
        return response

    elif agent_name == "webpage_tagger":
        # Import webpage tools directly
        from webpage_agent.tools import fetch_webpage
        from webpage_agent.prompts import TAGGING_SYSTEM_PROMPT

        # Get webpage content
        content = fetch_webpage(url)[:5000]  # Limit content length

        # Create a simple agent just for this request (no tools, no structured output)
        simple_agent = Agent(
            model=model,
            system_prompt=TAGGING_SYSTEM_PROMPT,
            instrument=False
        )

        # Make the LLM call
        result = await simple_agent.run(
            f"""Analyze this webpage and generate tags:

URL: {url}

Content (first 5000 chars):
{content}

Generate 3-5 relevant tags for this webpage. Return them as a simple list.""",
            usage=ctx.usage  # Pass usage for tracking
        )

        # Parse tags from the text output (same logic as youtube_tagger)
        output_text = str(result.output)
        import re
        tags = []
        # Try to extract tags from various formats
        if "tags:" in output_text.lower():
            tags_section = output_text.split("tags:", 1)[1] if "tags:" in output_text.lower() else output_text.split("Tags:", 1)[1]
            # Extract bullet points or numbered lists
            tag_lines = re.findall(r'[-*•]\s*(.+)', tags_section)
            if tag_lines:
                tags = [tag.strip() for tag in tag_lines[:5]]
            else:
                # Try comma-separated
                tags = [tag.strip() for tag in tags_section.split(',')[:5] if tag.strip()]
        elif any(marker in output_text for marker in ['1.', '2.', '3.']):
            # Numbered list
            tags = re.findall(r'\d+\.\s*(.+)', output_text)[:5]
        else:
            # Fall back to first 5 lines
            tags = [line.strip() for line in output_text.split('\n') if line.strip()][:5]

        response = {
            "agent": "webpage_tagger",
            "url": url,
            "tags": tags,
            "success": True
        }
        print(f"<<< WEBPAGE RESULT: {response}", flush=True)
        return response

    else:
        error_response = {
            "agent": agent_name,
            "url": url,
            "error": f"Unknown agent: {agent_name}",
            "success": False
        }
        print(f"<<< ERROR: {error_response}", flush=True)
        return error_response