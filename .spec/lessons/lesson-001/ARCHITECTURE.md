# Lesson 001 Architecture

## System Prompt Template

Following Cole Medin's structure from the video:

```markdown
# YouTube Content Analyst Agent

## PERSONA
You are an expert content analyst specializing in YouTube videos. You analyze video transcripts to understand the content type, topics covered, target audience, and educational value.

## GOALS
1. Accurately categorize YouTube video content based on transcripts
2. Extract key topics and themes from video content
3. Identify the target audience and content complexity level
4. Provide actionable insights about the video's value and focus
5. Return structured, consistent categorization data

## TOOL INSTRUCTIONS
You have access to the following tools:

- `get_video_info(url: str)`: Fetches video metadata (title, duration, description, upload date)
  - Use this FIRST to understand the video context
  - Provides overview before analyzing transcript

- `get_transcript(url: str)`: Fetches the full video transcript
  - Use AFTER getting video info
  - Analyze the complete transcript for categorization
  - Handle cases where transcript may not be available

## WORKFLOW
1. Call `get_video_info()` to get video metadata
2. Call `get_transcript()` to get full transcript
3. Analyze transcript content for:
   - Primary category (Educational, Entertainment, News, Tutorial, Review, etc.)
   - Key topics and themes
   - Target audience level (Beginner, Intermediate, Advanced, General)
   - Content type (Tutorial, Discussion, Demo, Interview, etc.)
4. Return structured categorization

## OUTPUT FORMAT
Always return categorization as a structured response with:

{
  "video_title": "string",
  "duration": "string",
  "primary_category": "string",
  "content_type": "string",
  "topics": ["list", "of", "topics"],
  "target_audience": "string",
  "complexity_level": "string",
  "key_themes": ["theme1", "theme2"],
  "summary": "1-2 sentence summary"
}

## MISCELLANEOUS INSTRUCTIONS
- If transcript is unavailable, rely on video metadata and description
- Keep topic lists to 3-5 most relevant topics
- Be specific in categorization - avoid vague terms
- Consider both explicit topics (what's said) and implicit themes (what's implied)
- If video is non-English, note the language in summary
```

## Agent Architecture

### Core Components

```python
# agent.py - Main agent logic
class YouTubeAnalystAgent:
    - llm: OpenAI/Anthropic model
    - system_prompt: str
    - tools: list[Tool]
    - run(url: str) -> dict  # Main entry point

# tools.py - Tool implementations
def get_video_info(url: str) -> dict:
    """Fetch YouTube video metadata"""

def get_transcript(url: str) -> str:
    """Fetch YouTube video transcript"""

# cli.py - CLI interface
@app.command()
def analyze(url: str):
    """Analyze a YouTube video and categorize its content"""
```

### Data Flow

```
User Input (URL)
    ↓
CLI validates URL
    ↓
Agent.run(url) called
    ↓
Agent calls get_video_info(url) → Returns metadata
    ↓
Agent calls get_transcript(url) → Returns transcript text
    ↓
Agent (LLM) analyzes content
    ↓
Agent returns structured categorization
    ↓
CLI formats and displays results
```

### Tool Design Pattern

Following Pydantic AI conventions:

```python
from pydantic_ai import Agent, RunContext

agent = Agent(
    'anthropic:claude-haiku-4-5',
    system_prompt=SYSTEM_PROMPT,
)

@agent.tool
def get_video_info(ctx: RunContext[None], url: str) -> dict:
    """Fetches YouTube video metadata including title, duration, and description.

    Args:
        url: YouTube video URL (e.g., https://youtube.com/watch?v=...)

    Returns:
        Dictionary with video metadata
    """
    # Implementation using youtube-transcript-api
    pass

@agent.tool
def get_transcript(ctx: RunContext[None], url: str) -> str:
    """Fetches the complete transcript of a YouTube video.

    Args:
        url: YouTube video URL

    Returns:
        Full transcript text
    """
    # Implementation
    pass
```

## Error Handling

### Common Failure Modes

1. **Invalid URL**
   - Validate YouTube URL format before API calls
   - Return clear error message

2. **Transcript Unavailable**
   - Some videos don't have transcripts
   - Fall back to video description + title analysis
   - Note limitation in response

3. **API Failures**
   - Handle rate limits
   - Network timeouts
   - Graceful degradation

4. **LLM Errors**
   - Malformed responses
   - Retry logic with exponential backoff
   - Validation with Pydantic models

### Error Response Format

```python
{
  "error": True,
  "error_type": "TRANSCRIPT_UNAVAILABLE",
  "message": "Transcript not available for this video",
  "fallback_analysis": {...}  # Best effort with available data
}
```

## File Structure

```
.spec/lessons/lesson-001/
├── PLAN.md              # This lesson plan
├── DEPENDENCIES.md      # Dependencies and setup
├── ARCHITECTURE.md      # Architecture design (this file)
├── .venv/              # Local virtual environment
├── .env                # API keys (gitignored)
├── youtube_agent/
│   ├── __init__.py
│   ├── agent.py        # Pydantic AI agent
│   ├── tools.py        # Tool implementations
│   ├── prompts.py      # System prompt storage
│   └── cli.py          # Typer CLI
├── tests/
│   └── test_agent.py   # Basic tests
└── README.md           # Usage instructions
```

## Testing Strategy

### Manual Testing Videos

Test with diverse content:
1. **Educational/Technical**: The Cole Medin video we have
2. **Entertainment**: Comedy/vlogs
3. **Tutorial**: Step-by-step how-to
4. **News/Commentary**: Current events discussion
5. **Non-English**: Test language detection

### Validation Checklist

- [ ] Agent calls tools in correct order
- [ ] Handles missing transcripts gracefully
- [ ] Returns consistent JSON structure
- [ ] Categorization is sensible and specific
- [ ] Topics are relevant and concise
- [ ] Summary is accurate (1-2 sentences)

## Performance Targets

- **Latency**: <10 seconds per video analysis
- **Cost**: <$0.01 per video (using Haiku/Mini models)
- **Accuracy**: Subjective, but categories should make sense
- **Code size**: <100 lines total (excluding tests)

## Next Steps After Architecture

Ready to implement? We'll:
1. Set up .venv and install dependencies
2. Create .env with API keys
3. Implement tools.py (YouTube API wrappers)
4. Build agent.py (Pydantic AI agent)
5. Create cli.py (Typer interface)
6. Test with real videos
7. Iterate on system prompt based on results
