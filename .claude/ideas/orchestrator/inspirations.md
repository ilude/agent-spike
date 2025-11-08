# Inspirations

  ## 2025-01-07: MCP Code Execution Pattern
  - **Sources**:
    - [Anthropic: Code Execution with MCP](https://www.anthropic.com/engineering/code-execution-with-mcp)
    - [Cloudflare Code Mode](https://blog.cloudflare.com/code-mode/)
    - [Data Analytics Agent](https://github.com/agency-ai-solutions/data-analytics-agent)
  - **Key insight**: Code execution > direct tool calls (LLMs better at code than tool syntax)
  - **Breakthrough**: IPython kernel as persistent working memory + sub-agents for isolation + self-evolution through generated .py
  files
  - **What we built**: orchestrator concept, design docs in `.claude/ideas/orchestrator/` (PRD, architecture, examples, comparisons,
  decisions - 2679 lines)
  - **Status**: Designed, not implemented. Save for when we hit actual orchestration pain.
  - **Impact**: Could become core pattern if simple coordinator (lesson-003) proves insufficient