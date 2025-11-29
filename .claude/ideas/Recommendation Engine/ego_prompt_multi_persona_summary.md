# EGO Prompt for Multi‑Persona Content Recommendation

This document summarizes how an EGO‑Prompt (Evolutionary Graph Optimization Prompt) system can be used in a **personal content recommendation engine** and how it handles **multiple personas** such as:
- Mini painting
- Makerspace creation
- Coding projects
- AI research / tinkering
- Woodworking

It covers:
1. The core idea of EGO Prompt
2. How it applies to recommendation systems
3. How multiple personas are managed
4. Detailed flow of the system
5. How reasoning, graph evolution, and personalization work

---

## 1. Core Idea of EGO Prompt
EGO Prompt is an architecture that enhances reasoning and personalization by:
- Building an **initial semantic causal graph (SCG)** representing concepts and relationships
- Running a **two‑stage reasoning loop** (Analyst → Decision‑Maker)
- Using a more powerful **Mentor Model** to critique and evolve both the prompt and the causal graph
- Repeating this iteratively so the system gets more aligned with actual behavior over time

Unlike traditional RAG or pure embeddings:
- The graph is **dynamic**, not static
- Reasoning is **personalized**, not one‑size‑fits‑all
- Preferences and concepts **evolve**, rather than being frozen
- The system learns *why* users prefer content, not just *what* they click

---

## 2. Real‑World Application: Personalized Content Recommendation
The recommendation system ingests:
- Videos (title, transcript, metadata)
- Blogs (text, tags, categories)
- User interactions (watch time, skips, likes, session timing)
- Embeddings (global vector for indexing)

Traditional embeddings only measure similarity.
EGO Prompt builds **reasoning chains**:
- Why did you like a certain video?
- What patterns show up across all your likes?
- Which underlying causes predict engagement?

This enables:
- New‑interest detection
- Session‑based preferences
- Mood/time‑of‑day based personalization
- Awareness of pacing, tone, narrator style, editing, cognitive load

---

## 3. Multi‑Persona Support
Instead of treating you as one monolithic user, the system represents multiple *sub‑selves* or personas:
- Mini painting
- Makerspace / tool layout
- Coding projects
- AI engineering
- Woodworking

Each persona has:
- Its **own semantic causal graph**
- Its **own system prompt** describing how it reasons
- Its **own causal‑reasoning prompt**
- Its own learned concepts, nodes, edges, and domain vocabulary

This prevents contamination of one interest area with another.

### Persona Examples
**Mini Painting Persona:**
- Nodes: color theory, OSL, weathering, speedpainting, airbrush vs brush
- Causal edges: "OSL technique → higher interest when lighting is discussed"

**Makerspace Persona:**
- Nodes: member safety, shop layout, tool zoning, 501(c)(3), CNC priority planning
- Edges: "tool zoning → better flow → higher satisfaction"

**Coding Persona:**
- Nodes: devcontainers, Python, Rust ergonomics, testing patterns, infra‑as‑code

**Woodworking Persona:**
- Nodes: joinery, dust collection, jigs, French cleats, finishes

Each persona grows independently.

---

## 4. Router: Choosing Which Persona Handles New Content
When a new video or blog appears, a **router model** predicts a probability distribution across personas.
Example for a video titled:
"Designing a tool wall layout for shared workshops":
- Makerspace: 0.50
- Woodworking: 0.40
- Mini painting: 0.10
- Coding/AI: 0.00

The content is then passed to the personas with the highest mixture weights.

---

## 5. Flow of the EGO Prompt System
Below is the full pipeline for recommendations.

### **Step 1 — Router chooses active persona(s)**
Determine which version(s) of you respond to this content.

### **Step 2 — Analyst extracts relevant causal paths**
From each persona’s SCG, the analyst pulls only the nodes/edges relevant to the new content.
Example (Woodworking persona):
- "tool wall" → "workflow" → "reduced wasted motion" → "higher satisfaction"

### **Step 3 — Decision‑Maker evaluates the content**
Combines:
- content features
- extracted causal paths
- your history in that persona

Outputs a recommendation with reasoning.

### **Step 4 — User interaction provides feedback**
Watch fully, ignore, bounce early, save, etc.

### **Step 5 — Mentor Model critiques the graphs and prompts**
If a recommendation was wrong, the mentor suggests corrections:
- add new nodes
- remove incorrect edges
- refine descriptions
- generalize concepts across personas when appropriate

Example:
"Add node: Background Music Overload → increases skip probability."

### **Step 6 — System updates persona graphs and prompts**
Each persona evolves independently.
Cross‑persona insights can be added when patterns apply broadly.

---

## 6. Cross‑Persona Learning
The system can discover universal themes you enjoy, such as:
- clear workflow demonstrations
- tool organization
- practical hands‑on examples
- charismatic teaching styles

These get represented as **shared latent patterns** across multiple persona graphs.

This enables:
- subtle transfer of preferences between domains
- recommendations that bridge hobbies
- smart novelty suggestions without noise

Example:
You liked a woodworking bench‑organization video → system may suggest a mini painting desk‑organization video.

---

## 7. Benefits Over Standard Recommenders
Compared to embeddings or keyword search:

### **EGO Prompt advantages:**
- Learns *why* you like things
- Evolves with your taste shifts
- Creates genuine reasoning chains
- Avoids stale/over‑repetitive content
- Can explain every recommendation
- Understands pacing, tone, editing, cognitive load
- Adapts per persona, not global preference
- Handles context (session, time of day, mood)

---

## 8. Summary
A multi‑persona EGO Prompt recommendation engine:
- Treats each hobby/interest as its own dynamic, evolving graph
- Routes new content to the appropriate persona(s)
- Uses reasoning, not just similarity, to evaluate every item
- Learns from mistakes through mentor feedback
- Evolves individual taste profiles over time
- Shares patterns across domains when appropriate

The final result is a **deeply personalized and explainable recommendation engine** that grows with you across all your interests.


---

## 9. Technical Implementation (Python + SurrealDB)

### 9.1. High-Level Architecture

**Core components:**
- **SurrealDB** as the main datastore for:
  - Users and personas
  - Semantic causal graphs (nodes + edges)
  - Content items (videos, blogs)
  - Interaction events (watch, skip, like, save, etc.)
  - Experiment / evolution logs
- **Python backend** for:
  - Persona routing
  - Analyst / decision-maker / mentor orchestration
  - Calling LLM APIs
  - Running the EGO optimization loop

Data flow:
1. Content ingested → stored in SurrealDB.
2. User events ingested → stored as event records.
3. Python service:
   - Loads content + relevant persona graph from SurrealDB.
   - Calls LLMs for analyst/decision/mentor passes.
   - Writes back updated prompts, nodes, and edges.

---

### 9.2. Suggested SurrealDB Schema

Namespace: `recsys`, DB: `personal`

**Users & Personas**
```sql
DEFINE TABLE user SCHEMAFULL;
DEFINE FIELD name      ON TABLE user TYPE string;
DEFINE FIELD createdAt ON TABLE user TYPE datetime VALUE time::now();

DEFINE TABLE persona SCHEMAFULL;
DEFINE FIELD user      ON TABLE persona TYPE record<user>;
DEFINE FIELD label     ON TABLE persona TYPE string;      -- e.g. 'woodworking'
DEFINE FIELD metadata  ON TABLE persona TYPE object;      -- e.g. { color: "#ff9900" }
DEFINE FIELD sysPrompt ON TABLE persona TYPE string;      -- system prompt for this persona
DEFINE FIELD cogPrompt ON TABLE persona TYPE string;      -- causal reasoning prompt
```

**Semantic Causal Graph**
```sql
DEFINE TABLE node SCHEMAFULL;
DEFINE FIELD persona   ON TABLE node TYPE record<persona>;
DEFINE FIELD label     ON TABLE node TYPE string;         -- e.g. 'visual organization'
DEFINE FIELD details   ON TABLE node TYPE string;         -- natural-language description
DEFINE FIELD weight    ON TABLE node TYPE number;         -- importance / confidence

DEFINE TABLE edge SCHEMAFULL;
DEFINE FIELD from      ON TABLE edge TYPE record<node>;
DEFINE FIELD to        ON TABLE edge TYPE record<node>;
DEFINE FIELD relation  ON TABLE edge TYPE string;         -- e.g. 'increases', 'decreases'
DEFINE FIELD details   ON TABLE edge TYPE string;         -- causal explanation
DEFINE FIELD weight    ON TABLE edge TYPE number;         -- strength / confidence
```

**Content Items**
```sql
DEFINE TABLE content SCHEMAFULL;
DEFINE FIELD kind       ON TABLE content TYPE string;     -- 'video' | 'blog'
DEFINE FIELD title      ON TABLE content TYPE string;
DEFINE FIELD uri        ON TABLE content TYPE string;     -- URL or ID
DEFINE FIELD metadata   ON TABLE content TYPE object;     -- tags, channel, duration, etc.
DEFINE FIELD features   ON TABLE content TYPE object;     -- derived (pacing, tone, etc.)
DEFINE FIELD embedding  ON TABLE content TYPE array<float>;
```

**Interactions & Experiments**
```sql
DEFINE TABLE interaction SCHEMAFULL;
DEFINE FIELD user       ON TABLE interaction TYPE record<user>;
DEFINE FIELD persona    ON TABLE interaction TYPE record<persona>;
DEFINE FIELD content    ON TABLE interaction TYPE record<content>;
DEFINE FIELD kind       ON TABLE interaction TYPE string; -- 'view', 'skip', 'like', ...
DEFINE FIELD value      ON TABLE interaction TYPE number; -- e.g. watch ratio 0..1
DEFINE FIELD createdAt  ON TABLE interaction TYPE datetime VALUE time::now();

DEFINE TABLE ego_run SCHEMAFULL;
DEFINE FIELD persona    ON TABLE ego_run TYPE record<persona>;
DEFINE FIELD workerId   ON TABLE ego_run TYPE string;
DEFINE FIELD step       ON TABLE ego_run TYPE int;
DEFINE FIELD metrics    ON TABLE ego_run TYPE object;     -- F1, accuracy, etc.
DEFINE FIELD changes    ON TABLE ego_run TYPE object;     -- applied mutations
DEFINE FIELD createdAt  ON TABLE ego_run TYPE datetime VALUE time::now();
```

---

### 9.3. Python: Basic SurrealDB Client Setup

```python
from surrealdb import Surreal
import asyncio

async def get_db():
    db = Surreal("ws://localhost:8000/rpc")
    await db.connect()
    await db.signin({"user": "root", "pass": "root"})
    await db.use("recsys", "personal")
    return db

async def get_persona(db, user_id: str, label: str):
    sql = "SELECT * FROM persona WHERE user = $user AND label = $label LIMIT 1;"
    res = await db.query(sql, {"user": user_id, "label": label})
    return res[0].get("result", [None])[0]
```

You can layer your own repository abstraction on top of this.

---

### 9.4. Loading Graph for a Persona

```python
async def load_graph_for_persona(db, persona_id: str):
    nodes_res = await db.query(
        "SELECT * FROM node WHERE persona = $p;", {"p": persona_id}
    )
    edges_res = await db.query(
        "SELECT * FROM edge WHERE from.persona = $p;", {"p": persona_id}
    )

    nodes = nodes_res[0]["result"]
    edges = edges_res[0]["result"]

    # Build adjacency for quick traversal
    adjacency = {n["id"]: [] for n in nodes}
    for e in edges:
        adjacency[e["from"]].append(e)

    return nodes, edges, adjacency
```

The adjacency map lets the analyst quickly traverse graph neighborhoods.

---

### 9.5. Analyst Stage (Sketch)

```python
from typing import List, Dict, Any

async def analyst_select_paths(llm, case_text: str, nodes: List[Dict[str, Any]], edges: List[Dict[str, Any]]):
    # You can prompt the LLM with a compact summary of nodes/edges
    graph_summary = make_graph_summary(nodes, edges)

    prompt = f"""
    You are an analyst selecting only the relevant causal logic for this case.

    Case:
    {case_text}

    Graph:
    {graph_summary}

    Return a JSON array of node IDs and edge IDs that are most relevant.
    """

    response = await llm(prompt)
    return parse_selected_paths(response)
```

Implementation details:
- `make_graph_summary` should compress nodes/edges into a manageable textual format.
- You can shard or sample the graph if it gets large.

---

### 9.6. Decision-Maker Stage (Sketch)

```python
async def decision_maker(llm, case_text: str, selected_graph_snippet: str):
    prompt = f"""
    You are a recommendation engine.

    Case (content + user context):
    {case_text}

    Relevant reasoning guidelines:
    {selected_graph_snippet}

    Decide whether to recommend this item.
    Return JSON with fields: {{"score": 0..1, "rationale": "..."}}.
    """

    response = await llm(prompt)
    return parse_decision(response)
```

The decision payload (score + rationale) is stored with the recommendation event.

---

### 9.7. Mentor Stage & Graph Evolution

When user feedback indicates an error (e.g., high predicted score but user skips quickly), call a stronger model:

```python
async def mentor_feedback(llm_strong, case, decision, graph_snippet, outcome):
    prompt = f"""
    You are a mentor model.

    Case:
    {case}

    Prior reasoning:
    {graph_snippet}

    Decision and outcome:
    {decision}
    Observed outcome: {outcome}

    Identify mistakes in the reasoning and suggest graph/prompt updates.
    Return JSON with:
    - add_nodes: [...]
    - add_edges: [...]
    - update_nodes: [...]
    - update_edges: [...]
    - prompt_updates: {{"sysPrompt": "...", "cogPrompt": "..."}}
    """

    response = await llm_strong(prompt)
    return parse_mentor_suggestions(response)
```

Then apply suggestions back into SurrealDB:

```python
async def apply_graph_updates(db, persona_id: str, suggestions: Dict[str, Any]):
    for node in suggestions["add_nodes"]:
        await db.create("node", {
            "persona": persona_id,
            "label": node["label"],
            "details": node["details"],
            "weight": node.get("weight", 1.0),
        })

    # Similarly for edges and updates...
```

---

### 9.8. Persona Router Implementation Sketch

Router gets:
- content features
- recent user interaction summary
- optional explicit mode (if you select a tab like "makerspace")

It outputs a distribution over personas:

```python
async def route_persona(llm, user_summary: str, content_summary: str, personas: list[dict]):
    persona_labels = ", ".join(p["label"] for p in personas)

    prompt = f"""
    User profile:
    {user_summary}

    Content:
    {content_summary}

    Personas: {persona_labels}

    Return a JSON object mapping persona label to probability (0..1) that
    this persona should handle the recommendation.
    """

    response = await llm(prompt)
    return parse_router_distribution(response)
```

You then:
- pick top-k personas
- run the analyst/decision loop per persona
- combine scores weighted by this distribution.

---

### 9.9. Putting It All Together (EGO Loop)

For each optimization step:
1. Sample a batch of past events (content + user + outcome).
2. For each event:
   - Run router → get persona mixture.
   - For each active persona:
     - Load graph from SurrealDB.
     - Run analyst + decision.
   - Compare predictions to ground truth outcomes.
3. For mispredictions:
   - Call mentor model → get graph/prompt updates.
   - Persist updates via SurrealDB.
4. Log metrics into `ego_run` table.

This implements the full EGO Prompt loop using Python + SurrealDB with multi-persona support.

