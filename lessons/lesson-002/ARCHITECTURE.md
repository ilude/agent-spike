# Lesson 002 Architecture

## System Prompt

Reuse from Lesson 001 with minor adaptation:

```markdown
# Webpage Content Tagging Agent

You are an expert whose responsibility is to help with automatic tagging for a read-it-later app.

You will receive webpage content in Markdown format. Please analyze the content and suggest relevant tags that describe its key themes, topics, and main ideas.

## RULES
- Aim for a variety of tags, including broad categories, specific keywords, and potential sub-genres
- If the tag is not generic enough, don't include it
- The content may include navigation menus, cookie consent, privacy notices, and ads - IGNORE these while tagging
- Focus only on the main article/content
- Aim for 3-5 tags
- If there are no good tags, return an empty array
- Tags should be lowercase and use hyphens for multi-word tags (e.g., "web-development")

## TOOL USAGE
You have access to:

- `fetch_webpage(url)`: Fetches webpage content and converts to Markdown
  - Use this to get the article content
  - Returns clean Markdown with ads/navigation removed
  - May return error if page is inaccessible or behind paywall

## WORKFLOW
1. Call `fetch_webpage(url)` to get Markdown content
2. Analyze the main content, ignoring:
   - Navigation menus
   - Cookie banners
   - Newsletter signup prompts
   - Ads and promotional content
   - Footer links
3. Identify key themes and topics
4. Generate 3-5 broad, reusable tags

## OUTPUT FORMAT
Return a JSON object with:
{
  "page_title": "string",
  "tags": ["tag1", "tag2", "tag3"],
  "summary": "Brief 1-sentence description of the article",
  "content_length": "approximate word count"
}

If page is inaccessible, return error information.
```

## Tool Design

### fetch_webpage() Implementation

```python
from docling.document_converter import DocumentConverter
from docling.datamodel.pipeline_options import PipelineOptions

def fetch_webpage(url: str) -> str:
    """Fetch webpage content and convert to clean Markdown.

    Args:
        url: Webpage URL

    Returns:
        Clean Markdown content or error message
    """
    try:
        # Configure Docling for web content
        pipeline_options = PipelineOptions()
        pipeline_options.do_ocr = False  # HTML doesn't need OCR
        pipeline_options.do_table_structure = True  # Preserve tables

        converter = DocumentConverter(
            pipeline_options=pipeline_options
        )

        # Fetch and convert
        result = converter.convert(url)
        markdown = result.document.export_to_markdown()

        # Check if content is too short (likely error/paywall)
        if len(markdown.strip()) < 100:
            return "ERROR: Page content too short (paywall or empty page)"

        # Optionally truncate for cost control
        max_chars = 15000  # ~3750 words
        if len(markdown) > max_chars:
            markdown = markdown[:max_chars] + "\n\n[Content truncated...]"

        return markdown

    except Exception as e:
        return f"ERROR: Failed to fetch page: {str(e)}"
```

## File Structure

```
.spec/lessons/lesson-002/
├── PLAN.md                  # Lesson plan
├── ARCHITECTURE.md          # This file
├── README.md               # Quick start
├── .env                    # API keys (symlink or copy from lesson-001)
├── webpage_agent/
│   ├── __init__.py
│   ├── agent.py           # Pydantic AI agent (adapted from lesson-001)
│   ├── tools.py           # Docling wrapper
│   ├── prompts.py         # System prompt (adapted from lesson-001)
│   └── cli.py             # Typer CLI (adapted from lesson-001)
└── tests/
    └── test_agent.py      # Basic tests
```

## Data Flow

```
User Input (URL)
    ↓
CLI validates URL
    ↓
Agent.run(url) called
    ↓
Agent calls fetch_webpage(url)
    ↓
Docling:
  - Downloads HTML
  - Parses DOM
  - Extracts main content
  - Strips navigation/ads
  - Converts to Markdown
    ↓
Agent (LLM) analyzes Markdown
    ↓
Agent returns tags + summary
    ↓
CLI displays results
```

## Error Handling

### Common Failure Modes

1. **404 / Page Not Found**
   - Return clear error: "Page not found (404)"

2. **Paywall / Login Required**
   - Detect short/empty content
   - Return: "Content inaccessible (likely paywall)"

3. **JavaScript-Heavy Sites**
   - Docling may not render JS
   - Return partial content with warning

4. **Network Errors**
   - Timeout, DNS failures
   - Return connection error message

5. **Very Large Pages**
   - Truncate to 15,000 characters
   - Note truncation in response

## Code Reuse from Lesson 001

### What We Reuse (80%)

- ✓ Agent structure (`agent.py`)
- ✓ CLI interface (`cli.py`)
- ✓ System prompt pattern (`prompts.py`)
- ✓ Error handling approach
- ✓ Interactive mode
- ✓ Output formatting

### What We Change (20%)

- ✗ Tool implementation (`tools.py` - Docling instead of youtube-transcript-api)
- ✗ Tool name (`fetch_webpage` instead of `get_transcript`)
- ✗ Prompt tweaks (mention ignoring navigation/ads)
- ✗ Input validation (URL patterns for webpages vs YouTube)

## Performance Considerations

### Latency
- Docling parsing: 2-5 seconds per page
- LLM analysis: 3-8 seconds
- **Total**: 5-15 seconds per webpage

### Cost
- Claude Haiku: ~$0.01 per article (assuming 3k words)
- Longer articles: up to $0.03

### Token Usage
- Markdown is more verbose than plain text
- Expect 1.5-2x more tokens than equivalent plain text
- Truncation helps control costs

## Testing Strategy

### Test Pages

1. **Clean blog post**
   - https://simonwillison.net/2024/Dec/8/prompts-grammars/
   - Expected: Clean markdown, accurate tags

2. **News article with ads**
   - https://arstechnica.com/
   - Expected: Ads stripped, main content tagged

3. **Documentation page**
   - https://docs.pydantic.dev/latest/
   - Expected: Code blocks preserved, technical tags

4. **Complex layout**
   - https://github.com/docling-project/docling
   - Expected: Main README content extracted

### Validation Checklist

- [ ] Fetches webpage content successfully
- [ ] Strips navigation menus
- [ ] Removes cookie banners
- [ ] Filters out ads
- [ ] Preserves main article content
- [ ] Generates relevant tags (not UI-related)
- [ ] Handles 404 errors gracefully
- [ ] Detects paywalls
- [ ] Truncates very long content
- [ ] Returns consistent JSON structure

## Next Steps After Architecture

Ready to implement? We'll:
1. Add Docling to dependencies
2. Create tool wrapper for `fetch_webpage()`
3. Copy and adapt agent from lesson-001
4. Update prompts for web content
5. Build CLI (minimal changes)
6. Test with diverse webpages
7. Iterate based on results
