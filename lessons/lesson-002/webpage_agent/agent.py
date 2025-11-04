"""Webpage tagging agent using Pydantic AI."""

import os
from pydantic_ai import Agent, RunContext
from dotenv import load_dotenv

from .prompts import TAGGING_SYSTEM_PROMPT
from .tools import fetch_webpage as _fetch_webpage
from .tools import get_page_info as _get_page_info


load_dotenv()


def create_agent(model: str | None = None, instrument: bool = True) -> Agent:
    """Create and configure the webpage tagging agent.

    Args:
        model: LLM model to use. If None, uses claude-3-5-haiku-20241022
        instrument: Enable Langfuse/OpenTelemetry instrumentation (default: True)

    Returns:
        Configured Pydantic AI agent
    """
    if model is None:
        model = os.getenv("DEFAULT_MODEL", "claude-3-5-haiku-20241022")

    agent = Agent(
        model,
        system_prompt=TAGGING_SYSTEM_PROMPT,
        instrument=instrument,  # Enable observability
    )

    @agent.tool
    def fetch_webpage(ctx: RunContext[None], url: str) -> str:
        """Fetches webpage content and converts to clean Markdown.

        Args:
            url: Webpage URL (must start with http:// or https://)

        Returns:
            Clean Markdown content with ads/navigation removed, or error message
        """
        return _fetch_webpage(url)

    @agent.tool
    def get_page_info(ctx: RunContext[None], url: str) -> dict:
        """Gets basic information about a webpage URL.

        Args:
            url: Webpage URL

        Returns:
            Dictionary with URL validation information
        """
        return _get_page_info(url)

    return agent


async def analyze_webpage(url: str, model: str | None = None) -> str:
    """Analyze a webpage and generate tags.

    Args:
        url: Webpage URL
        model: Optional LLM model override

    Returns:
        String response from the agent with tags and summary
    """
    agent = create_agent(model)

    result = await agent.run(
        f"Analyze this webpage and generate tags: {url}"
    )

    # Return the text response from the agent
    return result.output if hasattr(result, 'output') else str(result)
