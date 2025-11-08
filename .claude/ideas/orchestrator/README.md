# Self-Evolving Orchestrator Agent

**Status**: Concept/Design Phase
**Created**: 2025-01-07
**Inspiration**:
- [Anthropic: Code Execution with MCP](https://www.anthropic.com/engineering/code-execution-with-mcp)
- [Cloudflare: Code Mode](https://blog.cloudflare.com/code-mode/)
- [Data Analytics Agent](https://github.com/agency-ai-solutions/data-analytics-agent)

## Overview

A self-evolving AI orchestrator that uses **stateful IPython execution** and **code generation** instead of traditional tool calling. The system can discover tools progressively, delegate to specialized sub-agents, and **generate new capabilities** (functions and agents) that persist as Python files.

## Core Innovation

Instead of loading all tool definitions upfront (causing context bloat), the orchestrator:

1. **Writes code** to interact with tools (not direct tool calls)
2. **Uses IPython kernel** as persistent working memory (data stays outside LLM context)
3. **Delegates to sub-agents** with isolated, temporary contexts
4. **Generates new code** (functions and agents) that it saves and reuses
5. **Self-improves** over time by learning patterns and creating specialized capabilities

## Key Benefits

### Context Efficiency
- **Traditional MCP**: 150K tokens for all tool definitions upfront
- **This approach**: 2K tokens (progressive discovery) + IPython working memory

### Data Persistence
- Large datasets (transcripts, spreadsheets) stay in IPython memory
- Never flow through LLM context
- Accessible across multiple operations

### Sub-Agent Isolation
- Specialized agents get only the data they need
- Context destroyed after task completion
- Budget-efficient and focused

### Self-Evolution
- System learns patterns and creates reusable functions
- Generates new specialized sub-agents as needed
- Builds institutional knowledge over time
- All saved as reviewable Python files (not pickle)

## Architecture Layers

```
┌─────────────────────────────────────────────────┐
│ Coordinator Agent (Orchestrator)               │
│ - Minimal context (coordination only)          │
│ - Progressive tool discovery                   │
│ - Code generation                              │
└─────────────────────────────────────────────────┘
                    │
         ┌──────────┼──────────┐
         │          │          │
         ▼          ▼          ▼
    ┌────────┐ ┌────────┐ ┌──────────────┐
    │ IPython│ │Sub-    │ │Code Generator│
    │ Kernel │ │Agents  │ │Agents        │
    └────────┘ └────────┘ └──────────────┘

    Persistent  Temporary  Create New
    Working     Focused    Capabilities
    Memory      Contexts
```

## Documents in This Directory

- **[PRD.md](./PRD.md)**: Complete Product Requirements Document
- **[ARCHITECTURE.md](./ARCHITECTURE.md)**: Technical architecture and implementation details
- **[EXAMPLES.md](./EXAMPLES.md)**: Concrete usage examples and workflows
- **[COMPARISON.md](./COMPARISON.md)**: Comparison with traditional approaches

## Quick Example

```python
# User: "Tag these 10 YouTube videos"

# Traditional approach: All transcripts flow through LLM context (500K tokens)

# Orchestrator approach:
execute_python("""
urls = ['url1', ..., 'url10']
transcripts = {}
for i, url in enumerate(urls):
    transcripts[f'video_{i}'] = fetch_transcript(url)  # Stays in IPython
""")

# Delegate to specialized sub-agent with isolated context
for i in range(10):
    tags = call_subagent('youtube_tagger', variable_name=f'transcripts["video_{i}"]')
    execute_python(f"results['video_{i}'] = {tags}")

# Total context: ~4K tokens (coordinator) + 10 × 6K tokens (sub-agent calls)
# vs 500K+ tokens in traditional approach
```

## Next Steps

1. Review PRD and architecture documents
2. Build proof-of-concept as `lesson-004`
3. Implement core orchestrator with IPython execution
4. Add progressive tool discovery
5. Implement sub-agent delegation
6. Add code-generating sub-agents
7. Test self-evolution capabilities

## Related Work

- **Lesson 001**: YouTube tagging agent (potential sub-agent)
- **Lesson 002**: Webpage tagging agent (potential sub-agent)
- **Lesson 003**: Multi-agent coordinator (inspiration for routing pattern)
