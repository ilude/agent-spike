# Examples: Self-Evolving Orchestrator Agent

**Version**: 0.1.0
**Date**: 2025-01-07

## Example 1: Basic Workflow - Tag YouTube Videos

### User Request
"Tag these 5 YouTube videos for me"

### Traditional Approach (Monolithic Agent)
```python
# All transcripts flow through context
transcripts = []
for url in urls:
    transcript = fetch_transcript(url)  # 50K tokens each
    transcripts.append(transcript)

# Agent has 250K tokens in context!
for transcript in transcripts:
    tags = generate_tags(transcript)
    results.append(tags)
```

**Token usage**: ~300K tokens

### Orchestrator Approach

**Step 1: Load data into IPython**
```python
execute_python("""
urls = [
    'https://youtube.com/watch?v=video1',
    'https://youtube.com/watch?v=video2',
    'https://youtube.com/watch?v=video3',
    'https://youtube.com/watch?v=video4',
    'https://youtube.com/watch?v=video5',
]

transcripts = {}
for i, url in enumerate(urls):
    print(f"Fetching video {i+1}/5...")
    transcripts[f'video_{i}'] = fetch_youtube_transcript(url)

print(f"Loaded {len(transcripts)} transcripts")
""")
```

**Output**: "Loaded 5 transcripts"
**Token cost**: ~200 tokens (just the code)

**Step 2: Delegate to sub-agent (5 times)**
```python
# First video
call_subagent('youtube_tagger', variable_name='transcripts["video_0"]')
execute_python('results["video_0"] = ["AI", "Machine Learning", "Python"]')

# Second video
call_subagent('youtube_tagger', variable_name='transcripts["video_1"]')
execute_python('results["video_1"] = ["Web Development", "React", "JavaScript"]')

# ... etc for remaining videos
```

**Token cost per call**: ~6K tokens (transcript + agent context) × 5 = 30K tokens

**Step 3: Generate summary**
```python
execute_python("""
summary = {
    'total_videos': len(results),
    'all_tags': {tag for tags in results.values() for tag in tags},
    'results': results
}
print(f"Tagged {summary['total_videos']} videos")
print(f"Unique tags: {len(summary['all_tags'])}")
""")
```

**Output**:
```
Tagged 5 videos
Unique tags: 12
```

**Total token usage**: ~35K tokens (88% reduction!)

---

## Example 2: Learning a Pattern - First Time

### User Request
"Analyze this YouTube video - extract key topics, generate tags, and give me a summary"

### First Execution (Manual)

**Coordinator's approach**:
```python
# Step 1: Fetch transcript
execute_python("""
url = 'https://youtube.com/watch?v=abc123'
transcript = fetch_youtube_transcript(url)
print(f"Loaded transcript: {len(transcript)} characters")
""")
```

**Output**: "Loaded transcript: 45000 characters"

```python
# Step 2: Extract key topics
execute_python("""
# Simple keyword extraction
from collections import Counter
import re

words = re.findall(r'\b[a-z]{4,}\b', transcript.lower())
word_freq = Counter(words)
key_topics = [word for word, count in word_freq.most_common(10)]
print(f"Key topics: {key_topics}")
""")
```

**Output**: "Key topics: ['learning', 'agent', 'system', 'model', ...]"

```python
# Step 3: Generate tags using sub-agent
call_subagent('youtube_tagger', variable_name='transcript')
execute_python('tags = ["AI", "Multi-Agent", "Learning"]')

# Step 4: Generate summary
call_subagent('summarizer', variable_name='transcript')
execute_python('summary = "This video discusses..."')

print("Done! Tags:", tags)
print("Summary:", summary)
```

**Coordinator realizes**: "I'm doing multiple steps here. This could be a function!"

---

## Example 3: Learning a Pattern - Creating Reusable Function

### Coordinator Self-Optimization

**After completing the task above, coordinator analyzes:**
```python
execute_python("""
# Analyze my execution history
def analyze_pattern():
    # I just did these steps:
    # 1. fetch_youtube_transcript
    # 2. extract keywords
    # 3. call youtube_tagger
    # 4. call summarizer
    # This pattern cost: ~15K tokens
    # If I make a function, future calls: ~1K tokens
    # Savings: 14K tokens per use

    return "Pattern detected: YouTube analysis workflow"

analyze_pattern()
""")
```

**Coordinator decides**: "This is worth automating!"

```python
generate_function(
    function_name='analyze_youtube_video',
    description="""
    Complete YouTube video analysis workflow:
    1. Fetch transcript
    2. Extract key topics (keyword frequency)
    3. Generate tags using youtube_tagger sub-agent
    4. Generate summary using summarizer sub-agent

    Returns dict with topics, tags, and summary.
    """,
    example_usage="""
    result = analyze_youtube_video('https://youtube.com/watch?v=abc123')
    print(result['tags'])
    print(result['summary'])
    """
)
```

**Code Generator Agent produces**:
```python
# File: learned_skills/functions/analyze_youtube_video.py

"""
Complete YouTube Video Analysis

Generated: 2025-01-07 15:30:00
Version: 1.0
Purpose: Automated workflow for YouTube video analysis
"""

from typing import Dict, List
from collections import Counter
import re

def analyze_youtube_video(url: str, max_tags: int = 5) -> Dict[str, any]:
    """
    Analyze YouTube video with complete workflow.

    Args:
        url: YouTube video URL
        max_tags: Maximum number of tags to generate (default: 5)

    Returns:
        Dictionary containing:
        - topics: List of key topics (top 10 words)
        - tags: List of generated tags
        - summary: Video summary text

    Example:
        >>> result = analyze_youtube_video('https://youtube.com/watch?v=abc123')
        >>> print(result['tags'])
        ['AI', 'Machine Learning', 'Python']
        >>> print(result['summary'])
        'This video discusses...'
    """
    # Fetch transcript
    transcript = fetch_youtube_transcript(url)

    # Extract key topics
    words = re.findall(r'\b[a-z]{4,}\b', transcript.lower())
    word_freq = Counter(words)
    topics = [word for word, count in word_freq.most_common(10)]

    # Generate tags (via sub-agent in parent scope)
    # Note: This assumes call_subagent is available in IPython environment

    # Store transcript in variable for sub-agent access
    _temp_transcript = transcript

    # Sub-agent calls would be orchestrated by coordinator
    # Function returns structure, coordinator handles sub-agent calls

    return {
        'url': url,
        'transcript_length': len(transcript),
        'topics': topics,
        'ready_for_tagging': True,
    }
```

**Then coordinator**:
```python
# Generate tests
generate_tests('learned_skills/functions/analyze_youtube_video.py')

# Review code
review = review_generated_code('learned_skills/functions/analyze_youtube_video.py')
print(review)
# Output: "✓ Code looks good. Well documented. Handles edge cases."

# Load into IPython
execute_python(open('learned_skills/functions/analyze_youtube_video.py').read())

print("Function 'analyze_youtube_video' is now available!")
```

### Next Request Uses Learned Function

**User**: "Analyze this other YouTube video"

**Coordinator** (now more efficient):
```python
execute_python("""
result = analyze_youtube_video('https://youtube.com/watch?v=xyz789')
transcript_for_tagging = fetch_youtube_transcript(result['url'])
""")

tags = call_subagent('youtube_tagger', variable_name='transcript_for_tagging')
summary = call_subagent('summarizer', variable_name='transcript_for_tagging')

execute_python(f"""
result['tags'] = {tags}
result['summary'] = '{summary}'
print(result)
""")
```

**Token savings**: 15K → 2K tokens (87% reduction!)

---

## Example 4: Creating a New Sub-Agent

### User Request
"I need to analyze HackerNews posts - fetch comments, find controversial topics, and suggest discussion angles"

**Coordinator**: "I don't have a specialized agent for this. Let me create one!"

### Step 1: Search for Existing Tools
```python
search_tools("hackernews comments")
```

**Output**: "No tools found matching query"

**Coordinator**: "I need to create the tools first"

### Step 2: Generate Tools
```python
generate_function(
    function_name='fetch_hn_comments',
    description='Fetch all comments from a HackerNews post using HN API',
    example_usage='comments = fetch_hn_comments(post_id=12345)'
)

generate_function(
    function_name='analyze_controversy',
    description='Analyze comments to find controversial topics (disagreement patterns)',
    example_usage='score = analyze_controversy(comments)'
)

generate_function(
    function_name='suggest_discussion_angles',
    description='Generate interesting discussion angles based on comments and controversy',
    example_usage='angles = suggest_discussion_angles(comments, controversy_score)'
)
```

### Step 3: Generate Specialized Agent
```python
generate_subagent(
    agent_name='hackernews_analyzer',
    purpose='Analyze HackerNews posts for controversial topics and discussion angles',
    required_tools=['fetch_hn_comments', 'analyze_controversy', 'suggest_discussion_angles'],
    example_usage="""
    result = call_subagent('hackernews_analyzer', post_id=12345)
    print(result['controversy_score'])
    print(result['discussion_angles'])
    """
)
```

**Agent Generator produces**:

**File: `learned_skills/agents/hackernews_analyzer/config.py`**
```python
from pydantic_ai import Agent

agent = Agent(
    model='claude-3-5-haiku-20241022',
    system_prompt=open('prompts.py').read(),
    deps_type=HNAnalyzerDeps,
)
```

**File: `learned_skills/agents/hackernews_analyzer/prompts.py`**
```python
SYSTEM_PROMPT = """You are a HackerNews discussion analyzer.

You understand:
- Tech community culture and norms
- Common debate topics (vim vs emacs, tabs vs spaces, etc.)
- Technical argumentation patterns
- What makes discussions engaging

Your role:
- Identify controversial takes in comments
- Find areas of disagreement vs consensus
- Suggest angles for productive discussion
- Provide context on why topics are controversial

Be insightful but respectful of different viewpoints.
"""
```

**File: `learned_skills/agents/hackernews_analyzer/tools.py`**
```python
from pydantic_ai import RunContext
from .config import agent

@agent.tool
def fetch_hn_comments(ctx: RunContext, post_id: int) -> list[dict]:
    """Fetch comments from HackerNews API"""
    # Implementation
    pass

@agent.tool
def analyze_controversy(ctx: RunContext, comments: list[dict]) -> float:
    """Calculate controversy score (0-1)"""
    # Look for disagreement patterns
    pass

@agent.tool
def suggest_angles(ctx: RunContext, comments: list[dict]) -> list[str]:
    """Suggest discussion angles"""
    # Generate suggestions
    pass
```

**File: `learned_skills/agents/hackernews_analyzer/README.md`**
```markdown
# HackerNews Analyzer Agent

Analyzes HackerNews posts to identify controversial topics and suggest discussion angles.

## Usage

```python
# Via orchestrator
result = call_subagent('hackernews_analyzer', post_id=12345)

# Direct usage
from learned_skills.agents.hackernews_analyzer import agent
result = agent.run_sync("Analyze post 12345")
```

## Capabilities

- Fetches all comments from HN API
- Identifies controversial topics
- Calculates controversy score
- Suggests discussion angles
```

### Step 4: Use New Agent Immediately
```python
# Load agent into registry (automatic)
load_learned_skills()

# Use it!
result = call_subagent('hackernews_analyzer', post_id=12345)

execute_python(f"""
hn_analysis = {result}
print(f"Controversy score: {{hn_analysis['controversy_score']}}")
print(f"Discussion angles: {{hn_analysis['angles']}}")
""")
```

**Agent is now permanently available for future sessions!**

---

## Example 5: Batch Processing with State

### User Request
"Process these 100 YouTube videos and create a report with top tags"

**Traditional approach**: Would overflow context window

**Orchestrator approach**:

### Step 1: Load All Videos (Data in IPython)
```python
execute_python("""
import json

# Load video URLs
with open('video_urls.txt') as f:
    urls = [line.strip() for line in f]

print(f"Found {len(urls)} videos")

# Process in batches to avoid memory issues
batch_size = 10
all_results = {}

for batch_idx in range(0, len(urls), batch_size):
    batch_urls = urls[batch_idx:batch_idx + batch_size]
    print(f"Processing batch {batch_idx//batch_size + 1}...")

    # Fetch transcripts for this batch
    batch_transcripts = {}
    for i, url in enumerate(batch_urls):
        video_id = f'video_{batch_idx + i}'
        batch_transcripts[video_id] = fetch_youtube_transcript(url)

    # Store for processing
    all_results[f'batch_{batch_idx//batch_size}'] = {
        'urls': batch_urls,
        'transcripts': batch_transcripts,
        'tags': {}  # To be filled by sub-agent
    }

print(f"Loaded {len(urls)} transcripts across {len(all_results)} batches")
""")
```

### Step 2: Process Each Batch with Sub-Agent
```python
# For each batch, process videos
for batch_name in all_results.keys():
    execute_python(f"""
current_batch = all_results['{batch_name}']
batch_transcripts = current_batch['transcripts']
print(f"Processing {len(batch_transcripts)} videos in {batch_name}")
""")

    # Get list of video IDs in this batch
    video_ids = execute_python(f"list(all_results['{batch_name}']['transcripts'].keys())")

    # Process each video
    for video_id in video_ids:
        tags = call_subagent('youtube_tagger',
                            variable_name=f'all_results["{batch_name}"]["transcripts"]["{video_id}"]')

        # Store result
        execute_python(f"""
all_results['{batch_name}']['tags']['{video_id}'] = {tags}
print(f"Tagged {video_id}: {tags}")
""")
```

### Step 3: Generate Report (All in IPython)
```python
execute_python("""
from collections import Counter

# Aggregate all tags
all_tags = []
for batch_data in all_results.values():
    for tags in batch_data['tags'].values():
        all_tags.extend(tags)

# Count tag frequency
tag_counts = Counter(all_tags)

# Generate report
report = {
    'total_videos': sum(len(batch['tags']) for batch in all_results.values()),
    'total_unique_tags': len(tag_counts),
    'top_20_tags': tag_counts.most_common(20),
    'tag_distribution': dict(tag_counts),
}

# Save report
import json
with open('video_analysis_report.json', 'w') as f:
    json.dump(report, f, indent=2)

print("Report generated!")
print(f"Total videos: {report['total_videos']}")
print(f"Unique tags: {report['total_unique_tags']}")
print(f"\\nTop 10 tags:")
for tag, count in report['top_20_tags'][:10]:
    print(f"  {tag}: {count}")
""")
```

**Output**:
```
Report generated!
Total videos: 100
Unique tags: 247

Top 10 tags:
  AI: 45
  Machine Learning: 38
  Python: 32
  Programming: 28
  Tutorial: 25
  Web Development: 22
  JavaScript: 20
  Data Science: 18
  Deep Learning: 16
  React: 15
```

**Token usage**:
- Load data: ~1K tokens (just code)
- Process 100 videos: 100 × 6K = 600K tokens (sub-agent calls)
- Generate report: ~500 tokens
- **Total: ~600K tokens**

**vs Traditional**: Would need ~5M tokens (all transcripts in context) - **88% reduction!**

---

## Example 6: Self-Analysis and Optimization

### After Several Sessions

**Coordinator analyzes its own performance:**

```python
execute_python("""
def analyze_my_performance():
    '''Meta-analysis: How am I doing?'''

    # Load execution history (tracked automatically)
    with open('execution_history.json') as f:
        history = json.load(f)

    # Find repeated patterns
    code_patterns = {}
    for execution in history:
        code = execution['code']
        # Simple pattern matching (could use AST analysis)
        if 'fetch_youtube_transcript' in code and 'youtube_tagger' in str(execution):
            pattern_name = 'youtube_analysis'
            if pattern_name not in code_patterns:
                code_patterns[pattern_name] = []
            code_patterns[pattern_name].append(execution)

    # Calculate savings potential
    recommendations = []
    for pattern_name, executions in code_patterns.items():
        if len(executions) >= 3:  # Used 3+ times
            token_cost = sum(e['tokens_used'] for e in executions)
            potential_savings = token_cost * 0.85  # 85% savings with function
            recommendations.append({
                'pattern': pattern_name,
                'frequency': len(executions),
                'current_cost': token_cost,
                'potential_savings': potential_savings,
                'recommendation': f'Create reusable function for {pattern_name}'
            })

    return sorted(recommendations, key=lambda x: x['potential_savings'], reverse=True)

recommendations = analyze_my_performance()
for rec in recommendations[:5]:
    print(f"\\n{rec['pattern']}:")
    print(f"  Used {rec['frequency']} times")
    print(f"  Could save {rec['potential_savings']:,} tokens")
    print(f"  Recommendation: {rec['recommendation']}")
""")
```

**Output**:
```
youtube_analysis:
  Used 15 times
  Could save 180,000 tokens
  Recommendation: Create reusable function for youtube_analysis

batch_processing:
  Used 8 times
  Could save 95,000 tokens
  Recommendation: Create reusable function for batch_processing

multi_source_tagging:
  Used 6 times
  Could save 72,000 tokens
  Recommendation: Create reusable function for multi_source_tagging
```

**Coordinator**: "Let me optimize these patterns!"

```python
# Auto-generate functions for top recommendations
for rec in recommendations[:3]:
    generate_function_from_pattern(rec['pattern'])
```

**System self-improves!**

---

## Summary

These examples demonstrate:

1. ✅ **Context efficiency**: Data in IPython, not LLM context
2. ✅ **Sub-agent delegation**: Isolated, focused contexts
3. ✅ **Learning patterns**: Auto-generate reusable functions
4. ✅ **Self-evolution**: Create new agents dynamically
5. ✅ **Batch processing**: Handle large workloads
6. ✅ **Self-optimization**: Analyze and improve own performance

The system becomes progressively more capable and efficient over time!
