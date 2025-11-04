"""Coordinator agent that routes URLs to specialized agents."""

import os
import sys
from pathlib import Path
from typing import Dict, Any

# Add parent directory to path to import sibling lesson modules
lesson_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(lesson_root / "lesson-001"))
sys.path.insert(0, str(lesson_root / "lesson-002"))

from youtube_agent.agent import analyze_video
from webpage_agent.agent import analyze_webpage
from .router import URLRouter, URLType


class CoordinatorResult:
    """Result from the coordinator agent."""

    def __init__(
        self,
        url: str,
        url_type: URLType,
        handler: str,
        result: str,
        error: str | None = None,
    ):
        self.url = url
        self.url_type = url_type
        self.handler = handler
        self.result = result
        self.error = error

    def __str__(self) -> str:
        """String representation of the result."""
        if self.error:
            return f"Error: {self.error}"

        output = []
        output.append(f"URL: {self.url}")
        output.append(f"Type: {self.url_type.value}")
        output.append(f"Handler: {self.handler}")
        output.append(f"\n{self.result}")
        return "\n".join(output)

    def to_dict(self) -> Dict[str, Any]:
        """Convert result to dictionary."""
        return {
            "url": self.url,
            "url_type": self.url_type.value,
            "handler": self.handler,
            "result": self.result,
            "error": self.error,
        }


async def analyze_url(url: str, model: str | None = None) -> CoordinatorResult:
    """
    Analyze any URL by routing to the appropriate specialized agent.

    Args:
        url: The URL to analyze (YouTube video or webpage)
        model: Optional LLM model override

    Returns:
        CoordinatorResult with analysis and metadata
    """
    # Classify the URL
    url_type = URLRouter.classify_url(url)

    # Handle invalid URLs
    if url_type == URLType.INVALID:
        return CoordinatorResult(
            url=url,
            url_type=url_type,
            handler="None",
            result="",
            error=f"Invalid URL: {url}",
        )

    # Route to appropriate handler
    handler = URLRouter.get_handler_name(url_type)

    try:
        if url_type == URLType.YOUTUBE:
            result = await analyze_video(url, model)
        elif url_type == URLType.WEBPAGE:
            result = await analyze_webpage(url, model)
        else:
            return CoordinatorResult(
                url=url,
                url_type=url_type,
                handler=handler,
                result="",
                error=f"No handler available for URL type: {url_type.value}",
            )

        return CoordinatorResult(
            url=url, url_type=url_type, handler=handler, result=result
        )

    except Exception as e:
        return CoordinatorResult(
            url=url,
            url_type=url_type,
            handler=handler,
            result="",
            error=f"Error processing URL: {str(e)}",
        )


async def analyze_urls_batch(
    urls: list[str], model: str | None = None
) -> list[CoordinatorResult]:
    """
    Analyze multiple URLs in batch.

    Args:
        urls: List of URLs to analyze
        model: Optional LLM model override

    Returns:
        List of CoordinatorResult objects
    """
    results = []
    for url in urls:
        result = await analyze_url(url, model)
        results.append(result)
    return results
