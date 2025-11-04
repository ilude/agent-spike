"""YouTube tagging agent using Pydantic AI."""

import os
from pydantic_ai import Agent, RunContext
from dotenv import load_dotenv

from .prompts import TAGGING_SYSTEM_PROMPT
from .tools import get_video_info as _get_video_info
from .tools import get_transcript as _get_transcript


load_dotenv()


def create_agent(model: str | None = None) -> Agent:
    """Create and configure the YouTube tagging agent.

    Args:
        model: LLM model to use. If None, uses claude-3-5-haiku-20241022

    Returns:
        Configured Pydantic AI agent
    """
    if model is None:
        model = os.getenv("DEFAULT_MODEL", "claude-3-5-haiku-20241022")

    agent = Agent(
        model,
        system_prompt=TAGGING_SYSTEM_PROMPT,
    )

    @agent.tool
    def get_video_info(ctx: RunContext[None], url: str) -> dict:
        """Fetches YouTube video metadata including video ID.

        Args:
            url: YouTube video URL (e.g., https://youtube.com/watch?v=...)

        Returns:
            Dictionary with video metadata
        """
        return _get_video_info(url)

    @agent.tool
    def get_transcript(ctx: RunContext[None], url: str) -> str:
        """Fetches the complete transcript of a YouTube video.

        Args:
            url: YouTube video URL

        Returns:
            Full transcript text or error message
        """
        return _get_transcript(url)

    return agent


async def analyze_video(url: str, model: str | None = None) -> str:
    """Analyze a YouTube video and generate tags.

    Args:
        url: YouTube video URL
        model: Optional LLM model override

    Returns:
        String response from the agent
    """
    agent = create_agent(model)

    result = await agent.run(
        f"Analyze this YouTube video and generate tags: {url}"
    )

    # Return the text response from the agent
    return result.output if hasattr(result, 'output') else str(result)
