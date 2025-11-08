# Architecture: Self-Evolving Orchestrator Agent

**Version**: 0.1.0
**Date**: 2025-01-07

## System Architecture

### High-Level Overview

```
┌─────────────────────────────────────────────────────────────┐
│                    Coordinator Agent                         │
│  - Pydantic AI agent with minimal context                   │
│  - Has access to meta-tools only                            │
│  - Orchestrates via code generation                         │
└─────────────────────────────────────────────────────────────┘
                            │
                            │ Tools
        ┌───────────────────┼───────────────────┐
        │                   │                   │
        ▼                   ▼                   ▼
┌──────────────┐    ┌──────────────┐   ┌──────────────┐
│ IPython      │    │ Sub-Agents   │   │ Code Gen     │
│ Kernel       │    │ Registry     │   │ Agents       │
├──────────────┤    ├──────────────┤   ├──────────────┤
│ - Variables  │    │ - YouTube    │   │ - Code Gen   │
│ - Functions  │    │ - Webpage    │   │ - Test Gen   │
│ - Datasets   │    │ - Custom     │   │ - Code Review│
│ - State      │    │              │   │ - Agent Gen  │
└──────────────┘    └──────────────┘   └──────────────┘
        │                   │                   │
        │                   │                   │
        ▼                   ▼                   ▼
┌──────────────────────────────────────────────────────┐
│            Learned Skills (File System)              │
│  learned_skills/                                     │
│  ├── functions/                                      │
│  ├── agents/                                         │
│  ├── tests/                                          │
│  └── sessions/                                       │
└──────────────────────────────────────────────────────┘
```

## Core Components

### 1. Coordinator Agent

**Responsibility**: High-level orchestration and decision-making

**Tools Available**:
- `search_tools(query)` - Discover available tools
- `execute_python(code)` - Execute code in IPython
- `list_variables()` - Inspect IPython state
- `inspect_variable(name)` - Get variable details
- `call_subagent(agent_name, variable_name, **kwargs)` - Delegate to specialist
- `generate_function(name, description, example)` - Create new function
- `generate_subagent(name, purpose, tools, example)` - Create new agent
- `generate_tests(filepath)` - Create tests for code
- `review_generated_code(filepath)` - Review code quality
- `save_session_state(name)` - Persist session
- `load_session_state(name)` - Restore session
- `load_learned_skills()` - Load all learned capabilities

**Context Budget**:
- System prompt: ~1K tokens
- Tool definitions: ~500 tokens (meta-tools only)
- Conversation history: ~2K tokens
- **Total: ~4K tokens** (vs 150K traditional)

**Implementation**:
```python
coordinator = Agent(
    model='claude-3-5-sonnet-20241022',
    system_prompt="""You are an orchestrator agent.

    You have access to:
    1. IPython kernel for persistent working memory
    2. Sub-agents for specialized tasks
    3. Code generation for creating new capabilities

    Optimize for:
    - Token efficiency (keep data in IPython, not context)
    - Reusability (create functions for repeated patterns)
    - Specialization (delegate to focused sub-agents)
    """,
    deps_type=OrchestratorDeps,
)
```

### 2. IPython Kernel

**Responsibility**: Persistent working memory and code execution environment

**Key Features**:
- Single initialization per session
- Variables persist across executions
- Standard library access (pandas, numpy, etc.)
- Tool registry functions available
- Sandboxed execution

**Implementation**:
```python
from IPython.core.interactiveshell import InteractiveShell

# Initialize once
kernel = InteractiveShell.instance()

# Configure restrictions
kernel.enable_gui = lambda x: None  # Disable GUI
# Add import restrictions via import hooks

# Make tool registry available
kernel.user_ns['fetch_transcript'] = fetch_transcript_impl
kernel.user_ns['fetch_webpage'] = fetch_webpage_impl
# ... etc

def execute_code(code: str) -> dict:
    """Execute code and return results"""
    result = kernel.run_cell(code)

    return {
        'success': not result.error_in_exec,
        'result': result.result,
        'stdout': result.stdout if hasattr(result, 'stdout') else '',
        'error': str(result.error_in_exec) if result.error_in_exec else None,
    }
```

**Security Measures**:
- Import whitelist (only approved modules)
- No subprocess/os.system access
- No file I/O outside approved directories
- Timeout limits (60s max)
- Memory limits

### 3. Tool Registry

**Responsibility**: Central registry of available tool functions

**Structure**:
```python
TOOL_REGISTRY = {
    'fetch_youtube_transcript': {
        'function': fetch_youtube_transcript_impl,
        'signature': 'fetch_youtube_transcript(url: str) -> str',
        'description': 'Fetch transcript from YouTube video',
        'category': 'data_retrieval',
        'tags': ['youtube', 'transcript', 'video'],
    },
    'fetch_webpage': {
        'function': fetch_webpage_impl,
        'signature': 'fetch_webpage(url: str) -> str',
        'description': 'Fetch and convert webpage to markdown',
        'category': 'data_retrieval',
        'tags': ['webpage', 'html', 'markdown'],
    },
    # ... more tools
}
```

**Search Implementation**:
```python
def search_tools(query: str) -> str:
    """Search for tools matching query"""
    query_lower = query.lower()
    results = []

    for name, info in TOOL_REGISTRY.items():
        # Keyword matching
        if (query_lower in name.lower() or
            query_lower in info['description'].lower() or
            any(query_lower in tag for tag in info['tags'])):

            results.append(
                f"{info['signature']}\n"
                f"  {info['description']}\n"
            )

    if not results:
        return "No tools found matching query"

    return "\n".join(results)
```

**Future Enhancement**: Semantic search using embeddings

### 4. Sub-Agent Registry

**Responsibility**: Manage specialized sub-agents

**Structure**:
```python
SUBAGENT_REGISTRY = {
    'youtube_tagger': youtube_tagger_agent,
    'webpage_tagger': webpage_tagger_agent,
    'hackernews_analyzer': hackernews_analyzer_agent,
    # ... dynamically added agents
}
```

**Sub-Agent Calling**:
```python
@coordinator.tool
def call_subagent(
    agent_name: str,
    variable_name: str,
    **extra_kwargs
) -> str:
    """Call specialized sub-agent with data from IPython"""

    # 1. Get data from IPython environment
    data = kernel.user_ns.get(variable_name)
    if data is None:
        return f"Error: Variable '{variable_name}' not found"

    # 2. Get sub-agent
    subagent = SUBAGENT_REGISTRY.get(agent_name)
    if subagent is None:
        return f"Error: Sub-agent '{agent_name}' not found"

    # 3. Prepare dependencies/context for sub-agent
    deps = subagent.deps_type(data=data, **extra_kwargs)

    # 4. Call sub-agent with FRESH context (no history)
    result = subagent.run_sync(
        user_prompt=f"Process this {variable_name}",
        message_history=[],  # Fresh context!
        deps=deps,
    )

    # 5. Context destroyed when this function returns
    return result.data
```

**Key Points**:
- Each sub-agent call is isolated (no shared history)
- Data extracted from IPython, passed to sub-agent
- Result returned to coordinator
- Sub-agent context garbage collected

### 5. Code Generator Agents

**Responsibility**: Generate new functions and agents

#### Code Generator

```python
code_generator = Agent(
    model='claude-3-5-sonnet-20241022',  # Use better model
    system_prompt="""You are an expert Python code generator.

    Generate clean, type-hinted, documented Python code.
    Follow PEP 8 style guidelines.
    Include comprehensive docstrings with examples.
    Consider edge cases and error handling.

    Return ONLY the Python code, no explanations or markdown.
    """,
)
```

#### Test Generator

```python
test_generator = Agent(
    model='claude-3-5-sonnet-20241022',
    system_prompt="""You are an expert pytest test writer.

    Generate comprehensive test cases:
    - Happy path tests
    - Edge cases
    - Error conditions
    - Mock external dependencies

    Use pytest fixtures and parametrize where appropriate.
    Return ONLY the test code, no explanations.
    """,
)
```

#### Code Reviewer

```python
code_reviewer = Agent(
    model='claude-3-5-sonnet-20241022',
    system_prompt="""You are a senior Python code reviewer.

    Review code for:
    - Correctness (logic errors, edge cases)
    - Security (injection, unsafe operations)
    - Performance (inefficient algorithms)
    - Style (PEP 8 compliance)
    - Maintainability (readability, documentation)

    Format each issue as:
    [SEVERITY] Issue: Description
    Suggestion: Specific fix
    """,
)
```

#### Agent Generator

```python
agent_generator = Agent(
    model='claude-3-5-sonnet-20241022',
    system_prompt="""You are a Pydantic AI agent architect.

    Generate complete agent definitions including:
    - config.py: Agent setup (model, system_prompt, deps_type)
    - tools.py: Tool definitions with @agent.tool decorators
    - prompts.py: System prompts and templates
    - README.md: Purpose, usage, examples

    Follow existing patterns from lessons 001-003.
    Return JSON with file contents.
    """,
)
```

### 6. Learned Skills Directory

**Structure**:
```
learned_skills/
├── __init__.py
├── functions/
│   ├── __init__.py
│   ├── smart_tag_youtube.py
│   │   # """
│   │   # Smart YouTube Tagging
│   │   #
│   │   # Generated: 2025-01-15 14:23
│   │   # Version: 1.2
│   │   # Purpose: Efficient tagging with keyword extraction
│   │   # """
│   │   #
│   │   # def smart_tag_youtube(url: str) -> list[str]:
│   │   #     ...
│   └── batch_process_videos.py
├── agents/
│   ├── hackernews_analyzer/
│   │   ├── __init__.py
│   │   ├── config.py          # Agent definition
│   │   ├── tools.py           # Tool implementations
│   │   ├── prompts.py         # System prompts
│   │   └── README.md          # Documentation
│   └── video_with_references/
│       └── ...
├── tests/
│   ├── test_smart_tag_youtube.py
│   └── test_hackernews_analyzer.py
└── sessions/
    ├── session_2025_01_07.pkl    # IPython variables
    └── session_2025_01_08.pkl
```

**Loading Learned Skills**:
```python
def load_learned_skills():
    """Load all learned functions and agents on startup"""

    # Load functions into IPython
    functions_dir = Path('learned_skills/functions')
    for filepath in functions_dir.glob('*.py'):
        if filepath.name != '__init__.py':
            with open(filepath) as f:
                code = f.read()
            kernel.run_cell(code)

    # Load agents into registry
    agents_dir = Path('learned_skills/agents')
    for agent_dir in agents_dir.iterdir():
        if agent_dir.is_dir():
            config_path = agent_dir / 'config.py'
            if config_path.exists():
                # Import agent module
                spec = importlib.util.spec_from_file_location(
                    agent_dir.name,
                    config_path
                )
                module = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(module)

                # Register agent
                SUBAGENT_REGISTRY[agent_dir.name] = module.agent
```

## Data Flow

### Example: Process 10 YouTube Videos

```
1. User Request
   └─> Coordinator Agent

2. Coordinator: Load data into IPython
   └─> execute_python("""
       urls = ['url1', ..., 'url10']
       transcripts = {}
       for i, url in enumerate(urls):
           transcripts[f'video_{i}'] = fetch_transcript(url)
       """)
   └─> IPython Kernel
       └─> Variables: transcripts = {'video_0': 'transcript...', ...}
       └─> Data stays in IPython (NOT in coordinator context)

3. Coordinator: Delegate to sub-agent (Loop 10 times)
   └─> call_subagent('youtube_tagger', 'transcripts["video_0"]')
   └─> Extract transcript from IPython
   └─> YouTube Tagger Sub-Agent
       └─> Fresh context with only this transcript
       └─> Returns: ['AI', 'ML', 'Python']
       └─> Context destroyed
   └─> Store result back in IPython
       └─> execute_python('results["video_0"] = ["AI", "ML", "Python"]')

4. Coordinator: Generate summary
   └─> execute_python("""
       summary = {
           'total': len(results),
           'unique_tags': set(tag for tags in results.values() for tag in tags)
       }
       print(summary)
       """)
   └─> Return summary to user (NOT all transcripts)

Token Usage:
- Coordinator context: ~4K tokens (constant)
- Sub-agent calls: 10 × ~6K = 60K tokens (temporary)
- Total: ~64K tokens
- vs Traditional: 500K+ tokens (all transcripts in context)
```

### Example: Learn New Function

```
1. User: "I keep doing this pattern, save it"
   └─> Coordinator Agent

2. Coordinator: Generate function
   └─> generate_function(
       name='smart_tag_youtube',
       description='Fetch transcript, extract keywords, tag',
       example='tags = smart_tag_youtube("url")'
   )

3. Code Generator Agent
   └─> Writes Python code with type hints, docstrings
   └─> Returns code

4. Save to file
   └─> learned_skills/functions/smart_tag_youtube.py

5. Generate tests
   └─> generate_tests('learned_skills/functions/smart_tag_youtube.py')

6. Test Generator Agent
   └─> Writes pytest tests
   └─> Returns test code

7. Run tests
   └─> pytest learned_skills/tests/test_smart_tag_youtube.py

8. Review code
   └─> review_generated_code('learned_skills/functions/smart_tag_youtube.py')

9. Code Reviewer Agent
   └─> Analyzes code
   └─> Returns: "✓ Looks good. Minor: add type hint for return"

10. Load into IPython
    └─> kernel.run_cell(open('learned_skills/functions/smart_tag_youtube.py').read())

11. Function now available
    └─> execute_python("tags = smart_tag_youtube('new_url')")
```

## Security Architecture

### Sandboxing Strategy

**Import Restrictions**:
```python
ALLOWED_IMPORTS = {
    'pandas', 'numpy', 'scipy', 'matplotlib',
    'datetime', 'json', 'collections', 're',
    # ... data science libraries
}

BLOCKED_IMPORTS = {
    'subprocess', 'os.system', 'eval', 'exec',
    'compile', '__import__', 'open',  # controlled separately
}

# Custom import hook
def safe_import(name, *args, **kwargs):
    if name in BLOCKED_IMPORTS:
        raise ImportError(f"Import of '{name}' is not allowed")
    if name not in ALLOWED_IMPORTS:
        raise ImportError(f"Import of '{name}' requires approval")
    return original_import(name, *args, **kwargs)

builtins.__import__ = safe_import
```

**Filesystem Access**:
```python
# Only allow read from specific directories
ALLOWED_READ_DIRS = [
    'learned_skills/',
    'data/',
]

ALLOWED_WRITE_DIRS = [
    'learned_skills/functions/',
    'learned_skills/agents/',
    'learned_skills/tests/',
    'learned_skills/sessions/',
]
```

**Execution Limits**:
```python
import signal

def timeout_handler(signum, frame):
    raise TimeoutError("Code execution exceeded time limit")

def execute_with_timeout(code: str, timeout: int = 60):
    signal.signal(signal.SIGALRM, timeout_handler)
    signal.alarm(timeout)
    try:
        result = kernel.run_cell(code)
    finally:
        signal.alarm(0)
    return result
```

## Performance Considerations

### IPython Kernel Caching
- Initialize once per session (not per request)
- Reuse kernel across multiple code executions
- Amortize startup cost

### Tool Discovery Optimization
- Index tool registry by tags for fast lookup
- Cache search results (with invalidation)
- Consider semantic search for better matching

### Sub-Agent Call Optimization
- Lazy loading of sub-agent models
- Connection pooling for API calls
- Parallel sub-agent calls when independent

### State Persistence
- Incremental saves (not full state every time)
- Compress session files
- Purge old sessions automatically

## Error Handling

### Code Execution Errors
```python
try:
    result = kernel.run_cell(code)
except TimeoutError:
    return "Error: Code execution timed out (>60s)"
except MemoryError:
    return "Error: Code exceeded memory limits"
except Exception as e:
    return f"Error: {type(e).__name__}: {str(e)}"
```

### Sub-Agent Failures
```python
def call_subagent_with_retry(agent_name, variable_name, max_retries=3):
    for attempt in range(max_retries):
        try:
            return call_subagent(agent_name, variable_name)
        except Exception as e:
            if attempt == max_retries - 1:
                return f"Error after {max_retries} attempts: {e}"
            time.sleep(2 ** attempt)  # Exponential backoff
```

### Code Generation Failures
```python
def generate_function_with_validation(name, description, example):
    # Generate code
    code = code_generator.run_sync(...)

    # Validate syntax
    try:
        compile(code, '<string>', 'exec')
    except SyntaxError as e:
        # Retry with error feedback
        code = code_generator.run_sync(
            f"{original_prompt}\n\nFix syntax error: {e}"
        )

    # Review code
    review = review_generated_code(code)
    if 'CRITICAL' in review or 'HIGH' in review:
        # Retry with review feedback
        code = code_generator.run_sync(
            f"{original_prompt}\n\nAddress issues: {review}"
        )

    return code
```

## Scalability

### Horizontal Scaling
- Each user gets their own IPython kernel (isolated)
- Sub-agents can run on separate workers
- Code generation agents can be load-balanced

### Vertical Scaling
- IPython kernel memory grows with data
- Monitor memory usage, suggest cleanup
- Automatic garbage collection of old variables

### Long-Running Sessions
- Auto-save state every N operations
- Checkpoint mechanism for recovery
- Suggest session reset when memory high

## Monitoring and Observability

### Metrics to Track
- Token usage per request
- Token savings from IPython usage
- Sub-agent call frequency
- Code generation success rate
- Test pass rate
- Code review issue rate
- Session load time
- Average code execution time

### Logging
- All code executions logged
- Sub-agent calls logged with context size
- Code generation events logged
- Errors and retries logged

### Debugging
- Save execution history for replay
- IPython state snapshots for debugging
- Sub-agent conversation logs (when needed)

## Future Enhancements

### Phase 2+
- Semantic tool search (embeddings)
- Parallel sub-agent execution
- Distributed IPython kernels
- Web UI for viewing learned skills
- A/B testing of generated code variants
- Automatic performance profiling
- Cost optimization recommendations
- Multi-session collaboration

### Research Directions
- Meta-learning: Agent learns how to learn better
- Self-modification: Agent improves its own prompts
- Curriculum learning: Progressive skill building
- Transfer learning: Apply skills to new domains
