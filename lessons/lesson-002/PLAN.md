# Lesson 002: Webpage Content Tagging Agent

## Learning Objectives

- Fetch and parse web content using Docling
- Reuse agent patterns from Lesson 001
- Handle HTML → Markdown conversion
- Filter out noise (ads, navigation, cookie banners)
- Scale tagging system to general web content

## Project Overview

Build an AI agent that can:
1. Accept webpage URLs (articles, blog posts, documentation)
2. Fetch and parse HTML content using Docling
3. Convert to clean Markdown
4. Tag content with 3-5 relevant topics
5. Provide structured output for read-it-later apps

## Technologies

- **Python 3.14** with shared .venv (root project)
- **uv** - Package manager
- **Pydantic AI** - Agent framework (reuse from Lesson 001)
- **Docling** - Document parsing and HTML → Markdown
- **Claude/OpenAI** - LLM backend
- **Typer** - CLI interface

## Why Docling?

- **Local processing** - No external API, data stays private
- **HTML support** - Parses webpages natively
- **Clean output** - Smart filtering of navigation, ads, footers
- **Markdown export** - Perfect for LLM consumption
- **MIT license** - Open source, permissive
- **Active development** - IBM Research, trending on GitHub

## Architecture

```
webpage_agent/
├── __init__.py
├── agent.py          # Pydantic AI agent (reuse pattern)
├── tools.py          # Docling-based web fetching
├── prompts.py        # Tagging prompt (adapted from Lesson 001)
└── cli.py            # Typer CLI
```

## Agent Components

### 1. System Prompt
Reuse the tagging prompt from Lesson 001 with minor tweaks:
- Same rules (3-5 tags, broad categories, no generic noise)
- Updated tool descriptions for `fetch_webpage()`
- Handle cookie banners, privacy notices automatically

### 2. Tools
- `fetch_webpage(url)` - Uses Docling to:
  - Download HTML
  - Parse and extract main content
  - Convert to Markdown
  - Strip navigation, ads, footers
  - Return clean text for analysis

### 3. LLM Choice
- Continue with Claude Haiku (cheap, fast)
- Same model switching capability

### 4. Memory
- Short-term: Conversation history
- No long-term needed yet

## Docling Integration

### Basic Usage
```python
from docling.document_converter import DocumentConverter

converter = DocumentConverter()
result = converter.convert("https://example.com/article")
markdown = result.document.export_to_markdown()
```

### Advanced Options
```python
from docling.datamodel.pipeline_options import PipelineOptions
from docling.document_converter import DocumentConverter

# Configure for web content
pipeline_options = PipelineOptions()
pipeline_options.do_ocr = False  # Not needed for HTML
pipeline_options.do_table_structure = True

converter = DocumentConverter(pipeline_options=pipeline_options)
```

## Implementation Steps

1. **Setup** (~5 min)
   - Add docling to lesson-002 dependency group
   - `uv sync --group lesson-002`
   - Copy .env from lesson-001

2. **Docling Tool** (~15 min)
   - Create `fetch_webpage()` function
   - Handle URL validation
   - Parse with Docling
   - Export to Markdown
   - Error handling (404, timeouts, etc.)

3. **Agent Core** (~10 min)
   - Copy agent.py from lesson-001
   - Update tool from `get_transcript` to `fetch_webpage`
   - Adapt system prompt for web content
   - Test with single webpage

4. **CLI Interface** (~10 min)
   - Reuse CLI pattern from lesson-001
   - Update help text for webpages
   - Interactive mode for multiple URLs

5. **Testing & Iteration** (~15 min)
   - Test with news articles, blogs, documentation
   - Verify cookie banner filtering
   - Refine prompt for web-specific noise

## Expected Output

```bash
uv run python -m webpage_agent.cli analyze "https://example.com/article"

# Result:
Title: "Building Production-Ready AI Agents"
Tags: [ai-engineering, software-architecture, devops, machine-learning]
Summary: Article discusses best practices for deploying AI agents in production...
Content Length: 3,450 words
```

## Success Criteria

- ✓ Agent fetches and parses webpage content
- ✓ Docling strips navigation, ads, cookie banners
- ✓ Tags are relevant to main content (not UI elements)
- ✓ Handles common errors (404, paywall, etc.)
- ✓ Code remains <150 lines total
- ✓ Reuses 80% of Lesson 001 code

## Challenges to Address

### 1. Content Quality
- Some sites have paywalls → Detect and report
- JavaScript-heavy sites → May not render fully
- Solution: Detect empty/short content, return error

### 2. Noise Filtering
- Cookie banners, newsletter popups
- Solution: Docling handles most, prompt instructs LLM to ignore

### 3. Large Content
- Long articles → High token costs
- Solution: Truncate to first 10,000 characters for tagging

### 4. Rate Limiting
- Fetching many pages quickly
- Solution: Add simple delay in interactive mode

## Comparison to Lesson 001

| Aspect | Lesson 001 (YouTube) | Lesson 002 (Webpages) |
|--------|---------------------|----------------------|
| Source | YouTube transcripts | HTML webpages |
| Fetcher | youtube-transcript-api | Docling |
| Format | Plain text | Markdown |
| Challenge | No metadata | Noise filtering |
| Use Case | Video tagging | Article tagging |
| Code Reuse | Base template | 80% reused |

## Test Webpages

1. **Technical blog**: https://simonwillison.net/
2. **News article**: https://arstechnica.com/
3. **Documentation**: https://docs.pydantic.dev/
4. **Research paper**: https://arxiv.org/abs/2408.09869

## Next Lessons

- **Lesson 003**: Add Langfuse observability to both agents
- **Lesson 004**: Multi-agent coordinator (routes to YouTube or Webpage agent)
- **Lesson 005**: Mem0 for tag standardization across sessions

## Questions Before Starting

1. Should we handle PDFs too, or just HTML?
2. Content length limit for tagging (10k chars? full article)?
3. Any specific sites you want to test with?

## Estimated Time

- Planning: Complete ✓
- Implementation: 45-60 minutes
- Testing: 15 minutes
- **Total**: ~60-75 minutes
