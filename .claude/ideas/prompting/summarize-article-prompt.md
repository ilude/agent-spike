# Article Summarization Prompt - Enhanced for Actionable Content

## Purpose
Evaluate articles for actionable technical content vs. marketing hype, then create implementation-focused summaries that preserve all details needed to replicate techniques.

## Content Quality Assessment

First, evaluate if this article contains actionable information:

### Check for these RED FLAGS (marketing/hype article):
- Repeated mentions of specific products/platforms (especially enterprise vendors)
- Personal narrative style ("I thought... then I realized...")
- Market projections and growth statistics without implementation details
- Case studies without technical specifics
- Buzzword density without concrete definitions
- Zero code examples, architecture patterns, or technical frameworks
- No failure modes, debugging approaches, or limitations discussed
- Lacks "how to actually do this" guidance

### Check for these GREEN FLAGS (actionable content):
- Specific implementation steps or code examples
- Architecture patterns or design principles
- Tool/library/framework comparisons with tradeoffs
- Concrete techniques or methodologies
- Failure modes and mitigation strategies
- Clear technical constraints or boundaries
- Reproducible examples or experiments

## Output Format

### If 3+ red flags and <2 green flags: Flag as marketing content

```markdown
Assessment: Marketing/hype article - no actionable technical content

One-sentence summary: [What it's actually about]

Only useful insight (if any): [Single actionable takeaway, or "None"]

Recommendation: Skip - no implementation value
```

### If 2+ green flags: Proceed with full summary

**CRITICAL for actionable content**: Preserve ALL implementation details including:
- Exact tool names, commands, and syntax
- Specific version numbers or configuration details
- Complete code examples (don't truncate)
- Platform/service names and URLs
- Specific parameters, flags, or options
- Error messages or debugging approaches
- Alternative approaches or tools mentioned
- Exact file paths, API endpoints, or data structures
- Numerical values (timeouts, thresholds, limits)

**What NOT to preserve**:
- Marketing language or superlatives
- Author anecdotes unless they reveal technical insights
- Excessive background context
- Redundant explanations of common concepts

Use this structure:

---

# [Main Topic/Technique Name]

## The Problem
What issue or challenge does this address? (2-3 sentences max)

**Include**: Specific constraints, scale issues, or failure modes being addressed

## The Solution
What is the proposed solution or key finding?

**For highly actionable content**: Provide overview here, save detailed steps for Implementation section

**Include**:
- Core approach or methodology name
- Key components or phases
- Example scenario or use case (if provided)

## Why It Works
Brief explanation of the underlying mechanism or reasoning. (2-3 sentences)

**Include**:
- Technical principles exploited
- Why alternatives fail
- Critical success factors

## Results
Key metrics, findings, or performance improvements

**Format as bullet points**:
- Quantitative results (before/after, benchmarks)
- Qualitative improvements
- Limitations or caveats discovered

**Example**:
- Response time: 500ms → 50ms (10x improvement)
- Cost reduction: $1,350/day → $30/day (via caching)
- Limitation: Only works for articles, not web apps

## How to Use / Implementation

**This is the CRITICAL section for actionable content**

### For technique/methodology articles:
- **Break down into phases or steps**
- **Preserve exact commands, syntax, and tool names**
- **Include alternative tools or approaches mentioned**
- **Show example inputs and expected outputs**
- **Document configuration requirements**

**Example structure**:
```markdown
### Phase 1: [Name]

**Goal**: [What this achieves]

**Tools**:
- Tool A (primary use case)
- Tool B (alternative for X scenario)

**Command**:
\```bash
exact-command --with-flags input.txt
\```

**Example Results**:
- Finding 1: [Specific result]
- Finding 2: [Another specific result]

**Next Steps**: [How this feeds into next phase]
```

### For code/library articles:
- **Include complete code examples**
- **Preserve import statements and dependencies**
- **Show configuration/setup steps**
- **Include error handling patterns**

### For architecture/design articles:
- **Describe components and their relationships**
- **Include diagrams or ASCII art if helpful**
- **List specific technologies or services used**
- **Document tradeoffs and decision factors**

## Common Mistakes & Edge Cases

**Only include if article discusses**:
- OPSEC failures or security issues discovered
- Edge cases that break the technique
- Common implementation errors
- Debugging approaches

**Format**:
```markdown
### Mistake 1: [Description]
- **Problem**: [What went wrong]
- **Exposure/Impact**: [Consequences]
- **Prevention**: [How to avoid]
```

## Tools & Techniques Reference

**For articles with multiple tools, create quick reference**:

```markdown
### Tool Categories

**[Category Name]**:
- **Tool A** - [Primary use case]
  \```bash
  tool-a --example command
  \```
- **Tool B** - [When to use instead]
  \```bash
  tool-b --different-syntax
  \```

**Pro Tips**:
- [Specific advice from article]
```

## Implementation Checklist

**For workflow/process articles, create actionable checklist**:

```markdown
### [Phase Name] Checklist

- [ ] Step 1 with specific action
- [ ] Step 2 with tool name
- [ ] Step 3 with expected output
```

## Critical Success Factors

**Bullet list of key requirements for success**:
- [Factor 1 - be specific]
- [Factor 2 - include numbers/thresholds if mentioned]

## Source
[Link to original paper/article/resource]

## File Name
Suggest a filename using lowercase with hyphens, based on the main topic/technique

**Format**: `[main-concept]-[type].md`

**Examples**:
- `scary-osint-analyst-methodology.md`
- `verbalized-sampling-summary.md`
- `rag-performance-optimization.md`
- `agent-coordination-patterns.md`

---

## Summary Quality Checklist

Before finalizing, verify:

**For ALL summaries**:
- [ ] Problem clearly stated (2-3 sentences max)
- [ ] Solution overview provided
- [ ] Why It Works explains mechanism
- [ ] Results section has specific metrics or findings
- [ ] Source link included
- [ ] Filename suggested

**For ACTIONABLE summaries (2+ green flags)**:
- [ ] All tool names preserved exactly
- [ ] Commands/code include exact syntax
- [ ] Step-by-step process documented
- [ ] Alternative approaches mentioned
- [ ] Configuration details included
- [ ] Example inputs/outputs shown
- [ ] Limitations or edge cases noted
- [ ] Implementation checklist provided (if workflow/process article)
- [ ] No truncation of technical details
- [ ] Someone could replicate the technique from this summary alone

**For MARKETING summaries (<2 green flags)**:
- [ ] Flagged as marketing/hype
- [ ] One-sentence summary captures essence
- [ ] Single useful insight extracted (or "None")
- [ ] Skip recommendation provided

## Guidelines for Edge Cases

### Research Papers
- Include methodology details
- Preserve experimental setup
- Include baseline comparisons
- Note reproducibility details (datasets, code availability)

### Tutorial/How-To Articles
- Complete step-by-step preservation
- Include troubleshooting sections
- Preserve screenshots/diagrams descriptions
- Include prerequisite requirements

### Architecture/Design Articles
- Document component interactions
- Include technology stack details
- Preserve scaling considerations
- Note deployment requirements

### Tool Comparison Articles
- Create comparison matrix if helpful
- Include specific version numbers tested
- Preserve benchmark methodology
- Document test environment specs
