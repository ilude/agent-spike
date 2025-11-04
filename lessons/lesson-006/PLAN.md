# Lesson 006: Memory with Mem0

## Learning Objectives

By the end of this lesson, you will understand:

1. **Memory Architecture for AI Agents**
   - Multi-level memory (user, session, agent)
   - Semantic search and retrieval
   - Memory persistence across conversations

2. **Mem0 Integration**
   - Installing and configuring Mem0
   - Adding and retrieving memories
   - Search strategies for relevant context

3. **Pydantic AI + Mem0 Patterns**
   - Dynamic system prompts with memory context
   - Post-conversation memory updates
   - Memory-augmented agent responses

4. **Practical Memory Use Cases**
   - User preference tracking
   - Conversation continuity
   - Agent experience accumulation

## Problem Statement

Current agents (Lessons 001-003) are **stateless** - they forget everything between runs:
- No user preference tracking
- No conversation history
- No learning from past interactions
- Users must re-explain preferences every time

**Goal**: Add memory layer to make agents remember user preferences and past interactions.

## Memory Architecture

### Two Approaches Researched

#### Approach A: Mem0 (Official Memory Layer)
**Pros**:
- Purpose-built for AI memory
- 26% higher accuracy vs OpenAI memory
- 91% faster than full-context approaches
- 90% token reduction
- Hosted + self-hosted options

**Cons**:
- Requires OpenAI API for embeddings (additional cost)
- Another external dependency
- More complex setup

#### Approach B: Custom MongoDB Memory (from Medium article)
**Pros**:
- Full control over data structure
- No external API costs
- Pydantic models for validation

**Cons**:
- Need to build memory logic ourselves
- Requires MongoDB setup
- More code to maintain

### Decision: Use Mem0 for Learning

**Rationale**:
- Purpose-built for memory (don't reinvent the wheel)
- Excellent for learning memory patterns
- Can easily switch to custom implementation later
- Aligns with lesson philosophy: learn by using existing tools

## Mem0 Core Concepts

### Memory Levels

```python
# User-level memory (persists across all conversations)
memory.add(messages, user_id="user123")

# Session-level memory (within a conversation)
memory.add(messages, user_id="user123", session_id="session456")

# Agent-level memory (agent's accumulated knowledge)
memory.add(messages, agent_id="youtube_tagger")
```

### Memory Operations

1. **Add**: Extract and store facts from conversations
   ```python
   memory.add(messages, user_id="alice")
   ```

2. **Search**: Retrieve relevant memories
   ```python
   memories = memory.search("user's movie preferences", user_id="alice")
   ```

3. **Get All**: Retrieve all memories for a user
   ```python
   all_memories = memory.get_all(user_id="alice")
   ```

4. **Update**: Modify existing memories
   ```python
   memory.update(memory_id, data="updated content")
   ```

5. **Delete**: Remove memories
   ```python
   memory.delete(memory_id)
   ```

## Integration Pattern with Pydantic AI

### Pattern 1: Dynamic System Prompts (from Medium article)

```python
from pydantic_ai import Agent, RunContext

@agent.system_prompt(dynamic=True)
def system_prompt(ctx: RunContext[Dependencies]) -> str:
    # Retrieve relevant memories
    memories = memory.search(
        query=ctx.user_prompt,
        user_id=ctx.deps.user_id
    )

    # Format memories for system prompt
    memory_context = format_memories(memories)

    return f"""
    {base_system_prompt}

    <user_memory>
    {memory_context}
    </user_memory>
    """
```

### Pattern 2: Post-Conversation Memory Updates

```python
async def run_with_memory(prompt: str, user_id: str):
    # 1. Retrieve relevant memories
    memories = memory.search(query=prompt, user_id=user_id)

    # 2. Run agent with memory context
    result = await agent.run(
        prompt,
        deps=Dependencies(user_id=user_id, memories=memories)
    )

    # 3. Update memories after conversation
    memory.add(
        messages=[
            {"role": "user", "content": prompt},
            {"role": "assistant", "content": result.data}
        ],
        user_id=user_id
    )

    return result
```

## Implementation Plan

### Phase 1: Mem0 Setup and Basics

**Files to create**:
- `memory/config.py` - Mem0 configuration
- `memory/client.py` - Mem0 client wrapper
- `test_memory_basics.py` - Basic CRUD operations

**What to build**:
1. Initialize Mem0 with config
2. Wrapper functions for add/search/get_all/update/delete
3. Test basic memory operations

**Success criteria**:
- Can add memories
- Can search and retrieve memories
- Can update/delete memories

### Phase 2: Memory-Augmented Agents

**Files to create**:
- `memory/agent_memory.py` - Memory integration for agents
- `test_memory_agents.py` - Memory-augmented agent tests

**What to build**:
1. Memory-aware dependencies class
2. Dynamic system prompt with memory context
3. Post-conversation memory updates
4. Memory search strategies (semantic, recency)

**Success criteria**:
- Agents can retrieve user preferences
- Agents remember past interactions
- Memory updates automatically after conversations

### Phase 3: Practical Examples

**Files to create**:
- `examples/youtube_with_memory.py` - YouTube agent with memory
- `examples/webpage_with_memory.py` - Webpage agent with memory

**What to test**:
1. User says "I like tech content" → agent remembers for next run
2. User asks for tags → agent considers past preferences
3. Multiple users → memories stay separate

## Memory Schema Design

### User Profile Memory
```python
{
    "user_id": "alice",
    "content": "Prefers tech content, avoids politics",
    "category": "preferences",
    "metadata": {
        "source": "youtube_tagging",
        "confidence": "high"
    }
}
```

### Interaction History
```python
{
    "user_id": "alice",
    "content": "Tagged YouTube video about Python async",
    "category": "interaction",
    "metadata": {
        "timestamp": "2025-11-04T18:00:00",
        "agent": "youtube_tagger",
        "url": "https://youtube.com/..."
    }
}
```

### Agent Experience
```python
{
    "agent_id": "youtube_tagger",
    "content": "Tech videos benefit from specific tags: programming language, framework, level",
    "category": "heuristic",
    "metadata": {
        "learned_from": "interaction_patterns"
    }
}
```

## Testing Strategy

### Test Scenarios

1. **Basic Memory CRUD**
   - Add memory → verify stored
   - Search memory → verify retrieval
   - Update memory → verify changes
   - Delete memory → verify removal

2. **User Preference Tracking**
   - User expresses preference → stored
   - Next interaction → preference retrieved
   - Preference changes → old preference superseded

3. **Conversation Continuity**
   - Multi-turn conversation → context maintained
   - New session → previous context available
   - Different users → memories isolated

4. **Agent Learning**
   - Successful patterns → stored as heuristics
   - Repeated scenarios → effective strategies remembered
   - Pitfalls → warnings added to agent knowledge

## Key Decisions

### 1. Memory Granularity
**Decision**: Start with user-level memory (simplest)
- User preferences
- Interaction history
**Defer**: Session-level, agent-level (can add later)

### 2. Memory Update Strategy
**Decision**: Post-conversation updates (from Medium pattern)
- Keeps agent responses fast
- Allows complex memory analysis
- Background processing opportunity

### 3. Memory Search Strategy
**Decision**: Semantic search with Mem0 defaults
- Let Mem0 handle embeddings and vector search
- Can optimize later if needed

### 4. Storage Backend
**Decision**: Mem0 default (Qdrant local)
- Self-contained (no external DB)
- Good for learning
- Can migrate to cloud later

## Learning Outcomes

After completing this lesson, you will be able to:

✅ Explain why memory matters for AI agents
✅ Configure and use Mem0 for memory management
✅ Integrate memory with Pydantic AI agents using dynamic system prompts
✅ Implement post-conversation memory updates
✅ Design memory schemas for different use cases
✅ Test memory-augmented agents
✅ Understand trade-offs: Mem0 vs custom memory systems

## Estimated Time

- Phase 1 (Mem0 basics): ~30 minutes
- Phase 2 (Agent integration): ~45 minutes
- Phase 3 (Examples and testing): ~30 minutes

**Total**: ~1.5-2 hours

## References

1. **Mem0 Documentation**: https://docs.mem0.ai/
2. **Medium Article**: "Adding a Memory Layer to PydanticAI Agents" by Dream AI
   - Key insight: Post-conversation memory processing
   - Pattern: Dynamic system prompts with memory context
3. **Mem0 GitHub**: https://github.com/mem0ai/mem0
4. **Pydantic AI Docs**: Dynamic dependencies and system prompts

## Next Steps

After this lesson:
- Lesson 007: Multi-agent collaboration with shared memory
- Lesson 008: Agent orchestration patterns
- Lesson 009: Production deployment considerations

---

**Ready to build**: Let's give our agents the gift of memory! 🧠
