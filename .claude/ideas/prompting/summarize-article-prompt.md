First, evaluate if this article contains actionable information:

  ## Content Quality Assessment

  **Check for these RED FLAGS (marketing/hype article):**
  - Repeated mentions of specific products/platforms (especially enterprise vendors)
  - Personal narrative style ("I thought... then I realized...")
  - Market projections and growth statistics without implementation details
  - Case studies without technical specifics
  - Buzzword density without concrete definitions
  - Zero code examples, architecture patterns, or technical frameworks
  - No failure modes, debugging approaches, or limitations discussed
  - Lacks "how to actually do this" guidance

  **Check for these GREEN FLAGS (actionable content):**
  - Specific implementation steps or code examples
  - Architecture patterns or design principles
  - Tool/library/framework comparisons with tradeoffs
  - Concrete techniques or methodologies
  - Failure modes and mitigation strategies
  - Clear technical constraints or boundaries
  - Reproducible examples or experiments

  ## Output Format

  If **3+ red flags and <2 green flags**: Flag as marketing content
  Assessment: Marketing/hype article - no actionable technical content

  One-sentence summary: [What it's actually about]

  Only useful insight (if any): [Single actionable takeaway, or "None"]

  Recommendation: Skip - no implementation value

  If **2+ green flags**: Proceed with full summary using this structure:

  # [Main Topic/Technique Name]

  ## The Problem
  What issue or challenge does this address? (2-3 sentences max)

  ## The Solution
  What is the proposed solution or key finding? Include concrete examples if applicable.

  ## Why It Works
  Brief explanation of the underlying mechanism or reasoning. (2-3 sentences)

  ## Results
  Key metrics, findings, or performance improvements (bullet points)

  ## How to Use / Implementation
  Practical steps, methods, or code examples if applicable

  ## Source
  Link to original paper/article/resource

  ## File Name
  Suggest a filename using lowercase with hyphens, based on the main topic/technique (e.g., `verbalized-sampling-summary.md` or `technique-name.md`)