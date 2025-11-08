"""
Tools for orchestrator agent
"""

from pydantic_ai import RunContext
from typing import Dict, Any
import sys
from pathlib import Path

# Add lessons to path so we can import sub-agents
lessons_dir = Path(__file__).parent.parent.parent
sys.path.insert(0, str(lessons_dir))


def call_subagent(agent_name: str, url: str) -> Dict[str, Any]:
    """
    Call a specialized sub-agent with a URL.

    Args:
        agent_name: Name of sub-agent ('youtube_tagger' or 'webpage_tagger')
        url: URL to process

    Returns:
        Dictionary with tags and metadata
    """
    if agent_name == "youtube_tagger":
        from lesson_001.youtube_agent import agent as youtube_agent

        result = youtube_agent.run_sync(
            user_prompt=f"Tag this video: {url}",
            message_history=[]  # Isolated context - no history
        )

        return {
            "agent": "youtube_tagger",
            "url": url,
            "tags": result.data if isinstance(result.data, list) else [result.data],
            "success": True
        }

    elif agent_name == "webpage_tagger":
        from lesson_002.webpage_agent import agent as webpage_agent

        result = webpage_agent.run_sync(
            user_prompt=f"Tag this webpage: {url}",
            message_history=[]  # Isolated context - no history
        )

        return {
            "agent": "webpage_tagger",
            "url": url,
            "tags": result.data if isinstance(result.data, list) else [result.data],
            "success": True
        }

    else:
        return {
            "agent": agent_name,
            "url": url,
            "error": f"Unknown agent: {agent_name}",
            "success": False
        }
