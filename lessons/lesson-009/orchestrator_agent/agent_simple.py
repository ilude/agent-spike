"""
Simplified Orchestrator Agent

Uses direct LLM calls instead of nested agents to avoid deadlocks.
"""

from pydantic_ai import Agent
from .tools_simple import call_subagent_simple

# System prompt for orchestrator
SYSTEM_PROMPT = """You are an orchestrator that coordinates specialized sub-agents.

Available sub-agents:
- youtube_tagger: Tags YouTube videos (use for youtube.com URLs)
- webpage_tagger: Tags web articles (use for other URLs)

When given URLs to process:
1. Identify which sub-agent to use for each URL
2. Call call_subagent_simple(agent_name, url) for each URL
3. Collect all results
4. Summarize the tags found

Be efficient: call sub-agents in parallel when possible (make multiple tool calls).
Return organized results showing tags for each URL.
"""

# Create orchestrator agent
orchestrator = Agent(
    model="openai:gpt-5-mini",  # Using mini for better tool calling
    system_prompt=SYSTEM_PROMPT,
)

# Register the simplified tool
orchestrator.tool(call_subagent_simple)