# Design Decisions and Open Questions

**Version**: 0.1.0
**Date**: 2025-01-07

## Key Design Decisions

### 1. Why IPython Instead of Plain Python exec()?

**Decision**: Use IPython.core.interactiveshell

**Reasoning**:
- ✅ **Persistent state**: Variables survive across executions
- ✅ **Better error handling**: Rich error messages, stack traces
- ✅ **Magic commands**: Access to %timeit, %load, etc. if needed
- ✅ **Display system**: Can handle rich outputs (DataFrames, plots)
- ✅ **History**: Can inspect previous executions
- ✅ **Mature**: Battle-tested in Jupyter ecosystem

**Alternatives Considered**:
- `exec()` with custom globals dict: Too primitive, no state management
- Full Jupyter kernel: Too heavy, unnecessary overhead
- RestrictedPython: Good for sandboxing but lacks state persistence

### 2. Why Python Files Instead of Pickle?

**Decision**: Save generated code as .py files, not pickle

**Reasoning**:
- ✅ **Transparency**: Human-readable, inspectable
- ✅ **Version control**: Git diffs show what changed
- ✅ **Security**: No pickle deserialization vulnerabilities
- ✅ **Editability**: Humans can improve generated code
- ✅ **Portability**: Works across Python versions
- ✅ **Testing**: Can write proper unit tests

**Use Pickle For**:
- ⚠️ Session state (IPython variables): DataFrames, large objects
- ⚠️ Temporary data only (not code)

**Never Pickle**:
- ❌ Function definitions
- ❌ Agent configurations
- ❌ Long-term storage

### 3. Why Sub-Agents Instead of Monolithic?

**Decision**: Coordinator delegates to specialized sub-agents

**Reasoning**:
- ✅ **Context isolation**: Each sub-agent has focused, temporary context
- ✅ **Budget efficiency**: Only pay for context needed for specific task
- ✅ **Specialization**: Tuned prompts for specific domains
- ✅ **Reusability**: Same sub-agent for many tasks
- ✅ **Testing**: Can test sub-agents independently
- ✅ **Model selection**: Use Haiku for simple tasks, Sonnet for complex

**Tradeoff**: More API calls, but each cheaper

### 4. Why Code Generation for Evolution?

**Decision**: Generate Python files instead of programmatic tool registration

**Reasoning**:
- ✅ **Transparency**: See exactly what was generated
- ✅ **Review before use**: Human can approve/reject
- ✅ **Version tracking**: Git history of learned skills
- ✅ **Composition**: Generated code can use other generated code
- ✅ **Documentation**: README and docstrings explain what/why

**Alternatives Considered**:
- Dynamic tool registration: Less transparent, harder to debug
- Prompt engineering only: Doesn't persist across sessions
- Fine-tuning: Too slow, expensive, opaque

### 5. Why Separate Code Generator Sub-Agents?

**Decision**: Dedicated agents for code gen, test gen, review, agent gen

**Reasoning**:
- ✅ **Better prompts**: Each focused on specific task
- ✅ **Better model choice**: Can use Sonnet for quality
- ✅ **Iterative refinement**: Coordinator can retry with feedback
- ✅ **Testability**: Can evaluate each independently
- ✅ **Quality gates**: Review before deployment

**Agent Specializations**:
- **Code Generator**: Write functions (use Sonnet for quality)
- **Test Generator**: Write pytest tests (comprehensive coverage)
- **Code Reviewer**: Catch bugs/security issues (critical path)
- **Agent Generator**: Create complete sub-agents (complex task)

### 6. Why Progressive Tool Discovery?

**Decision**: search_tools() instead of loading all upfront

**Reasoning**:
- ✅ **Token efficiency**: Load only what's needed
- ✅ **Scalability**: Can have 1000s of tools without context bloat
- ✅ **Flexibility**: Easy to add new tools without reconfiguration
- ✅ **Semantic search**: (Future) Find tools by meaning, not just name

**Implementation**:
- Phase 1: Simple keyword matching
- Phase 2: Embeddings for semantic search
- Phase 3: Usage-based ranking (popular tools first)

---

## Open Questions

### Q1: Sandbox Technology Choice?

**Options**:
1. **IPython with import restrictions** (Phase 1)
   - Pros: Simple, fast, already using IPython
   - Cons: Not as secure, Python-level restrictions only

2. **RestrictedPython** (Phase 2)
   - Pros: Designed for sandboxing, compile-time checks
   - Cons: Limited functionality, some libraries won't work

3. **Subprocess with resource limits** (Phase 3)
   - Pros: Strong isolation, kernel-level limits
   - Cons: Slower startup, complexity

4. **Docker containers** (Future)
   - Pros: Maximum isolation, reproducible
   - Cons: Heavy overhead, slow startup

**Recommendation**: Start with IPython + import restrictions, add layers as needed

**Decision needed**: What level of security is required for MVP?

### Q2: Approval Workflow for Generated Code?

**Options**:
1. **Fully automatic** (execute immediately)
   - Fast but risky

2. **Automatic with review** (review + auto-fix issues)
   - Balanced approach

3. **Manual approval** (human reviews every generation)
   - Safe but slow

4. **Trust-based** (automatic for simple, manual for complex)
   - Adapts to risk level

**Recommendation**: Start with #2 (automatic with review), add #4 (trust-based) later

**Decision needed**: What's acceptable risk tolerance?

### Q3: Session Storage Strategy?

**Options**:
1. **Local files only** (sessions/ directory)
   - Simple but not synced

2. **Cloud storage** (S3, Google Drive)
   - Synced across machines but complexity

3. **Database** (SQLite, PostgreSQL)
   - Queryable but overkill

4. **Hybrid** (local + optional cloud backup)
   - Best of both

**Recommendation**: Start with #1 (local), add #4 (hybrid) later

**Questions**:
- How long to keep sessions? (default 30 days?)
- Max session size? (compress if >100MB?)
- Auto-cleanup old sessions?

### Q4: Error Recovery Strategy?

**Scenarios**:
1. **Code execution error**
   - Retry? How many times?
   - Ask human? When?

2. **Sub-agent failure**
   - Fallback to another agent?
   - Retry with different prompt?

3. **Code generation produces invalid code**
   - Automatic re-generation with error?
   - How many attempts before giving up?

4. **IPython kernel crashes**
   - Restart kernel? Lose state?
   - Auto-save state to prevent loss?

**Recommendation**:
- Code execution: 1 retry, then ask human
- Sub-agent: 3 retries with exponential backoff
- Code generation: 3 attempts with feedback, then ask human
- Kernel crash: Auto-restart + restore from last save

**Decision needed**: Recovery vs. asking human (UX tradeoff)

### Q5: Tool Registry Population?

**Options**:
1. **Start empty** (learn everything)
   - Pure self-evolution but slow start

2. **Pre-populate from lessons** (youtube, webpage tools)
   - Faster start, builds on existing work

3. **Import from MCP servers** (if available)
   - Maximum flexibility

4. **Hybrid** (core tools + learn more)
   - Balanced approach

**Recommendation**: #2 (pre-populate from lessons 001-003), then learn more

**Questions**:
- Which tools to include initially?
- How to organize categories?
- Auto-discover from existing code?

### Q6: Model Selection Strategy?

**For Coordinator**:
- Option A: Sonnet (better reasoning, higher cost)
- Option B: Haiku (faster, cheaper)

**For Sub-Agents**:
- Most: Haiku (simple, focused tasks)
- Complex: Sonnet (e.g., complex analysis)

**For Code Generators**:
- Code Gen: Sonnet (quality matters)
- Test Gen: Sonnet (comprehensive tests)
- Code Review: Sonnet (catch subtle issues)
- Agent Gen: Sonnet (complex task)

**Recommendation**:
- Coordinator: Sonnet (orchestration quality critical)
- Sub-agents: Haiku default, Sonnet for complex
- Code gen: Always Sonnet (generated code used repeatedly)

**Decision needed**: Budget vs. quality tradeoff

### Q7: State Inspection Granularity?

**Options**:
1. **Minimal** (list_variables only)
   - Simple but limited visibility

2. **Basic** (list + inspect_variable)
   - Balanced approach

3. **Detailed** (schema, statistics, samples)
   - Great visibility but more tokens

4. **Query-based** ("show me all DataFrames > 1000 rows")
   - Flexible but complex

**Recommendation**: Start with #2 (basic), add #3 (detailed) later

**Questions**:
- How much detail without bloating context?
- When to use detailed inspection?
- Cost of inspection vs. value?

### Q8: Semantic Search Implementation?

**For tool discovery**:

**Options**:
1. **Keyword only** (simple matching)
   - Fast, simple, but limited

2. **Embeddings** (semantic search)
   - Better matching but cost/complexity

3. **Hybrid** (keyword + semantic)
   - Best of both

**Recommendation**: Start with #1 (keyword), add #2 (embeddings) in Phase 2

**Questions**:
- Which embedding model? (OpenAI, local?)
- When to recompute embeddings?
- Cache embeddings or compute on-demand?

### Q9: Multi-Session Collaboration?

**Scenarios**:
- User on multiple machines
- Multiple users sharing learned skills
- Team environment

**Options**:
1. **Single-user, single-machine** (MVP)
   - Simple, no sync needed

2. **Single-user, multi-machine** (cloud sync)
   - Sync learned_skills via Git or cloud

3. **Multi-user with sharing** (team mode)
   - Shared skill library, isolation for sessions

4. **Full collaboration** (real-time)
   - Complex, out of scope

**Recommendation**: #1 for MVP, #2 for future

**Questions**:
- How to handle conflicts? (Git merge?)
- Privacy concerns? (who sees what?)
- Versioning strategy?

### Q10: Performance Monitoring?

**What to track**:
- Token usage per request
- Token savings (vs traditional)
- Code execution time
- Sub-agent call frequency
- Code generation success rate
- Test pass rate
- User satisfaction

**Options**:
1. **Basic logging** (file-based)
   - Simple but limited analysis

2. **Structured logging** (JSON)
   - Queryable, analyzable

3. **Metrics system** (Prometheus, etc.)
   - Professional but complex

4. **Built-in dashboard** (web UI)
   - Great UX but scope creep

**Recommendation**: Start with #2 (structured logging), add analysis later

**Questions**:
- What metrics matter most?
- When to alert user?
- How to visualize improvements?

---

## Decisions Needed Before Implementation

### Must Decide:
1. ✅ **Sandbox approach** (IPython + restrictions for MVP)
2. ✅ **Code as files** (decided: yes, .py files)
3. ✅ **Sub-agent architecture** (decided: yes, isolated contexts)
4. ⚠️ **Approval workflow** (leaning: automatic with review)
5. ⚠️ **Tool registry** (leaning: pre-populate from lessons)

### Can Decide Later:
6. ⏳ **Session storage** (local files for MVP)
7. ⏳ **Error recovery** (start simple, iterate)
8. ⏳ **Model selection** (Sonnet for coordinator/codegen, Haiku for sub-agents)
9. ⏳ **Semantic search** (Phase 2 feature)
10. ⏳ **Multi-session** (future feature)

---

## Next Steps

1. **Review PRD and Architecture** with stakeholders
2. **Make remaining decisions** (approval workflow, tool registry)
3. **Create lesson-004 plan** (break into phases)
4. **Build Phase 1**: Core orchestrator + IPython execution
5. **Validate approach** before building self-evolution features

---

## Notes and Considerations

### Context Efficiency is Key
- Primary goal: Reduce token usage by 80-90%
- Measure everything: Track token usage rigorously
- Compare with baselines: Lessons 001-003, traditional MCP

### Security Cannot Be Afterthought
- Start with basic sandboxing (import restrictions)
- Code review before execution (at least for MVP)
- Never execute without some validation

### Transparency Builds Trust
- All generated code visible as .py files
- Human can review, edit, approve
- Git history shows evolution

### Start Simple, Iterate
- Don't build everything at once
- Phase 1: Just orchestrator + IPython
- Phase 2: Add sub-agents
- Phase 3: Add code generation
- Phase 4: Add self-evolution

### Build on Existing Work
- Leverage lessons 001-003 as sub-agents
- Use proven patterns (Pydantic AI, Typer CLIs)
- Familiar tech stack (Python, uv, Claude)

### Learning Project First
- This is lesson-004, not production
- Focus on proving concepts
- Document learnings in COMPLETE.md
- Production hardening comes later

---

## References

- [Anthropic: Code Execution with MCP](https://www.anthropic.com/engineering/code-execution-with-mcp)
- [Cloudflare: Code Mode](https://blog.cloudflare.com/code-mode/)
- [Data Analytics Agent](https://github.com/agency-ai-solutions/data-analytics-agent)
- Lessons 001-003 (this project)
- IPython documentation
- Pydantic AI documentation
