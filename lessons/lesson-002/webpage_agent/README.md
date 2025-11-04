# Webpage Tagging Agent

AI agent that analyzes webpage content and generates tags for read-it-later applications.

## Features

- Fetches webpage content using Docling
- Converts HTML to clean Markdown
- Strips ads, navigation, and UI elements automatically
- Generates 3-5 relevant tags using LLM
- Truncates content to 15k chars for cost control
- CLI interface with single page and interactive modes

## Usage

```bash
# Single webpage analysis
cd .spec/lessons/lesson-002
uv run python -m webpage_agent.cli analyze "https://example.com/article"

# Interactive mode
uv run python -m webpage_agent.cli interactive

# Use different model
uv run python -m webpage_agent.cli analyze "URL" --model gpt-4o-mini
```

## How It Works

1. Docling fetches and parses HTML
2. Converts to clean Markdown (removes ads, navigation)
3. Truncates to 15k chars if needed
4. LLM analyzes content
5. Returns 3-5 relevant tags + summary

## Limitations

- HTML webpages only (no PDFs in this version)
- Content truncated to ~15k chars (~3750 words)
- JavaScript-heavy sites may not render fully
- Paywalled content will be detected and reported

## Example Output

```json
{
  "page_title": "Introduction to AI Agents",
  "tags": ["artificial-intelligence", "software-engineering", "python", "tutorial"],
  "summary": "Comprehensive guide to building AI agents with modern frameworks"
}
```
