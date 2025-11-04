# Lesson 006: Memory with Mem0

**Status**: Phase 1 Complete (Mem0 wrapper and basic operations)

## What is Mem0?

Mem0 is a specialized memory layer for AI agents that provides:
- **Automatic fact extraction** from conversations
- **Semantic search** for relevant memories
- **Multi-level memory** (user, agent, session scopes)
- **Persistent storage** across sessions

Think of it as giving your AI agents a "memory bank" where they can store and retrieve contextual information about users, conversations, and past interactions.

## Why Memory Matters for AI Agents

Without memory, AI agents are stateless - they forget everything between interactions:
- ❌ Users must re-explain preferences every time
- ❌ No learning from past interactions
- ❌ No conversation continuity
- ❌ Repetitive and frustrating user experience

With memory:
- ✅ Agents remember user preferences
- ✅ Conversations build on previous context
- ✅ Personalized responses based on history
- ✅ Natural, continuous user experience

## What We Built

This lesson implements **Phase 1** from PLAN.md - a clean Mem0 wrapper:

```
memory/
├── __init__.py         # Package exports
├── config.py          # API key validation
└── client.py          # MemoryClient wrapper
```

### MemoryClient Features

The `MemoryClient` class provides simplified access to Mem0:

1. **Adding memories** from conversations
2. **Searching memories** semantically
3. **Getting all memories** for a user
4. **Updating memories** with new information
5. **Deleting memories** (specific or all)
6. **Formatting memories** for system prompts

## Quick Start

### Setup

```bash
# Install dependencies (from project root)
uv sync --group lesson-006

# Set up API keys
cd lessons/lesson-006
cp ../lesson-001/.env .  # Or create new .env

# Add to .env:
OPENAI_API_KEY=sk-proj-...  # Required for Mem0 embeddings
```

### Basic Usage

```python
from memory import MemoryClient

# Initialize client
client = MemoryClient()

# Add memories from conversation
client.add(
    messages=[
        {"role": "user", "content": "I love Python tutorials"},
    ],
    user_id="alice",
    metadata={"category": "preference"}
)

# Search memories semantically
memories = client.search(
    query="What content does the user prefer?",
    user_id="alice"
)

# Get all memories for a user
all_memories = client.get_all(user_id="alice")

# Format for system prompt
formatted = client.format_memories_for_prompt(memories)
print(formatted)
# Output:
# 1. Loves Python tutorials (relevance: 0.89)
```

### Running the Test

```bash
cd lessons/lesson-006
uv run python test_memory_simple.py
```

This demonstrates:
- Adding 3 different memories
- Searching with semantic queries
- Retrieving all memories
- Formatting for prompts
- Cleanup

## How Mem0 Works

### Fact Extraction

Mem0 automatically extracts facts from conversations:

**Input**:
```python
messages=[
    {"role": "user", "content": "I love watching tech tutorials and Python videos"}
]
```

**Extracted fact**: "Loves watching tech tutorials and Python videos"

### Semantic Search

Search finds relevant memories even without exact keyword matches:

**Query**: "What content does the user prefer?"

**Matches**:
- "Loves watching tech tutorials" (high relevance)
- "Prefers not to see political content" (medium relevance)

### Storage

Mem0 stores data locally by default:
- **Vector embeddings**: `~/.mem0/qdrant/` (for semantic search)
- **History DB**: `~/.mem0/history.db` (SQLite)

## Key Learnings

### 1. Mem0 API Return Formats

**Important**: Mem0 can return either lists OR dicts with a 'results' key:

```python
# Sometimes returns list directly
memories = client.search(...)  # → [{"memory": "...", "id": "..."}, ...]

# Sometimes returns dict with 'results' key
memories = client.search(...)  # → {"results": [...], "metadata": ...}

# Always handle both cases:
if isinstance(result, dict) and 'results' in result:
    memories = result['results']
elif isinstance(result, list):
    memories = result
```

### 2. User Isolation

Memories are scoped by `user_id`:
```python
# Alice's memories
client.add(messages, user_id="alice")

# Bob's memories (completely separate)
client.add(messages, user_id="bob")

# Search only retrieves for specified user
alice_memories = client.search(query, user_id="alice")  # Only Alice's
```

### 3. Metadata for Context

Add metadata to organize memories:
```python
client.add(
    messages=[...],
    user_id="alice",
    metadata={
        "category": "preference",
        "source": "youtube_tagging",
        "timestamp": "2025-11-04"
    }
)
```

### 4. System Prompt Integration

Use `format_memories_for_prompt()` to add context to agents:

```python
memories = client.search("user preferences", user_id="alice")
formatted = client.format_memories_for_prompt(memories)

system_prompt = f"""
You are a helpful assistant.

<user_memory>
{formatted}
</user_memory>

Use the user's preferences to personalize your responses.
"""
```

## What's NOT Included

This lesson implements **only Phase 1** from PLAN.md. The following are intentionally deferred:

### Phase 2: Agent Integration (Not Built)
- Dynamic system prompts with memory context
- Post-conversation memory updates
- Integration with Pydantic AI agents
- Memory-aware dependencies class

### Phase 3: Practical Examples (Not Built)
- YouTube agent with memory
- Webpage agent with memory
- Multi-agent memory sharing

**Rationale**: Focus on learning Mem0 basics first. Agent integration can be added later when needed.

## Next Steps

If you want to extend this lesson:

1. **Add dynamic system prompts** (Phase 2):
   ```python
   @agent.system_prompt(dynamic=True)
   def system_prompt(ctx: RunContext) -> str:
       memories = client.search(ctx.user_prompt, user_id=ctx.deps.user_id)
       return f"Base prompt\n<memory>{format(memories)}</memory>"
   ```

2. **Post-conversation updates** (Phase 2):
   ```python
   async def run_with_memory(prompt, user_id):
       result = await agent.run(prompt)
       client.add(
           messages=[
               {"role": "user", "content": prompt},
               {"role": "assistant", "content": result.data}
           ],
           user_id=user_id
       )
       return result
   ```

3. **Build memory-aware agents** (Phase 3):
   - Enhance YouTube tagger to remember user preferences
   - Track learning goals and suggest relevant content
   - Multi-agent coordination with shared memory

## References

- **Mem0 Documentation**: https://docs.mem0.ai/
- **Mem0 GitHub**: https://github.com/mem0ai/mem0
- **Medium Article**: "Adding a Memory Layer to PydanticAI Agents" by Dream AI
- **PLAN.md**: Full lesson plan with all 3 phases

## Files

```
lessons/lesson-006/
├── memory/                    # Mem0 wrapper package
│   ├── __init__.py
│   ├── config.py
│   └── client.py             # Main MemoryClient class
├── test_memory_simple.py     # Simple working test (THIS ONE!)
├── test_memory_basics.py     # Comprehensive test (has API quirks)
├── test_single_client.py     # Quick file locking test
├── .env                      # API keys (create from lesson-001)
├── PLAN.md                   # Complete lesson plan
├── README.md                 # This file
└── COMPLETE.md               # Completion summary
```

## Usage Examples

### Example 1: User Preferences

```python
client = MemoryClient()

# User tells us their preferences
client.add(
    messages=[
        {"role": "user", "content": "I prefer short videos under 10 minutes"},
    ],
    user_id="alice"
)

# Later, when tagging videos, retrieve preferences
memories = client.search(
    query="user's video length preferences",
    user_id="alice"
)

# Use in system prompt
formatted = client.format_memories_for_prompt(memories)
# → "1. Prefers short videos under 10 minutes (relevance: 0.92)"
```

### Example 2: Learning Goals

```python
# User shares learning goal
client.add(
    messages=[
        {"role": "user", "content": "I'm learning React hooks"},
    ],
    user_id="bob",
    metadata={"category": "learning_goal"}
)

# Later, suggest relevant content
memories = client.search(
    query="what is the user learning",
    user_id="bob"
)
# → Finds "Learning React hooks" memory
```

### Example 3: Multi-User Isolation

```python
# Different users, different memories
client.add(messages, user_id="alice")
client.add(messages, user_id="bob")

# Alice's search only sees Alice's memories
alice_memories = client.search(query, user_id="alice")

# Bob's search only sees Bob's memories
bob_memories = client.search(query, user_id="bob")
```

## Troubleshooting

### "OPENAI_API_KEY not found"
Mem0 requires OpenAI API for embeddings. Copy `.env` from lesson-001 or create new:
```bash
cd lessons/lesson-006
cp ../lesson-001/.env .
```

### File locking errors
Use single MemoryClient instance throughout your application (don't create multiple). Fixed in current implementation.

### Empty search results
- Mem0 needs time to index after adding memories (usually instant)
- Check user_id matches between add() and search()
- Try broader search queries

### UnicodeEncodeError on Windows
The test files include Windows encoding fixes. If you see this error in your own code:
```python
import io, sys
if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
```

---

**Time to completion**: ~1.5 hours (Phase 1 only)

**Next lesson**: TBD (likely multi-agent collaboration or production patterns)
