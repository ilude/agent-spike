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

# Add individual lesson directories to path for importing agents
sys.path.insert(0, str(lessons_dir / "lesson-001"))
sys.path.insert(0, str(lessons_dir / "lesson-002"))

# Create sub-agents once globally (following Pydantic AI best practices)
from youtube_agent.agent import create_agent as create_youtube_agent
from webpage_agent.agent import create_agent as create_webpage_agent

youtube_agent = create_youtube_agent(instrument=False)
webpage_agent = create_webpage_agent(instrument=False)


async def call_subagent(ctx: RunContext, agent_name: str, url: str) -> Dict[str, Any]:
    """
    Call a specialized sub-agent with a URL.

    Args:
        ctx: Pydantic AI run context
        agent_name: Name of sub-agent ('youtube_tagger' or 'webpage_tagger')
        url: URL to process

    Returns:
        Dictionary with tags and metadata
    """
    print(f"\n>>> CALLING SUBAGENT: {agent_name} with URL: {url}")

    if agent_name == "youtube_tagger":
        print(f">>> About to call youtube_agent.run...", flush=True)
        try:
            result = await youtube_agent.run(
                user_prompt=f"Tag this video: {url}",
                usage=ctx.usage,  # Pass usage for proper tracking
            )
            print(f">>> youtube_agent.run completed", flush=True)
            print(f">>> Result type: {type(result)}", flush=True)
            print(f">>> Result output: {result.output}", flush=True)
        except Exception as e:
            print(f">>> ERROR in youtube_agent.run: {e}", flush=True)
            raise

        response = {
            "agent": "youtube_tagger",
            "url": url,
            "tags": result.output if isinstance(result.output, list) else [result.output],
            "success": True
        }
        print(f"<<< YOUTUBE RESULT: {response}", flush=True)
        return response

    elif agent_name == "webpage_tagger":
        result = await webpage_agent.run(
            user_prompt=f"Tag this webpage: {url}",
            usage=ctx.usage,  # Pass usage for proper tracking
        )

        response = {
            "agent": "webpage_tagger",
            "url": url,
            "tags": result.output if isinstance(result.output, list) else [result.output],
            "success": True
        }
        print(f"<<< WEBPAGE RESULT: {response}")
        return response

    else:
        error_response = {
            "agent": agent_name,
            "url": url,
            "error": f"Unknown agent: {agent_name}",
            "success": False
        }
        print(f"<<< ERROR: {error_response}")
        return error_response
