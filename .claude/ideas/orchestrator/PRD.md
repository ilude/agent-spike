# Product Requirements Document: Self-Evolving Orchestrator Agent

**Version**: 0.1.0
**Date**: 2025-01-07
**Status**: Design Phase

## 1. Problem Statement

### Current Limitations

**Context Window Bloat**
- Traditional MCP agents load all tool definitions upfront (150K+ tokens)
- Intermediate data flows through LLM context repeatedly
- Expensive and hits context limits quickly

**Stateless Operations**
- Each tool call is independent
- Large datasets must be passed through context
- No persistent working memory

**Limited Adaptability**
- Fixed set of tools and agents
- Cannot learn from experience
- No capability to create new specialized tools

**Sub-Optimal Token Usage**
- Full transcripts/documents passed to LLM even when only summary needed
- Monolithic agent holds all data in context
- Context grows unbounded with conversation length

## 2. Solution Overview

A **self-evolving orchestrator agent** that:

1. Uses **IPython kernel** as persistent working memory
2. Writes **code to orchestrate tools** instead of direct tool calls
3. **Progressively discovers** tools as needed
4. **Delegates to specialized sub-agents** with isolated contexts
5. **Generates new code** (functions and agents) saved as Python files
6. **Self-improves** by learning patterns and creating reusable capabilities

## 3. User Stories

### As a user, I want to...

**US-1: Process Large Datasets Efficiently**
- Process 100 YouTube video transcripts without context overflow
- System should keep data in memory, not LLM context
- Only summaries/results returned to me

**US-2: Reuse Learned Patterns**
- After teaching system a workflow once, it should remember
- System should create reusable functions automatically
- Next time, just call the learned function

**US-3: Delegate to Specialists**
- Complex tasks should use specialized sub-agents
- Each specialist should have focused, temporary context
- Results combined by orchestrator

**US-4: Self-Improvement**
- System should identify inefficient patterns
- Generate optimized functions automatically
- Test and validate generated code

**US-5: Transparency**
- View all learned functions as readable Python files
- Review generated code before deployment
- Edit or improve generated code manually

**US-6: Resume Previous Work**
- Load previous session with all learned capabilities
- Access variables from previous session
- Continue where I left off

## 4. Core Features

### 4.1 Stateful IPython Execution

**Description**: Persistent IPython kernel as working memory

**Requirements**:
- FR-1.1: Initialize IPython kernel once per session
- FR-1.2: Execute Python code in persistent environment
- FR-1.3: Variables persist across multiple executions
- FR-1.4: Support standard data science libraries (pandas, numpy, etc.)
- FR-1.5: Return execution results and stdout to orchestrator
- FR-1.6: Handle execution errors gracefully

**Success Metrics**:
- Data loaded once, reused N times without reloading
- Memory usage stays constant (not growing with conversation)

### 4.2 Progressive Tool Discovery

**Description**: Load tool definitions only as needed

**Requirements**:
- FR-2.1: `search_tools(query)` finds relevant tools
- FR-2.2: Tool registry contains all available functions
- FR-2.3: Search supports keyword matching
- FR-2.4: Search returns function signatures and documentation
- FR-2.5: Only 2 meta-tools loaded initially (~500 tokens)
- FR-2.6: (Future) Semantic search using embeddings

**Success Metrics**:
- Initial context: <2K tokens (vs 150K traditional)
- Tool definitions loaded on-demand
- 98%+ reduction in upfront token usage

### 4.3 Code Execution

**Description**: Execute generated Python code in sandbox

**Requirements**:
- FR-3.1: `execute_python(code)` runs in IPython kernel
- FR-3.2: Sandboxed execution (restricted imports/operations)
- FR-3.3: Access to tool registry functions
- FR-3.4: Return both stdout and last expression value
- FR-3.5: Capture and report errors
- FR-3.6: Timeout protection (prevent infinite loops)

**Success Metrics**:
- Code execution latency <1s for simple operations
- Security: No access to filesystem outside allowed directories
- Reliability: 99%+ execution success rate

### 4.4 Sub-Agent Delegation

**Description**: Call specialized agents with isolated contexts

**Requirements**:
- FR-4.1: `call_subagent(name, variable_name)` delegates to specialist
- FR-4.2: Extract data from IPython environment
- FR-4.3: Create fresh context for sub-agent (no history)
- FR-4.4: Pass only necessary data to sub-agent
- FR-4.5: Sub-agent context destroyed after completion
- FR-4.6: Return sub-agent result to orchestrator
- FR-4.7: Store result back in IPython environment

**Success Metrics**:
- Sub-agent context: <10K tokens per call
- Context isolation: No memory leaks between calls
- Token efficiency: 90%+ reduction vs monolithic agent

### 4.5 Code Generation (Functions)

**Description**: Generate reusable Python functions

**Requirements**:
- FR-5.1: `generate_function(name, description, examples)` creates function
- FR-5.2: Code generator sub-agent writes function code
- FR-5.3: Save to `learned_skills/functions/{name}.py`
- FR-5.4: Include type hints and docstrings
- FR-5.5: Load immediately into IPython environment
- FR-5.6: Version tracking in file header

**Success Metrics**:
- Generated code passes review 90%+ of time
- Functions are syntactically valid 100%
- Human-readable and maintainable code

### 4.6 Code Generation (Agents)

**Description**: Generate new specialized sub-agents

**Requirements**:
- FR-6.1: `generate_subagent(name, purpose, tools)` creates agent
- FR-6.2: Agent generator sub-agent writes complete agent
- FR-6.3: Generate directory structure: config.py, tools.py, prompts.py, README.md
- FR-6.4: Save to `learned_skills/agents/{name}/`
- FR-6.5: Register agent in SUBAGENT_REGISTRY
- FR-6.6: Agent immediately available for use

**Success Metrics**:
- Generated agents work on first try 80%+ of time
- Complete agent structure (all files present)

### 4.7 Code Testing

**Description**: Generate and run tests for generated code

**Requirements**:
- FR-7.1: `generate_tests(filepath)` creates pytest tests
- FR-7.2: Test generator sub-agent writes comprehensive tests
- FR-7.3: Save to `learned_skills/tests/test_{name}.py`
- FR-7.4: Run tests immediately after generation
- FR-7.5: Report test results to orchestrator
- FR-7.6: Support for mocking external dependencies

**Success Metrics**:
- Generated tests achieve 80%+ code coverage
- Tests identify bugs before deployment

### 4.8 Code Review

**Description**: Review generated code before deployment

**Requirements**:
- FR-8.1: `review_generated_code(filepath)` analyzes code
- FR-8.2: Code reviewer sub-agent checks correctness, security, style
- FR-8.3: Return list of issues with severity levels
- FR-8.4: Suggest specific improvements
- FR-8.5: Support iterative refinement (re-generate with feedback)

**Success Metrics**:
- Identify security issues 95%+ of time
- Identify correctness issues 90%+ of time

### 4.9 State Inspection

**Description**: Orchestrator can inspect IPython state

**Requirements**:
- FR-9.1: `list_variables()` shows all variables with types
- FR-9.2: `inspect_variable(name)` shows details without full data
- FR-9.3: For DataFrames: shape, columns, head
- FR-9.4: For dicts/lists: length, keys/items preview
- FR-9.5: For large objects: summary statistics only

**Success Metrics**:
- State inspection returns <1K tokens
- Orchestrator can make informed decisions about data

### 4.10 Session Persistence

**Description**: Save and restore sessions

**Requirements**:
- FR-10.1: `save_session_state(name)` persists session
- FR-10.2: Save IPython variables (using pickle for data)
- FR-10.3: Save references to learned functions/agents (file paths)
- FR-10.4: `load_session_state(name)` restores session
- FR-10.5: Reload all learned functions from files
- FR-10.6: Re-register all learned agents

**Success Metrics**:
- Session restore time <5s
- 100% of learned capabilities restored

### 4.11 Self-Analysis

**Description**: System analyzes its own performance

**Requirements**:
- FR-11.1: Track execution history (code patterns, frequency)
- FR-11.2: Identify repeated patterns worth automating
- FR-11.3: Calculate token savings from learned functions
- FR-11.4: Suggest optimizations to user
- FR-11.5: Auto-generate functions for common patterns (with approval)

**Success Metrics**:
- Identify 90%+ of repeated patterns
- Token savings compound over time

## 5. Technical Requirements

### 5.1 Security

- SEC-1: Sandboxed code execution (no arbitrary filesystem access)
- SEC-2: No network access from executed code (except via approved tools)
- SEC-3: Import restrictions (no `subprocess`, `eval`, etc.)
- SEC-4: Timeout limits (max 60s per execution)
- SEC-5: Memory limits (prevent OOM)
- SEC-6: Code review before automatic execution

### 5.2 Performance

- PERF-1: IPython kernel startup <1s
- PERF-2: Code execution latency <2s for typical operations
- PERF-3: Tool discovery <500ms
- PERF-4: Sub-agent delegation <5s per call
- PERF-5: Session save/load <5s

### 5.3 Reliability

- REL-1: Handle execution errors gracefully (no crashes)
- REL-2: Automatic retry on transient failures
- REL-3: Validate generated code syntax before execution
- REL-4: Graceful degradation if sub-agent unavailable

### 5.4 Maintainability

- MAINT-1: All generated code PEP 8 compliant
- MAINT-2: Type hints on all generated functions
- MAINT-3: Comprehensive docstrings
- MAINT-4: Version tracking in file headers
- MAINT-5: README for each generated agent

## 6. Directory Structure

```
learned_skills/
├── functions/
│   ├── __init__.py
│   ├── smart_tag_youtube.py
│   ├── batch_process_videos.py
│   └── ...
├── agents/
│   ├── hackernews_analyzer/
│   │   ├── __init__.py
│   │   ├── config.py
│   │   ├── tools.py
│   │   ├── prompts.py
│   │   └── README.md
│   └── ...
├── tests/
│   ├── test_smart_tag_youtube.py
│   └── ...
└── sessions/
    ├── session_2025_01_07.pkl
    └── ...
```

## 7. Success Metrics

### Token Efficiency
- **Baseline**: Traditional MCP = 150K initial + data through context
- **Target**: <2K initial + data in IPython (98%+ reduction)

### Context Usage Per Task
- **Baseline**: 50K tokens per task (with data)
- **Target**: 5K tokens per task (90% reduction)

### Capability Growth
- Week 1: 5 learned functions, 2 learned agents
- Week 4: 20 learned functions, 5 learned agents
- Week 12: 50+ learned functions, 10+ learned agents

### Code Quality
- Generated code passes review: 90%+
- Generated tests catch bugs: 85%+
- Human edit rate: <20% (most code used as-is)

### User Satisfaction
- Users can resume work easily: 95%+
- System learns patterns: 90%+ success
- Transparent and understandable: 85%+

## 8. Risks and Mitigations

### Risk: Generated Code Security
- **Impact**: High (code execution vulnerabilities)
- **Mitigation**: Mandatory code review, sandboxing, import restrictions

### Risk: IPython State Corruption
- **Impact**: Medium (loss of working data)
- **Mitigation**: Auto-save state periodically, easy reset mechanism

### Risk: Code Generation Quality
- **Impact**: Medium (unreliable generated functions)
- **Mitigation**: Test generation, code review, iterative refinement

### Risk: Sub-Agent Context Leakage
- **Impact**: Medium (privacy, token waste)
- **Mitigation**: Explicit context isolation, no shared history

### Risk: Performance Overhead
- **Impact**: Low (slower than direct tool calls)
- **Mitigation**: IPython persistent kernel (no repeated startup), caching

## 9. Non-Goals (Out of Scope)

- NOT building a full IDE or notebook interface
- NOT replacing Pydantic AI (building on top of it)
- NOT supporting multi-user sessions (single-user for now)
- NOT distributed execution across machines
- NOT real-time collaboration

## 10. Open Questions

1. **Sandbox technology**: RestrictedPython vs subprocess vs containers?
2. **Code generation model**: Use Sonnet for quality or Haiku for cost?
3. **Session storage**: Where to store session files? How long to keep?
4. **Approval workflow**: Auto-execute generated code or require human approval?
5. **Error recovery**: How many retries? When to ask human for help?
6. **Tool registry**: Pre-populate with lessons 001-003 agents, or start empty?

## 11. Timeline (Tentative)

### Phase 1: Core Infrastructure (Lesson 004-A)
- IPython kernel integration
- Basic code execution
- Progressive tool discovery
- Variable inspection

### Phase 2: Sub-Agent Delegation (Lesson 004-B)
- Sub-agent calling mechanism
- Context isolation
- Integration with lessons 001-003

### Phase 3: Code Generation (Lesson 004-C)
- Code generator sub-agent
- Function generation and saving
- Test generator sub-agent
- Code reviewer sub-agent

### Phase 4: Self-Evolution (Lesson 004-D)
- Agent generator sub-agent
- Pattern recognition
- Self-analysis and optimization
- Session persistence

### Phase 5: Polish and Documentation (Lesson 004-E)
- Error handling improvements
- Comprehensive testing
- User documentation
- Examples and tutorials

## 12. Appendix: Comparison with Existing Approaches

See [COMPARISON.md](./COMPARISON.md) for detailed comparison with:
- Traditional MCP
- Cloudflare Code Mode
- Data Analytics Agent
- Current lessons 001-003
