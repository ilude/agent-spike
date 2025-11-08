"""
Minimal Orchestrator Agent

Coordinates calls to specialized sub-agents (youtube_tagger, webpage_tagger).
"""

from pydantic_ai import Agent
from .tools import call_subagent

# System prompt for orchestrator
SYSTEM_PROMPT = """You are an orchestrator that coordinates specialized sub-agents.

Available sub-agents:
- youtube_tagger: Tags YouTube videos (use for youtube.com URLs)
- webpage_tagger: Tags web articles (use for other URLs)

When given URLs to process:
1. Identify which sub-agent to use for each URL
2. Call call_subagent(agent_name, url) for each URL
3. Collect all results
4. Summarize the tags found

Be efficient: call sub-agents in parallel when possible (make multiple tool calls).
Return organized results showing tags for each URL.
"""

# Create orchestrator agent
orchestrator = Agent(
    model="openai:gpt-5-nano",  # Using nano for cost-effective testing
    system_prompt=SYSTEM_PROMPT,
)

# Register tools
orchestrator.tool(call_subagent)
