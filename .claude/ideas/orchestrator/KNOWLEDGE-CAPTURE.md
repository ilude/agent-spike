# Knowledge Capture System Design: Content → Application Workflows

> Expert knowledge management and AI system design for capturing and utilizing "content → application" workflows.

## Context

- **Project**: agent-spike (multi-agent AI learning project)
- **Document**: .claude/VISION.md describes a goal (#4) to "Suggest applications of learned concepts to active projects"
- **Current situation**: A workflow just occurred that exemplifies this goal:
  1. External content discovered (YouTube video: https://www.youtube.com/watch?v=D4ImbDGFgIM about MCP vs code-execution)
  2. Discussion with AI assistant to extract concepts
  3. Brainstorming how concepts apply to agent-spike project
  4. Result: New experiment (orchestrator pattern) directly inspired by the video

## Task

Design the optimal system for capturing and utilizing these "content → application" workflows.

---

## Part 1: Meta-Prompt Design

### Essential Context Questions

#### What information is essential to preserve?

Core capture elements:
- **Source**: URL, title, author, publication date, content type (video/article/paper)
- **Discovery**: Date discovered, how found (search? recommendation? serendipity?)
- **Concepts**: Key ideas extracted (bullet points, not full transcript)
- **Applications**: How concepts map to this project (specific lessons, problems solved)
- **Artifacts**: What was created (documentation, code, lessons)
- **Outcomes**: Git commits, files created, decisions made
- **Inspiration Score**: How impactful was this? (1-5 scale)
- **Status**: Captured? Discussed? Applied? Implemented? Completed?

#### Who/what will use this information later?

Multiple consumers:
1. **Human (immediate)**: Quick reference during development
2. **Human (reflective)**: Pattern recognition across months/years
3. **AI Recommender (Lesson 011)**: Find similar content, suggest applications
4. **New collaborators**: Understand project evolution and influences
5. **Documentation system**: Auto-generate "Inspired by" sections

#### What future queries should this enable?

Query types:
- "What inspired lesson X?"
- "Show me all content about [MCP/agents/code-execution]"
- "What content have I captured but not applied?"
- "Find content similar to this new article"
- "What patterns exist in how I apply external ideas?"
- "Timeline of project influences"
- "Which sources were most impactful?"

#### How does this integrate with existing project documentation?

Integration points:
- **VISION.md**: Links from Goal #4 to inspiration log
- **STATUS.md**: Current work references inspiration
- **Lesson READMEs**: "Inspired by" section with link
- **Git commits**: Reference inspiration IDs in commit messages
- **.claude/ideas/**: Detailed explorations link back to source

### Output Format Questions

#### Optimal format: Hybrid approach

```
inspirations/
├── INDEX.md                     # Human-readable timeline and overview
├── inspirations.json            # Machine-readable structured data
├── by-lesson/
│   ├── lesson-009-link.md      # Symlinks or references
│   └── ...
├── by-topic/
│   ├── mcp.md                  # Grouped by theme
│   ├── code-execution.md
│   └── ...
└── 2025/
    ├── 2025-01-07-mcp-vs-code-execution.md  # Detailed capture
    └── ...
```

**Rationale:**
- **INDEX.md**: Human scanning, quick overview
- **inspirations.json**: AI/automation queries, consistent schema
- **by-lesson/**: Direct project connections
- **by-topic/**: Pattern recognition, related content
- **Timestamped files**: Full context preservation

### Reasoning & Verification

#### What makes a "good" capture different from "poor"?

**Good capture:**
- ✅ Captures WHY, not just WHAT (motivation, problem solved)
- ✅ Links to concrete outcomes (commits, files, lessons)
- ✅ Enough detail to recreate thinking process
- ✅ Machine-queryable but human-readable
- ✅ Takes 5-10 minutes to create, saves hours later

**Poor capture:**
- ❌ Just bookmarks without context
- ❌ Too detailed (copy-paste entire article)
- ❌ No connection to project actions
- ❌ Inconsistent format (can't be queried)
- ❌ Never updated with outcomes

#### How will we know if this system is working 6 months from now?

**Success indicators:**
- Used weekly (not gathering dust)
- Enables AI recommender (Lesson 011) with real queries
- New lessons reference inspirations naturally
- Collaborators understand project influences
- Patterns emerge (e.g., "We often apply X concept to Y problem")

**Failure indicators:**
- Last update was 4 months ago
- Format changed 3 times (inconsistency)
- Only captures 20% of actual influences
- Too much overhead to maintain

#### What are the failure modes?

1. **Over-documentation**: Every YouTube video captured in excruciating detail → maintenance burden → abandonment
2. **Under-documentation**: Just URLs → lose context → can't remember why it mattered
3. **Inconsistent format**: Different structure each time → can't query → AI agents can't use
4. **Disconnected from workflow**: Separate system → extra step → people forget
5. **No outcomes tracking**: Captures ideas but not what happened → can't measure impact

### Future Use Cases

#### How would an Application Suggester Agent query this?

```python
# Application Suggester Agent
def suggest_applications(new_content_url: str):
    """
    Given new content, find similar past inspirations and suggest applications
    """
    # 1. Extract concepts from new content
    concepts = extract_concepts(new_content_url)
    
    # 2. Query inspirations.json for similar concepts
    similar = semantic_search(concepts, "inspirations/inspirations.json")
    
    # 3. Analyze application patterns
    patterns = analyze_application_patterns(similar)
    
    # 4. Suggest specific project applications
    return {
        'similar_inspirations': similar,
        'common_patterns': patterns,
        'suggested_applications': generate_suggestions(concepts, patterns),
        'relevant_lessons': find_relevant_lessons(concepts)
    }
```

#### How does this feed the VISION.md recommendation engine?

**Integration:**
- Tracks which types of content lead to successful implementations
- Identifies gaps (concepts captured but not applied)
- Suggests new content based on current project needs
- Learns what "good inspiration" looks like for this project

#### Could this be automatically populated by parsing chat transcripts?

Yes, with:
- Claude chat exports → parse for URLs shared
- Detect "brainstorming" patterns in conversation
- Extract key concepts and applications discussed
- Auto-generate draft inspiration entries for human review
- Track which chats led to commits/files/lessons

---

## Part 2: Multi-Perspective Debate

### Persona 1: Busy Developer (Immediate Utility)

**Primary Priority**: Minimize overhead, maximize immediate value

#### Opening Argument

"Look, I'm in the middle of coding. When I find something useful, I need to capture it in 30 seconds and get back to work. Here's what I propose:

**Format**: Simple markdown file `INSPIRATIONS.md` in project root.

**Structure:**
```markdown
# Project Inspirations

## 2025-01-07: MCP vs Code Execution
- **Source**: https://www.youtube.com/watch?v=D4ImbDGFgIM
- **Key idea**: Code execution > direct tool calls for context efficiency
- **Applied to**: lesson-009 orchestrator concept
- **Files**: .claude/ideas/orchestrator/*
- **Status**: Documented, ready to implement

## 2025-01-05: Another Thing
...
```

**Why this works:**
- One file, easy to find
- Chronological (matches how I think: "What did I do last week?")
- Minimal structure (URL + 3 bullets = done)
- Can grep it easily (`grep -i "mcp" INSPIRATIONS.md`)
- Lives where code lives (project root)

**What I don't want:**
- Separate database
- Complex schema to remember
- Multiple files to update
- Fancy tools that need maintenance

I've seen elaborate systems fail. Keep it simple, keep it in one place, make it fast."

#### Critique of AI Architect

"Your JSON schema is engineering masturbation. Nobody will maintain that. You want me to remember field names, structure embeddings, validate against schemas—when? While I'm coding? I'll just skip capturing entirely rather than deal with `inspiration.schema.json` validation errors.

And embeddings? Really? We're a learning project, not Google. That's premature optimization. Build the simple thing first, then add complexity when you actually NEED it.

Your approach optimizes for a future system (Lesson 011) that doesn't exist yet. What if we never build it? Or build it differently? You've created overhead for a hypothetical."

#### Critique of Knowledge Manager

"You want me to write a blog post for every YouTube video? That 2,679-line inspiration file? That's 30 minutes of work! I found something useful, I want to note it in 30 SECONDS and move on.

And your directory structure—`inspirations/mcp-and-protocols/connections.md`—I have to decide WHERE to put it, THEN write detailed markdown, THEN cross-reference other inspirations? That's three friction points before I even start.

The perfect capture system that takes 30 minutes won't get used. The 30-second system that's 'good enough' will. Your system optimizes for the 1% of inspirations that deserve deep analysis, but makes the 99% painful."

#### Refinement & Compromise

"Okay, fair points. Lost context IS expensive—I've experienced that pain. And 200 entries in one file would be chaos.

**Refined proposal:**
- Keep the simplicity (markdown, quick capture)
- Add minimal structure (YAML frontmatter for queryability)
- Split by time (monthly files: `inspirations/2025-01.md`)
- Add `INDEX.md` for human scanning

**Format:**
```markdown
# January 2025 Inspirations

## insp-2025-01-001: MCP vs Code Execution
<!--
url: https://www.youtube.com/watch?v=D4ImbDGFgIM
type: video
date: 2025-01-07
status: applied
impact: 5
tags: mcp, code-execution, orchestrator
applied_to: lesson-009
-->

**Key concepts:**
- Code execution > direct tool calls (context efficiency)
- Progressive tool discovery (load on-demand)
- IPython = persistent state outside LLM context

**What we did:**
- Created `.claude/ideas/orchestrator/` (5 docs, 2679 lines)
- Designed self-evolving orchestrator for lesson-009
- Three-way comparison: Anthropic MCP + Cloudflare + Data Analytics Agent

**Breakthrough insight:**
IPython kernel can be working memory for orchestrator, with sub-agents for specialized tasks. Generated code saved as .py files (not pickle) for transparency.

**Links:**
- Docs: `.claude/ideas/orchestrator/README.md`
- Related: insp-2025-01-002 (Cloudflare Code Mode)
```

**Compromise points:**
- Monthly files (not one huge file) → manageable size
- HTML comments for structured data → machine-parseable, not invasive for humans
- Still quick to write (~2 minutes, not 30 seconds but not 30 minutes)
- Human-readable prose, but queryable via comment parsing

**What I'm NOT doing:**
- Separate JSON file (too much overhead)
- Complex schema validation (brittle)
- Multiple cross-referenced files (coordination problem)

This balances capture speed with long-term value."

---

### Persona 2: AI System Architect (Future Automation)

**Primary Priority**: Structured data that enables automation and semantic search

#### Opening Argument

"We're building a recommendation engine. That requires structured, queryable data. Markdown is nice for humans but terrible for machines. Here's the right approach:

**Format**: JSON schema with strict validation

**Structure:**
```json
{
  "inspirations": [
    {
      "id": "insp-001",
      "source": {
        "url": "https://www.youtube.com/watch?v=D4ImbDGFgIM",
        "type": "video",
        "title": "Code Execution with MCP",
        "author": "Anthropic",
        "published": "2024-12-15",
        "discovered": "2025-01-07"
      },
      "concepts": [
        {"name": "code-execution", "category": "architecture"},
        {"name": "context-efficiency", "category": "optimization"},
        {"name": "progressive-discovery", "category": "design-pattern"}
      ],
      "applications": [
        {
          "type": "lesson",
          "id": "lesson-009",
          "description": "Orchestrator with IPython state",
          "status": "documented"
        }
      ],
      "artifacts": [
        {
          "type": "documentation",
          "paths": [".claude/ideas/orchestrator/"]
        }
      ],
      "impact": 5,
      "embeddings": [0.234, 0.567, ...],
      "relationships": ["insp-002", "insp-007"]
    }
  ]
}
```

**Why this is necessary:**
1. **Semantic search**: Embeddings enable "find content like this"
2. **Structured queries**: JSON Path/GraphQL for complex queries
3. **Type safety**: Schema validation prevents inconsistency
4. **Machine learning**: Training data for recommendation engine
5. **API-ready**: Future web UI or external integrations

**Schema-first approach:**
- Define `inspiration.schema.json`
- Validation on every entry
- CLI tool to add/query entries
- Git hooks to validate JSON

Markdown is for humans. We're building an AI system. The data layer must be machine-first."

#### Critique of Busy Developer

"Your single markdown file is the classic engineering anti-pattern: 'works for 10 entries, breaks at 100.' What happens when `INSPIRATIONS.md` has 200 entries? Grepping for 'mcp' returns 15 matches—now what? No way to filter by status, impact, date range, applied vs not applied.

And it's not queryable. Lesson 011 (the recommendation engine) needs to:
- Find inspirations with similar concepts
- Identify application patterns
- Suggest new applications

Your format requires parsing unstructured markdown, handling inconsistent formatting (you WILL format things differently each time), and hoping people don't deviate from the template. That's brittle.

Worst: no validation. Nothing stops someone from adding an entry without a URL, or misspelling 'Status', or forgetting which format to use. Six months from now, `INSPIRATIONS.md` will be a mess."

#### Critique of Knowledge Manager

"You're optimizing for the wrong thing. Yes, comprehensive context is valuable, but at what cost? Your individual inspiration file is 150+ lines with YAML frontmatter, markdown headers, cross-references, open questions, future applications...

The overhead-to-value ratio is terrible. Most inspirations don't warrant that detail. And your multi-file structure creates coordination problems:
- Update theme README
- Update individual file
- Update applied-to-lessons file
- Update connections.md
- Update main README timeline

That's 5 files to keep in sync! This WILL rot. Humans are bad at maintaining complex cross-references.

Your system optimizes for the ideal case (comprehensive retrospective analysis) but makes the common case (quick capture) painful. That's backwards."

#### Refinement & Compromise

"Alright, I hear you—humans do the capturing, format can't be hostile. And building for non-existent Lesson 011 is speculative.

**Refined proposal:**
Start simple, evolve to structured:

**Phase 1 (MVP)**: Markdown with consistent structure
```markdown
# inspirations/2025-01-07-mcp-code-execution.md
---
id: insp-001
url: https://www.youtube.com/watch?v=D4ImbDGFgIM
date: 2025-01-07
status: applied
impact: 5
tags: [mcp, code-execution, orchestrator]
---

[Human-friendly markdown content]
```

**Phase 2 (When Lesson 011 starts)**: Extract to JSON
```bash
# Script to parse markdown frontmatter → inspirations.json
$ python scripts/compile_inspirations.py
# Generates inspirations.json from markdown files
# Markdown remains source of truth, JSON is build artifact
```

**Phase 3 (If needed)**: Add embeddings
```bash
# Generate embeddings for semantic search
$ python scripts/generate_embeddings.py
# Creates inspirations_embeddings.json
```

**Compromise points:**
- Markdown first (human-friendly capture)
- Structured extraction when needed (build step, not upfront)
- YAML frontmatter (enough structure for parsing, familiar to developers)
- JSON as build artifact (not source of truth)

**What I'm NOT doing:**
- Schema validation on every commit (too strict)
- Hand-writing JSON (hostile to humans)
- Premature embeddings (wait for need)

This gives machines what they need WITHOUT making humans' lives miserable. Markdown is input, JSON is derived output."

---

### Persona 3: Knowledge Manager (Comprehensive Context)

**Primary Priority**: Preserve rich context and connections for long-term learning

#### Opening Argument

"Both of you are missing the point. This isn't about convenience OR machines—it's about preserving learning over time. Here's what actually matters:

**Format**: Rich markdown with extensive cross-references, organized by theme

**Structure:**
```
inspirations/
├── README.md                    # Overview and timeline
├── mcp-and-protocols/
│   ├── README.md               # Theme overview
│   ├── 2025-01-07-anthropic-mcp-code-execution.md
│   ├── 2024-12-10-cloudflare-code-mode.md
│   └── connections.md          # How these relate
├── agent-architectures/
│   ├── README.md
│   ├── 2025-01-03-multi-agent-systems.md
│   └── ...
└── applied-to-lessons/
    ├── lesson-009.md           # All inspirations for lesson-009
    └── ...
```

**Individual inspiration file:**
```markdown
---
id: insp-001
source_url: https://www.youtube.com/watch?v=D4ImbDGFgIM
source_type: video
title: "Code Execution with MCP"
author: Anthropic
published: 2024-12-15
discovered: 2025-01-07
status: applied
impact: 5/5
related: [insp-002, insp-007]
---

# Code Execution with MCP (Anthropic Blog)

## Context
Discovered while researching how to reduce context bloat in lesson-003 coordinator...

## Key Concepts
### 1. Code Execution > Direct Tool Calls
**Why it matters**: LLMs trained on real code, not synthetic tool examples...

### 2. Progressive Tool Discovery
**Why it matters**: Load definitions on-demand vs all upfront...

## How We Applied This

### Brainstorming Session
**Date**: 2025-01-07
**Participants**: User + Claude
**Duration**: ~2 hours

**Initial question**: "Can Pydantic AI do progressive discovery?"
**Breakthrough moment**: Realized IPython kernel = persistent state...

### Outcomes
1. **Documentation created** (5 files, 2,679 lines)
   - `.claude/ideas/orchestrator/PRD.md`
   - `.claude/ideas/orchestrator/ARCHITECTURE.md`
   - ... (see full list)

2. **Lesson concept**: lesson-009 (self-evolving orchestrator)
   - Combines MCP insights with IPython persistence
   - Adds self-evolution through code generation

3. **Git commits**: (to be added when implemented)

### Related Inspirations
- **insp-002**: Cloudflare Code Mode (V8 isolates)
- **insp-007**: Data Analytics Agent (IPython approach)

### Lessons Learned
- Code execution pattern applies broadly
- Sub-agent isolation critical
- Self-evolution requires transparency (files, not pickle)

### Open Questions
- Which sandbox approach? (IPython restrictions vs containers)
- Approval workflow for generated code?
- Session persistence strategy?

## Follow-up Content to Explore
- [ ] RestrictedPython documentation
- [ ] V8 isolate performance benchmarks
- [ ] IPython kernel internals

## Future Applications
Could this pattern apply to:
- Multi-modal agent pattern? (video + audio processing)
- Production deployment? (scale considerations)
```

**Why this preserves learning:**
1. **Rich context**: Can reconstruct thinking months later
2. **Connections**: See relationships between ideas
3. **Evolution tracking**: From discovery → brainstorm → implementation
4. **Lessons learned**: What worked, what didn't
5. **Future value**: Questions to explore, related concepts

This isn't documentation—it's institutional memory. In 6 months when we revisit this, we'll thank ourselves for capturing the full story."

#### Critique of Busy Developer

"Your minimalism is false economy. You save 5 minutes now, waste 2 hours later when you need context you didn't capture.

Real scenario: Six months from now, you're designing lesson-015 and remember 'that MCP thing from January.' You open `INSPIRATIONS.md`, find:
```markdown
## 2025-01-07: MCP vs Code Execution
- Source: https://www.youtube.com/watch?v=D4ImbDGFgIM
- Key idea: Code execution > direct tool calls
- Applied to: lesson-009
- Status: Documented
```

That's it? What was the breakthrough insight? Why did we choose IPython over RestrictedPython? What open questions did we have? You'll spend an hour re-watching the video and re-reading `.claude/ideas/orchestrator/` files trying to reconstruct the thinking.

Lost context is expensive. Your format captures WHAT happened but not WHY it mattered."

#### Critique of AI Architect

"Your obsession with structure ignores that humans do the capturing. JSON is hostile to human workflows:
- Can't quickly edit in any text editor (syntax errors break everything)
- Can't skim visually (arrays of objects aren't scannable)
- Can't write naturally (prose becomes strings with escaped quotes)

Example: Try capturing '3 key insights' in your format. You'll type:
```json
"concepts": [
  {"name": "code-execution", "category": "???"},
```
Wait, what are valid categories? Let me check the schema... And I have to quote everything... And don't forget that trailing comma...

This is why developers hate data entry. The format fights natural expression.

Worse: You're building for Lesson 011 before Lesson 011 exists. That's speculative generality—adding complexity for a hypothetical future need. What if the recommendation engine needs different data? You've locked yourself into a schema too early."

#### Refinement & Compromise

"I concede: my 150-line inspiration file is overkill for most captures. But we need ENOUGH context to be useful later.

**Refined proposal:**
Two-tier system based on impact:

**Tier 1: Quick Captures (90% of inspirations)**
```markdown
## insp-001: MCP Code Execution
- **Source**: https://www.youtube.com/watch?v=D4ImbDGFgIM (video, 2025-01-07)
- **Key insight**: Code execution > tool calls for context efficiency
- **Application**: lesson-009 orchestrator with IPython state
- **Artifacts**: `.claude/ideas/orchestrator/` (5 docs)
- **Status**: ✅ Applied (documented, ready to implement)
- **Impact**: ⭐⭐⭐⭐⭐
- **Related**: insp-002 (Cloudflare), insp-007 (Data Analytics)
```
~2 minutes to capture, bullet format

**Tier 2: Deep Dives (10% of inspirations)**
When something is truly significant (like this MCP discovery), expand with:
```markdown
### Deep Dive: Why This Mattered

**Problem we were solving:**
Lesson-003 coordinator had context bloat with multiple agents...

**Brainstorming process:**
Started asking "Can Pydantic AI do progressive discovery?"
Realized IPython = persistent state...
Combined with sub-agent delegation pattern...

**Key decisions:**
- Python files vs pickle (transparency)
- IPython vs RestrictedPython (MVP simplicity)
- Sub-agents for specialization (context isolation)

**Open questions:**
- Sandbox approach?
- Approval workflow?

**Future potential:**
This pattern could apply to lesson-012 (multi-modal)...
```
~10 minutes for high-impact inspirations

**File organization:**
```
inspirations/
├── 2025/
│   ├── 2025-01.md          # Monthly quick captures
│   └── 2025-01-07-mcp-deep-dive.md  # Optional deep dives
└── INDEX.md                # Timeline overview
```

**Compromise points:**
- Default to quick capture (low overhead)
- Deep dive only when justified (significant impact/complexity)
- Monthly files (manageable, chronological)
- INDEX.md for scanning (human UX)

**What I'm NOT doing:**
- Requiring extensive detail for every inspiration (overkill)
- Complex cross-reference maintenance (brittle)
- Multiple files to update (coordination tax)

This preserves valuable context without making everything a blog post."

---

## Part 3: Synthesis & Recommendation

### Hybrid Approach: Practical System

**Core Principles:**
1. **Low friction capture** (2-3 minutes, not 30 minutes)
2. **Machine queryable** (consistent structure, parseable)
3. **Scales gracefully** (10 entries → 200 entries)
4. **Preserves context** (enough to recreate thinking)
5. **Evolves with project** (simple → sophisticated)

### Recommended Structure

```
inspirations/
├── README.md                 # Human overview, timeline, patterns
├── 2025/
│   ├── 2025-01.md           # Monthly captures (bulk)
│   └── 2025-01-07-mcp-orchestrator.md  # Optional deep dives
├── by-lesson/               # (Generated) Links to lessons
│   └── lesson-009.md
└── .meta/
    └── inspirations.json    # (Generated) Machine-readable index
```

### Monthly Capture Format

**File: `2025-01.md`**

```markdown
# January 2025 Inspirations

> Quick reference for content that influenced this project this month.
> For full context on major inspirations, see individual deep-dive files.

---

## insp-2025-01-001: MCP vs Code Execution Architecture
**Source**: [Code Execution with MCP](https://www.youtube.com/watch?v=D4ImbDGFgIM) (Anthropic video)
**Discovered**: 2025-01-07 | **Status**: ✅ Applied | **Impact**: ⭐⭐⭐⭐⭐

**Key concepts:**
- Code execution > direct tool calls (LLMs better at code than tool syntax)
- Progressive tool discovery (2K vs 150K token overhead)
- IPython as persistent working memory outside LLM context

**What we built:**
- lesson-009 concept: Self-evolving orchestrator
- Comprehensive design docs: `.claude/ideas/orchestrator/` (PRD, architecture, examples)
- Combines MCP insights + IPython state + sub-agent delegation + code generation

**Breakthrough insight:**
IPython kernel = working memory. Sub-agents = focused contexts. Generated code as .py files = transparency.

**Related**: [Deep dive](./2025-01-07-mcp-orchestrator.md) | insp-2025-01-002 (Cloudflare), insp-2024-12-015 (Cole Medin video)

**Links:**
- Design docs: `.claude/ideas/orchestrator/README.md`
- Git commits: (TBD when implemented)

---

## insp-2025-01-002: [Next inspiration]
...
```

### Optional Deep Dive Format

**File: `2025-01-07-mcp-orchestrator.md`**

```markdown
---
id: insp-2025-01-001
title: "MCP vs Code Execution: Orchestrator Design"
source_url: https://www.youtube.com/watch?v=D4ImbDGFgIM
source_type: video
discovered: 2025-01-07
status: applied
impact: 5
tags: [mcp, code-execution, orchestrator, ipython, self-evolution]
related: [insp-2025-01-002, insp-2024-12-015]
---

# Deep Dive: MCP Code Execution → lesson-009 Orchestrator

## Context: Why We Were Looking

**The problem:**
Lesson-003 coordinator was getting complex. Each sub-agent (youtube, webpage) called independently, but no shared state. Started wondering: "How do production systems handle this?"

**Discovery path:**
1. Researching MCP implementations
2. Found Anthropic blog post about code execution
3. Followed references to Cloudflare Code Mode and Data Analytics Agent
4. 2-hour brainstorming session with Claude

## What We Learned

### Core Insight: LLMs are Better at Code Than Tool Syntax

**Traditional MCP:**
```python
# Load 150K tokens of tool definitions upfront
tools = [drive.getDoc, drive.updateDoc, ..., salesforce.createLead, ...]
```

**Code Execution:**
```python
# Agent writes code that orchestrates tools
code = """
doc = drive.getDoc(id)
processed = transform(doc)  # Stays in sandbox
salesforce.createLead(processed)
"""
```

**Why this matters:**
LLMs trained on billions of lines of real code, but only synthetic/contrived tool examples. Code generation leverages their strengths.

## Application to agent-spike

**Our adaptation:**
1. IPython kernel = persistent working memory (not just sandbox)
2. Sub-agent delegation = specialized contexts (our lesson-003 pattern)
3. Code generation = self-evolution (save as .py files, not pickle)
4. Progressive discovery = search_tools() vs loading all upfront

**Novel combination:**
None of the source materials (Anthropic, Cloudflare, Data Analytics Agent) combined ALL these. We synthesized:
- Anthropic's progressive discovery
- Cloudflare's "code is better" insight
- Data Analytics Agent's IPython approach
- Our lesson-003 multi-agent pattern
- Added self-evolution (generate functions and agents)

## Brainstorming Session Highlights

**Key questions asked:**
- "Can Pydantic AI tools do progressive discovery?" → YES (search_tools pattern)
- "Could IPython be stateful environment?" → YES (persistent kernel)
- "Do sub-agents need the transcript in context?" → YES (but temporarily, then destroyed)
- "Pickle vs Python files?" → Files (transparency, git, review)

**Breakthrough moments:**
1. Realizing IPython = working memory (data outside LLM context)
2. Sub-agents get isolated context (not shared history)
3. System can generate new functions AND agents (self-evolution)

## What We Built

**Artifacts created (2025-01-07, ~3 hours):**
- `.claude/ideas/orchestrator/README.md` (overview)
- `.claude/ideas/orchestrator/PRD.md` (requirements, 13KB)
- `.claude/ideas/orchestrator/ARCHITECTURE.md` (technical design, 20KB)
- `.claude/ideas/orchestrator/EXAMPLES.md` (6 detailed examples, 18KB)
- `.claude/ideas/orchestrator/COMPARISON.md` (vs 6 other approaches, 11KB)
- `.claude/ideas/orchestrator/DECISIONS.md` (design rationale, 12KB)

**Total:** 2,679 lines of design documentation

**Status:** Concept phase, ready for lesson-009 implementation

## Key Design Decisions

### 1. Why IPython Instead of Plain exec()?

- Persistent state across executions
- Better error handling
- Rich display system (DataFrames, plots)
- Battle-tested (Jupyter ecosystem)

### 2. Why Python Files Instead of Pickle?

- Transparency (human-readable)
- Version control (git diffs)
- Security (no deserialization)
- Editability (humans can improve)

### 3. Why Sub-Agents Instead of Monolithic?

- Context isolation (budget efficiency)
- Specialization (tuned prompts)
- Reusability (same agent, many tasks)

## Open Questions (For Implementation)

**Technical:**
- Sandbox approach: IPython restrictions vs RestrictedPython vs subprocess?
- Session persistence: Local files vs cloud storage?
- Error recovery: Retry how many times before asking human?

**Design:**
- Approval workflow: Auto-execute generated code or require review?
- Tool registry: Pre-populate from lessons 001-003 or start empty?
- Model selection: Sonnet for coordinator or Haiku for cost?

**Future:**
- Could this integrate with MCP servers? (not just Python libraries)
- Multi-user sessions? (shared learned skills)
- Web UI for learned skills browser?

## Impact Assessment

**Immediate:**
- Lesson-009 concept defined
- Comprehensive design documentation
- Clear implementation path (5 phases)

**Long-term potential:**
- Could become core pattern for entire project
- Enables true self-improvement (system generates own capabilities)
- Aligns with VISION.md goals (especially #3 and #4)

**Influenced by:**
- insp-2025-01-002: Cloudflare Code Mode (V8 isolates insight)
- insp-2024-12-015: Cole Medin video (multi-agent foundations)

**May influence:**
- lesson-010+: Advanced agent patterns
- Production architecture decisions
- VISION.md recommendation engine (lesson-011)

## Related Content to Explore

**Follow-up research:**
- RestrictedPython documentation (sandboxing options)
- V8 isolate performance benchmarks (if relevant)
- IPython kernel internals (state management)
- Pydantic AI agent composition patterns

**Similar concepts:**
- AutoGPT's code execution mode
- LangChain's Python REPL tool
- Semantic Kernel's plugins

## Lessons Learned

**About this capture process:**
- High-impact inspirations deserve deep documentation
- Brainstorming session was ~2 hours, documentation ~3 hours
- Writing this deep dive surfaced additional insights (e.g., "we synthesized 4 sources uniquely")
- Having this context will be invaluable when implementing lesson-009

**About the concepts:**
- Code execution is powerful but requires security considerations
- Self-evolution needs transparency (files, not black boxes)
- Best ideas come from combining multiple sources, not just copying one
```

---

## Immediate Action: Capture Today's Workflow

### Right now, create:

1. **Create directory structure:**
```bash
mkdir -p inspirations/2025 inspirations/.meta
touch inspirations/README.md inspirations/2025/2025-01.md
```

2. **Add to `inspirations/README.md`:**
```markdown
# Project Inspirations

> External content (videos, articles, papers) that influenced agent-spike development.

## Overview

This directory captures the "content → learning → application" pipeline:
- Discover interesting content
- Extract key concepts
- Apply to agent-spike
- Track outcomes

**Purpose:** Enable future AI recommendation engine (VISION.md Goal #4, lesson-011)

## Organization

- **Monthly files** (`2025/2025-01.md`): Quick captures (2-3 min each)
- **Deep dives** (`2025/2025-01-07-topic.md`): High-impact inspirations (10-15 min)
- **Machine index** (`.meta/inspirations.json`): Auto-generated for AI queries

## Current Status

- **Total inspirations**: 1
- **Applied**: 1 (lesson-009 orchestrator)
- **In progress**: 0
- **Backlog**: 0

## Timeline

### January 2025
- **2025-01-07**: [MCP Code Execution](#insp-2025-01-001) → lesson-009 concept ⭐⭐⭐⭐⭐

## Top Influences

1. **MCP Code Execution** (Anthropic) → lesson-009 orchestrator
2. *(More as project evolves)*

## Patterns Observed

*(Will emerge over time)*

- **Common application**: Taking external architecture patterns and adapting to Python/Pydantic AI
- **Success factor**: Combining multiple sources, not copying one
```

3. **Add capture to `inspirations/2025/2025-01.md`** (using format above)

4. **Create deep dive `inspirations/2025/2025-01-07-mcp-orchestrator.md`** (using format above)

5. **Update VISION.md Goal #4:**
```markdown
#### 4. Suggest Applications of Learned Concepts

**Goal:** When encountering new concepts, suggest applications to active projects

**Current Status:** ✅ Manual process established
- **Inspiration tracking**: `inspirations/` directory captures content → application workflow
- **Recent success**: MCP code execution video → lesson-009 orchestrator concept

**Future (lesson-011):** Application Suggester Agent
- Semantic search over inspirations
- Pattern recognition (how we typically apply concepts)
- Proactive suggestions when discovering new content

**Dependencies:** lesson-009 (orchestrator provides foundation for recommendation engine)
```

---

## Incremental Path: Evolution Over Time

### Phase 1: Manual Capture (Weeks 1-4)
- Use markdown monthly files
- Quick captures (2-3 min)
- Optional deep dives for high-impact
- Build habit, learn what's valuable

**Evaluation:** After 10 inspirations, review:
- Are we maintaining it?
- Is format working?
- What context do we wish we'd captured?

### Phase 2: Structured Extraction (Weeks 5-8)
- Add script: `scripts/compile_inspirations.py`
- Parse YAML frontmatter → `inspirations.json`
- Validate consistent capture
- Enable basic queries

### Phase 3: Semantic Search (Weeks 9-12)
- Generate embeddings for inspirations
- Build similarity search
- Start prototyping lesson-011 recommender
- Test queries: "Find content like X", "What haven't we applied?"

### Phase 4: Automation (Months 4-6)
- Parse Claude chat transcripts for URLs
- Auto-detect brainstorming sessions
- Generate draft inspiration entries
- Human reviews and approves

### Phase 5: Recommendation Engine (lesson-011)
- Full semantic search
- Pattern recognition (application strategies)
- Proactive suggestions ("Based on lesson-009, you might like...")
- Integration with VISION.md goals

---

## Integration Points

### 1. VISION.md
```markdown
### Goal #4: Suggest Applications → Track in inspirations/

**Links:**
- Inspiration log: `inspirations/README.md`
- Latest: `inspirations/2025/2025-01.md`
- lesson-011 design: (TBD)
```

### 2. STATUS.md
```markdown
### Current Work: lesson-009 (Orchestrator)

**Inspired by:** insp-2025-01-001 (MCP Code Execution)
- See: `inspirations/2025/2025-01-07-mcp-orchestrator.md`
- Design docs: `.claude/ideas/orchestrator/`
```

### 3. Lesson READMEs
```markdown
# lesson-009: Self-Evolving Orchestrator

**Inspired by:**
- [Anthropic: Code Execution with MCP](https://www.anthropic.com/engineering/code-execution-with-mcp)
- [Cloudflare: Code Mode](https://blog.cloudflare.com/code-mode/)
- [Data Analytics Agent](https://github.com/agency-ai-solutions/data-analytics-agent)

**See:** `inspirations/2025/2025-01-07-mcp-orchestrator.md` for how we applied these concepts

## Key Insight

Combined MCP progressive discovery + IPython state + sub-agent delegation + code generation
to create self-evolving system. Novel synthesis, not present in any source material.
```

### 4. Git Commits
```bash
git commit -m "feat(lesson-009): implement IPython kernel integration

Implements core orchestrator with persistent IPython state.
Data stays in kernel memory, not LLM context.

Inspired by: insp-2025-01-001
See: inspirations/2025/2025-01-07-mcp-orchestrator.md

🤖 Generated with Claude Code
Co-Authored-By: Claude <noreply@anthropic.com>"
```

### 5. Future lesson-011 (Recommendation Engine)
```python
# lesson-011/application_suggester/agent.py

@agent.tool
def find_similar_inspirations(url: str) -> list[dict]:
    """Given new content, find similar past inspirations"""
    # Load inspirations.json
    with open('inspirations/.meta/inspirations.json') as f:
        inspirations = json.load(f)
    
    # Extract concepts from new content
    new_concepts = extract_concepts(url)
    
    # Semantic similarity search
    similar = semantic_search(new_concepts, inspirations)
    
    return similar

@agent.tool
def suggest_applications(url: str) -> dict:
    """Suggest how to apply new content to current project"""
    similar = find_similar_inspirations(url)
    
    # Analyze application patterns
    patterns = analyze_patterns(similar)
    
    # Generate suggestions
    return {
        'similar_inspirations': similar,
        'common_patterns': patterns,
        'suggested_lessons': suggest_lessons(patterns),
        'estimated_impact': estimate_impact(patterns)
    }
```

---

## Success Metrics

### Quantitative
- ✅ Capture 80%+ of significant influences (not 100%, not 20%)
- ✅ Used weekly (checked/updated at least once per week)
- ✅ Enables lesson-011 queries (machine-readable structure works)
- ✅ Cross-referenced in 90%+ of lesson READMEs

### Qualitative
- ✅ Can answer "What inspired lesson X?" in 30 seconds
- ✅ Patterns emerge (common application strategies visible)
- ✅ New collaborators understand project influences
- ✅ Captures "why" not just "what" (context preserved)
- ✅ Feels valuable, not burdensome (maintained over months)

### Failure Indicators
- ❌ Last update >2 weeks ago
- ❌ Format changed 3+ times (inconsistency)
- ❌ Can't query it (too unstructured)
- ❌ Lost context on major decisions

### Review Cadence
- **Monthly**: Scan captures, ensure consistency
- **Quarterly**: Analyze patterns, adjust format if needed
- **After lesson-011 built**: Validate AI can query effectively

---

## Concrete Example: Today's MCP Workflow

### What happened:
1. User shared YouTube URL about MCP vs code execution
2. Discussed concepts (2 hours): progressive discovery, IPython state, self-evolution
3. Created comprehensive design docs (3 hours): 6 files, 2,679 lines
4. Result: lesson-009 concept fully specified

### How to capture this:

**Step 1: Quick capture in `inspirations/2025/2025-01.md` (2 minutes)**

```markdown
## insp-2025-01-001: MCP vs Code Execution Architecture
**Source**: [Code Execution with MCP](https://www.youtube.com/watch?v=D4ImbDGFgIM) (Anthropic video)
**Discovered**: 2025-01-07 | **Status**: ✅ Applied | **Impact**: ⭐⭐⭐⭐⭐

**Key concepts:**
- Code execution > direct tool calls (context efficiency)
- Progressive tool discovery (2K vs 150K tokens)
- IPython as persistent working memory

**What we built:**
- lesson-009 concept: Self-evolving orchestrator
- Design docs: `.claude/ideas/orchestrator/` (6 files, 2,679 lines)
- Combines 4 sources: Anthropic + Cloudflare + Data Analytics Agent + our lesson-003 pattern

**Breakthrough insight:**
IPython kernel = working memory. Sub-agents = isolated contexts. Code generation as .py files = transparency.

**Related**: [Deep dive](./2025-01-07-mcp-orchestrator.md)

**Links:**
- Design: `.claude/ideas/orchestrator/README.md`
- Commits: (TBD on implementation)
```

**Step 2: Deep dive in `inspirations/2025/2025-01-07-mcp-orchestrator.md` (10 minutes)**

Use full template from above including:
- Context (why we were looking)
- What we learned (key insights)
- Brainstorming highlights (questions, breakthroughs)
- What we built (artifacts)
- Design decisions (rationale)
- Open questions (for implementation)
- Impact assessment
- Related content to explore
- Lessons learned

**Step 3: Update integrations (3 minutes)**

- `inspirations/README.md`: Add to timeline, update counts
- `VISION.md`: Update Goal #4 with this success
- `.claude/ideas/orchestrator/README.md`: Link back to inspiration

**Total time:** ~15 minutes
- For a 5-hour session that produced major design work
- Context preserved for future reference and lesson-011

**Result:**
- Human can review this in 6 months and understand full context
- AI (lesson-011) can query structured data
- Pattern captured for recognizing similar opportunities
- Project history documented

---

## Summary: Recommended System

**Format:** Markdown-first with YAML frontmatter (human-friendly, machine-parseable)

**Structure:**
- Monthly files for quick captures (90% of inspirations)
- Optional deep dives for high-impact (10%)
- Auto-generated JSON for AI queries (build artifact, not source)

**Workflow:**
- 2-3 minutes for quick capture (low friction)
- 10-15 minutes for deep dives (high-impact only)
- Weekly review (ensure consistency)
- Monthly patterns analysis (learn from history)

**Evolution:**
- Phase 1: Manual markdown (establish habit)
- Phase 2: Structured extraction (enable queries)
- Phase 3: Semantic search (build lesson-011)
- Phase 4: Automation (parse chat transcripts)

**Integration:**
- Links from VISION.md, STATUS.md, lesson READMEs
- References in git commits
- Foundation for lesson-011 recommendation engine

**Success:** Enables both human review and AI queries, maintained over months, patterns emerge, valuable not burdensome.

**This balances all three perspectives:** simple enough to maintain (Busy Developer), structured enough to query (AI Architect), rich enough to preserve context (Knowledge Manager).
