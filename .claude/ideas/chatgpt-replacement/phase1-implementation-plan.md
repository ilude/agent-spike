# Phase 1: Conversation History - Implementation Plan

**Goal**: Persistent conversation history with sidebar UI, auto-naming, and search.

## Storage Design

**Location**: `compose/data/conversations/`

**Structure**:
```
compose/data/conversations/
├── index.json                    # List of all conversations (metadata only)
└── {uuid}.json                   # Individual conversation files
```

**index.json**:
```json
{
  "conversations": [
    {
      "id": "uuid-1234",
      "title": "Auto-generated title",
      "created_at": "2025-11-22T06:08:00Z",
      "updated_at": "2025-11-22T06:15:00Z",
      "message_count": 5,
      "model": "moonshotai/kimi-k2:free"
    }
  ]
}
```

**{uuid}.json**:
```json
{
  "id": "uuid-1234",
  "title": "Auto-generated title",
  "created_at": "2025-11-22T06:08:00Z",
  "updated_at": "2025-11-22T06:15:00Z",
  "model": "moonshotai/kimi-k2:free",
  "messages": [
    {
      "id": "msg-uuid",
      "role": "user",
      "content": "Hello",
      "timestamp": "2025-11-22T06:08:00Z"
    },
    {
      "id": "msg-uuid-2",
      "role": "assistant",
      "content": "Hi there!",
      "timestamp": "2025-11-22T06:08:05Z",
      "sources": []
    }
  ]
}
```

## Backend Implementation

### 1. New Router: `compose/api/routers/conversations.py`

**Endpoints**:
```
GET  /conversations              # List all (from index.json)
POST /conversations              # Create new conversation
GET  /conversations/{id}         # Get full conversation
PUT  /conversations/{id}         # Update title
DELETE /conversations/{id}       # Delete conversation
GET  /conversations/search?q=    # Simple text search
```

### 2. Conversation Service: `compose/services/conversations.py`

**Methods**:
- `list_conversations()` - Read index.json
- `create_conversation()` - Create new, add to index
- `get_conversation(id)` - Read {id}.json
- `update_conversation(id, data)` - Update file and index
- `delete_conversation(id)` - Delete file, remove from index
- `add_message(id, message)` - Append message, update timestamps
- `search_conversations(query)` - Grep through conversation files
- `generate_title(first_message)` - Use cheap LLM to summarize

### 3. Modify WebSocket Handler

- Accept optional `conversation_id` in connect
- Save messages to conversation file on each exchange
- Auto-create conversation on first message if none provided
- Return `conversation_id` in responses

## Frontend Implementation

### 1. Layout Changes

**Current**: Full-width chat
**New**: Sidebar (280px) + Chat area

```
+------------------+--------------------------------+
| Sidebar          | Chat Area                      |
| - New Chat btn   |                                |
| - Search         |                                |
| - Conversation   |                                |
|   list           |                                |
+------------------+--------------------------------+
```

### 2. New Components/State

**State**:
- `conversations` - List from API
- `activeConversationId` - Current conversation
- `searchQuery` - Search filter

**Actions**:
- `loadConversations()` - Fetch list on mount
- `selectConversation(id)` - Load full conversation
- `createNewChat()` - Clear current, start fresh
- `deleteConversation(id)` - Delete and refresh
- `renameConversation(id, title)` - Update title

### 3. API Client Updates (`src/lib/api.js`)

Add methods:
- `listConversations()`
- `createConversation()`
- `getConversation(id)`
- `updateConversation(id, data)`
- `deleteConversation(id)`
- `searchConversations(query)`

## Implementation Order

1. **Backend storage service** (30 min)
   - Create conversations.py service
   - File read/write operations
   - Index management

2. **Backend REST endpoints** (20 min)
   - Create conversations router
   - Wire up to FastAPI app

3. **Auto-title generation** (15 min)
   - Add generate_title() using Haiku or free model
   - Call after first assistant response

4. **Frontend sidebar layout** (30 min)
   - Add sidebar container
   - Style conversation list
   - New chat button

5. **Frontend API integration** (20 min)
   - Add API methods
   - Load conversations on mount
   - Select/switch conversations

6. **Frontend search** (15 min)
   - Search input in sidebar
   - Filter/search API call

7. **WebSocket conversation tracking** (20 min)
   - Modify WebSocket to persist messages
   - Handle conversation_id

8. **Polish & test** (20 min)
   - Delete/rename UI
   - Edge cases
   - Mobile responsiveness

## Files to Create/Modify

**Create**:
- `compose/services/conversations.py`
- `compose/api/routers/conversations.py`
- `compose/data/conversations/index.json` (empty initial)

**Modify**:
- `compose/api/main.py` - Register new router
- `compose/api/routers/chat.py` - Add conversation tracking
- `compose/frontend/src/lib/api.js` - Add conversation methods
- `compose/frontend/src/routes/chat/+page.svelte` - Add sidebar

## Commit Strategy

1. `feat(backend): add conversation storage service`
2. `feat(backend): add conversations REST API`
3. `feat(backend): add auto-title generation`
4. `feat(frontend): add conversation sidebar layout`
5. `feat(frontend): integrate conversation API`
6. `feat(frontend): add conversation search`
7. `feat(chat): persist messages to conversations`
8. `feat(frontend): add rename/delete conversation actions`

Push after each commit.
