# Message Bus Implementation - Current State

## Feature: Celery + RabbitMQ Message Bus for Agent-Spike

### Context
Implementing a message-driven architecture to expose agent-spike Python 3.14 codebase to N8N workflows without Python version conflicts. This follows the architecture design in `.claude/ideas/message-bus/celery-rabbitmq-architecture.md`.

### Current State
- **Phase**: Planning → Implementation
- **Decision**: Celery + RabbitMQ chosen over alternatives (SimStudio, Flowise, Windmill)
- **Priority**: YouTube API rate limiting integration (10,000 units/day quota)

### Key Design Decisions

#### 1. Architecture Choice
After researching multiple workflow tools (SimStudio, Flowise, Windmill), chose Celery + RabbitMQ because:
- Full control over Python 3.14 environment
- Hot reload development workflow
- Battle-tested production stack
- Clean N8N integration via HTTP/AMQP

#### 2. YouTube API Rate Limiting
Critical requirement: Handle 10,000 units/day quota with adaptive rate limiting for burst patterns.

**Implementation approach**:
- SQLite quota tracker (persistent across restarts)
- Adaptive burst limiter for feast-or-famine patterns
- Prioritization system for important videos
- Fallback to cached data when quota exhausted

#### 3. Archive-First Pattern Integration
All expensive API calls archived before processing:
- YouTube Data API responses → `projects/data/archive/youtube/`
- LLM outputs → tracked with cost metadata
- Processing versions → tracked for reprocessing

### Implementation Checklist

#### Phase 1: Core Infrastructure
- [ ] Create `message_bus/` directory structure
- [ ] Set up docker-compose.dev.yml (RabbitMQ, Redis, Flower)
- [ ] Create tasks.py with basic Celery app
- [ ] Implement dev.sh launcher with hot reload

#### Phase 2: Agent Tasks
- [ ] Wrap lesson-001 YouTube agent as Celery task
- [ ] Wrap lesson-002 webpage agent as Celery task
- [ ] Wrap lesson-007 cache manager as Celery task
- [ ] Add smart router task for URL pattern matching

#### Phase 3: Rate Limiting
- [ ] Create SQLite quota tracker
- [ ] Implement adaptive burst limiter
- [ ] Add priority queue for important videos
- [ ] Create quota monitoring dashboard

#### Phase 4: N8N Integration
- [ ] Document HTTP API patterns via Flower
- [ ] Create example N8N workflows
- [ ] Test webhook callbacks
- [ ] Add monitoring alerts

### Files to Create
```
message_bus/
├── tasks.py              # Celery task definitions
├── celeryconfig.py       # Celery configuration
├── rate_limiter.py       # YouTube API quota management
├── docker-compose.dev.yml # Infrastructure
├── dev.sh                # Development launcher
└── requirements.txt      # celery[amqp], flower, redis
```

### Next Steps
1. Create message_bus directory structure
2. Implement basic Celery infrastructure
3. Add YouTube API rate limiting
4. Test with N8N workflows