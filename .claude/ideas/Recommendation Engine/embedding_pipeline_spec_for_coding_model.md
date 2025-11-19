# Embedding & Chunking Pipeline Spec (for Coding Model)

This document defines how to implement the **embedding + chunking + storage** pipeline for my Personal Research Assistant.

You (the coding model) are responsible for writing code that follows this design. Do not change models or core architecture unless explicitly instructed.

---

## 1. High-Level Goals

We want to index content (primarily YouTube transcripts and web pages) so that the system can:

1. **Search semantically** across chunks of content.
2. **Model my preferences** and recommend content I will like.
3. **Suggest applicable content** for current projects/problems.

To accomplish this, every content item will have **two types of embeddings**:

1. A **global embedding** (one vector per item) representing the whole document.
2. Multiple **chunk embeddings** (many vectors per item) representing local regions.

These two representations will be stored in **separate Qdrant collections** and used for different tasks.

---

## 2. Models to Use

**Important:** Every content item MUST have exactly:
- **One global embedding** (`gte-large-en-v1.5`) stored in the `content` collection.
- **N chunk embeddings** (`bge-m3`) stored in the `content_chunks` collection.

The coding model must enforce this strictly.

### 2.1 Global Embedding Model

- **Model:** `Alibaba-NLP/gte-large-en-v1.5`
- **Role:** Global / whole-document embeddings.
- **Context window:** 8,192 tokens.
- **Output dimension:** 1024.

Use this model to create **one vector per content item** (video transcript, blog post, article, etc.).

This global vector is used for:
- Recommendations.
- Preference learning.
- Application suggester.
- Feed ranking.

### 2.2 Chunk Embedding Model

- **Model:** `BAAI/bge-m3`
- **Role:** Chunk-level embeddings for semantic search and local relevance.
- **Context window:** 8,192 tokens.
- **Output dimension:** 1024.

Use this model for **all chunks** produced from content (transcripts + web pages).

Chunk vectors are used for:
- Semantic search.
- Question-specific retrieval.
- Concept extraction and tagging.
- Locating the most relevant passages.

> Important: Do not mix up the two models. Global = `gte-large-en-v1.5`. Chunks = `bge-m3`.

---

## 3. Content Types

**Important:**
- **YouTube transcripts** → use **time + token chunker only** (DO NOT use Docling).
- **Web content** → use **Docling hybrid chunking**.

We will handle two main content types:

We will handle two main content types:

1. **YouTube video transcripts** (from `youtube-transcript-api`).
2. **Web content** (blogs, articles, docs) processed via **Docling**.

Each type has its own chunking strategy, but both share the same embedding models.

---

## 4. Collections in Qdrant

We will maintain **two Qdrant collections**:

### 4.1 `content` Collection (Global Level)

One record per logical content item (e.g., per video, per article).

- **Vector model:** `gte-large-en-v1.5` (global embedding).
- **Vector dimension:** 1024.

**Suggested schema (payload fields):**

- `id` (string): stable unique ID, e.g. `"youtube:<video_id>"` or `"web:<domain>/<slug>"`.
- `type` (string): e.g. `"youtube_video"`, `"web_article"`.
- `title` (string).
- `source` (string): channel/site name.
- `url` (string).
- `summary` (string): optional, a short summary.
- `tags` (list[str]): optional semantic tags.
- `created_at` (datetime or ISO string).
- `rating` (int/float): my personal rating.
- `importance` (string or int): how important I consider this item.
- `projects` (list[str]): project IDs this content relates to.
- `raw_metadata` (object): any additional metadata.

**Vector field:**
- `global_embedding` (1024-dim float vector from `gte-large-en-v1.5`).

### 4.2 `content_chunks` Collection (Chunk Level)

Multiple records per content item.

- **Vector model:** `BAAI/bge-m3`.
- **Vector dimension:** 1024.

**Suggested schema (payload fields):**

- `id` (string): unique chunk ID, e.g. `"youtube:<video_id>:chunk_<index>"`.
- `doc_id` (string): ID of the parent item (matches `content.id`).
- `type` (string): `"youtube_chunk"` or `"web_chunk"`.
- `title` (string): same title as parent, for convenience.
- `source` (string): channel/site.
- `url` (string): parent URL.
- `chunk_index` (int): 0-based index.
- `text` (string): chunk text.
- `start_char` / `end_char` (int): optional, offsets into full text.
- `start_time` / `end_time` (float): for YouTube chunks, seconds in video.
- `local_summary` (string): optional, short summary of this chunk.
- `tags` (list[str]): optional local tags.
- `projects` (list[str]): optional project IDs.

**Vector field:**
- `chunk_embedding` (1024-dim float vector from `bge-m3`).

---

## 5. Chunking Strategies

We use **different chunking strategies** for transcripts and web pages, but both produce chunks that go through `bge-m3`.

### 5.1 YouTube Transcripts (Flat + Timestamped)

Transcripts from `youtube-transcript-api` are a flat list of segments with timestamps:

```json
{
  "start": 12.34,
  "duration": 5.43,
  "text": "..."
}
``

They do NOT have structural headings, so we build chunk structure based on **time + token length**.

**Algorithm (time + token hybrid chunking):**

1. Convert transcript segments to a sequence of text units with their timestamps.
2. Tokenize text (approximate tokens if necessary) to track chunk sizes.
3. Iterate through segments and accumulate into a buffer while:
   - total tokens in buffer < ~2,000–3,000 tokens, AND
   - no large pause has been hit.
4. A "large pause" is when `next.start - current_end > PAUSE_THRESHOLD` (e.g. 8–10 seconds). When this happens, finalize the current chunk.
5. When either limit is hit (token size or pause), finalize a chunk:
   - Chunk text = concatenation of segment texts.
   - Chunk `start_time` = start of first segment in chunk.
   - Chunk `end_time` = end of last segment in chunk.
6. Optionally add a small overlap:
   - Include the last 1–2 segments from the previous chunk at the beginning of the next chunk to maintain continuity.
7. For extremely long videos (> 8,192 tokens total):
   - The above logic will naturally produce multiple chunks.
   - Ensure individual chunks stay well under 8,192 tokens (target 2k–3k, hard cap at ~6k–7k).

Each finalized chunk is then embedded with **`bge-m3`** and stored in the `content_chunks` collection.

### 5.2 Web Content (Blogs, Articles, Docs) via Docling

Web content is processed with **Docling**, which emits a structured representation (headings, paragraphs, lists, code blocks, etc.). Docling also supports **hybrid chunking**, combining structural and token-based boundaries.

**For web content:**

1. Use Docling to convert HTML/Markdown into a structured form.
2. Use Docling's hybrid chunker to produce semantically meaningful chunks that respect:
   - headings/sections,
   - paragraphs,
   - code blocks,
   while keeping each chunk under a chosen token limit.
3. Choose target chunk size ~1,000–2,000 tokens (with a hard cap well below 8,192).
4. For each chunk returned by Docling:
   - Extract chunk text.
   - Track `start_char`/`end_char` offsets into the full text if Docling provides this.
   - Generate a `chunk_index` and any local summaries or tags.
5. Embed each chunk with **`bge-m3`** and store in `content_chunks`.

Docling's hybrid chunking is not used for YouTube transcripts, only for structured web content.

---

## 6. Global Embedding Generation (All Content Types)

For each content item (video or web page), we also compute a **global embedding** with `gte-large-en-v1.5`.

### 6.1 For Items ≤ 8,192 Tokens

1. Build a single text string representing the whole item:
   - For videos: full transcript text.
   - For web pages: Docling-flattened body text (or a cleaned, linearized form).
2. Feed this text to `gte-large-en-v1.5` once.
3. Store the resulting 1024-dim vector as `global_embedding` in the `content` collection.

### 6.2 For Items > 8,192 Tokens

1. Split the full text into **2–3 large slices** (e.g., ~6–8k tokens each).
2. For each slice, compute a `gte-large-en-v1.5` embedding.
3. Take the **mean** of these slice embeddings → final `global_embedding`.
4. Store this pooled embedding in `content`.

Do not store slice-level `gte` vectors in Qdrant; only store the final pooled vector.

---

## 7. Ingestion Flow (Step-by-Step)

This is the high-level ingestion pipeline you should implement in code.

### 7.1 For a New YouTube Video

1. **Fetch transcript** via `youtube-transcript-api`.
2. **Build full transcript text**:
   - Concatenate segments with spaces/newlines.
3. **Create or update `content` record**:
   - Construct `id = "youtube:<video_id>"`.
   - Fill metadata: `title`, `source` (channel), `url`, etc.
4. **Compute global embedding** with `gte-large-en-v1.5`:
   - If total tokens ≤ 8,192: embed full transcript.
   - Else: split into 2–3 slices, embed, mean-pool.
   - Save vector into `content.global_embedding`.
5. **Chunk transcript** using the time + token hybrid strategy.
6. For each chunk:
   - Compute `bge-m3` embedding.
   - Create a `content_chunks` record with payload described above.

### 7.2 For a New Web Article

1. **Fetch page HTML/Markdown**.
2. **Run Docling** to get structured representation.
3. **Flatten** to a full-text representation for global embedding.
4. **Create or update `content` record** with metadata.
5. **Compute global embedding** with `gte-large-en-v1.5`:
   - Same ≤8k vs >8k logic as above.
6. **Run Docling hybrid chunking** to generate chunks.
7. For each chunk:
   - Compute `bge-m3` embedding.
   - Create `content_chunks` record with appropriate payload.

---

## 8. Query & Ranking (High-Level Behavior)

### 8.0 Retrieval Modes (Search vs Recommendation vs Application Suggester)
Different tasks require different weightings in the final score. The coding model must expose three retrieval modes, each applying different weights:

#### **Search Mode** ("Find what matches this query")
- `w_chunk` = **high**
- `w_global` = medium
- `w_persona` = low
- `w_pref` = low

#### **Recommendation Mode** ("What should I watch next?")
- `w_chunk` = low
- `w_global` = medium
- `w_persona` = **high**
- `w_pref` = **high**

#### **Application Suggester Mode** ("Help with project X")
- `w_chunk` = **high**
- `w_global` = medium
- `w_persona` = medium
- `w_pref` = medium

These modes should be selectable by the caller.

This section is for context; the exact scoring formula can be refined later. Still, your code should make it easy to plug in this logic.

### 8.1 Types of Queries

1. **Semantic search:**
   - Input: free-text query.
   - Behavior: find chunks that best match query meaning.

2. **Problem-to-content suggestion (Application Suggester):**
   - Input: description of current project/problem.
   - Behavior: find content (videos/articles) that likely contain solutions or good examples.

3. **Preference-based recommendation:**
   - Input: implicit/explicit feedback and current context.
   - Behavior: rank already known content by how well it matches my preferences and the situation.

### 8.2 Suggested Retrieval Flow (Search / Problem-Solving)

1. **Encode query twice:**
   - `query_chunk_vec` = `bge-m3(query_text)`.
   - `query_global_vec` = `gte-large-en-v1.5(query_text)`.
2. **Chunk search:**
   - Use `query_chunk_vec` against `content_chunks` collection.
   - Retrieve top N chunks (e.g., 50–200).
3. **Group by `doc_id`** and compute a per-document **chunk score** (e.g., max or top-k mean similarity).
4. **Global similarity:**
   - For each candidate `doc_id`, fetch its `global_embedding` from `content`.
   - Compute similarity to `query_global_vec`.
5. **Combine signals:**
   - `score(doc) = w_chunk * chunk_score + w_global * global_score + w_pref * preference_score(doc)`.
   - `preference_score(doc)` can come from a user preference vector or ratings stored in Mem0.
6. **Return ranked documents + key chunks:**
   - For each doc, also return top few matching chunks (text + timestamps), so the UI can jump into the relevant part.

The precise weights (`w_chunk`, `w_global`, `w_pref`) can be tuned later.

---

## 9. Persona Modeling (Preference Intelligence Layer)

This section adds **persona‑based preference modeling**, which is separate from semantic search and global content meaning.

Personas represent **different dimensions of my taste**. They should influence recommendations differently than chunk-level or global-level relevance.

### 9.1 What a Persona Is
A *persona* is a vector representing one facet of my preferences, such as:
- "deep technical / infrastructure"
- "philosophy / storytelling"
- "humor / absurdity"
- "tutorial / step‑by‑step learning style"

Each persona is:
- a **1024‑dim vector** (same as global embeddings),
- built from **my liked/rated content**,
- updated incrementally as I interact with the system.

### 9.2 Persona Storage
Store personas in **Mem0** or a dedicated Qdrant collection:

**Collection name:** `personas`

**Fields:**
- `id`: persona name (e.g., `"technical_deep"`).
- `vector`: 1024‑dim persona embedding.
- `metadata`: optional fields (description, tags, confidence, created_at).

### 9.3 How Personas Are Built
For each persona:
1. Gather all **global embeddings** (gte-large) of content assigned to that persona.
2. Compute the persona vector as:
   - mean of embeddings, or
   - weighted mean if some items have higher ratings.
3. Store/update the persona vector in `personas`.

### 9.4 How Personas Influence Ranking
Personas are used in addition to:
- **chunk-match relevance** (bge‑m3)
- **global semantic relevance** (gte‑large)

For each candidate document:
1. Compute `persona_similarity = cosine(doc.global_embedding, persona.vector)`.
2. Optionally combine multiple personas:
   - highest similarity,
   - weighted persona blend,
   - or persona chosen by context.

### 9.5 Final Recommendation Score
Extend the earlier combined score:

```
score(doc) =
    w_chunk  * chunk_similarity(doc)
  + w_global * global_similarity(doc)
  + w_persona * persona_similarity(doc)
  + w_pref * preference_history(doc)
```

### 9.6 How Personas Differ From Search
**Search** answers: "What content matches this query?"
- Uses **chunk embeddings** (bge‑m3).
- Focused on local, task-level relevance.

**Personas** answer: "What content matches *my* taste?"
- Uses **global embeddings** (gte-large) against persona vectors.
- Focused on personal preference, tone, style, and learning style.

These signals are complementary.

---

## 10. Implementation Notes for the Coding Model

1. **Do not change models** unless explicitly instructed:
   - Global: always `Alibaba-NLP/gte-large-en-v1.5`.
   - Chunks: always `BAAI/bge-m3`.

2. **Abstract embedding calls** behind helper functions, for example:
   - `embed_global(text: str) -> np.ndarray` (gte-large).
   - `embed_chunk(text: str) -> np.ndarray` (bge-m3).

3. **Keep ingestion idempotent**:
   - If a `content.id` already exists, update the record instead of creating duplicates.
   - For chunks, you may choose to delete old chunks for a `doc_id` and re-insert.

4. **Be careful with tokenization estimates**:
   - If you do not have exact tokenizer functions, use a conservative character-to-token heuristic (e.g., 4 chars ≈ 1 token) to stay safely under model limits.

5. **Design payloads to be forward-compatible**:
   - It should be easy to add fields like `difficulty`, `style`, `trust_score` later.

6. **Logging and metrics**:
   - It will be useful to log:
     - number of chunks per doc,
     - average chunk size,
     - embedding latency per item.

This spec should give you everything needed to implement the embedding + chunking pipeline aligned with the overall system vision.

