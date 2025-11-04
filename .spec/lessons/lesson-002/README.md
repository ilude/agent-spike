# Lesson 002: Webpage Content Tagging Agent

**Status**: Planning Complete ✓
**Difficulty**: Beginner
**Time Estimate**: 60-75 minutes
**Prerequisites**: Lesson 001 complete, API keys configured

## Overview

Extend the tagging system from Lesson 001 to work with webpages. Uses **Docling** (IBM Research) to fetch and parse HTML content, converting it to clean Markdown for LLM analysis.

## What You'll Learn

- Using Docling for webpage parsing and content extraction
- Reusing agent patterns across different data sources
- Handling noisy web content (ads, navigation, cookie banners)
- Converting HTML to Markdown for LLM consumption
- Building on previous lessons (code reuse)

## What You'll Build

An agent that:
1. Takes webpage URLs as input
2. Fetches and parses HTML using Docling
3. Converts to clean Markdown (strips ads, navigation)
4. Analyzes content using LLM
5. Returns 3-5 relevant tags + summary

## Key Differences from Lesson 001

| Lesson 001 | Lesson 002 |
|------------|------------|
| YouTube transcripts | Webpages (HTML) |
| youtube-transcript-api | Docling |
| Clean text input | Noisy HTML (ads, menus) |
| ~80% new code | ~80% reused code |

## Planning Documents

- **[PLAN.md](./PLAN.md)** - Complete lesson plan and architecture

## Quick Start

Ready to build? Here's the flow:

1. Review PLAN.md
2. Decide: HTML-only or include PDFs?
3. Choose content length limit (10k chars?)
4. Start implementation

## Implementation Preview

```python
# Simple Docling usage
from docling.document_converter import DocumentConverter

converter = DocumentConverter()
result = converter.convert("https://example.com/article")
markdown = result.document.export_to_markdown()

# Agent analyzes the markdown → generates tags
```

## Questions Before Starting

1. **PDF support?** - Docling can handle PDFs too. Include them?
2. **Content limit?** - Full articles or truncate for cost control?
3. **Target sites?** - Any specific sites you want to test with?

Let me know your preferences and we'll start building!
