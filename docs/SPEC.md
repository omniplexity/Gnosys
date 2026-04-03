# Project Overview

## Platform
- Built on: **OpenClaw** (v0.5+)
- Type: OpenClaw Plugin (memory + contextEngine slots)
- Language: TypeScript plugin wrapper + Python backend

> Implementation note: current native OpenClaw plugins are JS/TS modules loaded by the Gateway. For Gnosys, Python should be used as a backend service behind a small TS wrapper rather than as a standalone native plugin entrypoint.

## Vision
Gnosys is a unified intelligence framework for OpenClaw that combines:
- Multi-agent multi-layer pipeline orchestration
- Advanced multi-tier memory system
- Self-learning loop for continuous improvement

## Version
**v0.1** - Initial specification

## Status
In Progress

## Terminology

| Term | Definition |
|------|------------|
| **Tier** | Memory storage layer (Working, Episodic, Semantic, Archive) |
| **Type** | Memory classification (Conversational, Entity, Procedural, Factual, Emotional, Meta) |
| **Agent Role** | Function type in pipeline (Primary, Coordinator, Specialist, Worker) |
| **Skill** | Extracted reusable workflow from task execution |
| **Trajectory** | Complete record of a task's execution |
| **Consolidation** | Process of moving/summarizing memory between tiers |

## Version History

| Version | Date | Changes |
|---------|------|---------|
| 0.1.0 | 2024-01 | Initial specification |

---

# Architecture

## Plugin Architecture

Gnosys operates as an OpenClaw plugin that occupies two slots:
- `memory` - Primary memory backend
- `contextEngine` - Context injection and management

## Directory Structure

```
~/.openclaw/
├── gnosys/                      # Gnosys root
│   ├── config.json              # Gnosys configuration
│   ├── db/                      # SQLite databases
│   │   ├── gnosys.db            # Core data
│   │   └── vectors.db           # Vector embeddings
│   ├── memory/                  # Memory storage
│   │   ├── working/             # Working memory (in-memory)
│   │   ├── episodic/            # Episode storage
│   │   ├── semantic/            # Semantic knowledge
│   │   └── archive/             # Long-term archive
│   ├── agents/                  # Agent instances
│   ├── sessions/                # Session data
│   ├── cache/                   # Runtime cache
│   └── logs/                    # Gnosys logs
```

## OpenClaw Integration Points

| Hook/Slot | Integration |
|-----------|-------------|
| `memory` slot | Replace memory-core plugin |
| `contextEngine` slot | Custom context injection |
| `registerTool` | Gnosys CLI and tools |
| `registerHook` | Lifecycle hooks |
| `registerCommand` | Slash commands |

---

# Subsystem: Memory System

## Overview

Multi-tier, multi-layer memory system that replaces and extends OpenClaw's default memory. Designed for persistent cross-session memory with semantic retrieval, procedural skill storage, and metadata tracking.

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                      Memory Core                            │
├─────────────────────────────────────────────────────────────┤
│  Tier 1: Working   ←→  Tier 2: Episodic  ←→  Tier 3: Semantic│
│       ↓                                    ↓                │
│  Tier 4: Archive ←──────────────────────────────────────────│
└─────────────────────────────────────────────────────────────┘
```

## Memory Tiers

### Tier 1: Working Memory
- **Purpose**: Immediate context, current conversation
- **Storage**: In-memory (RAM)
- **Retention**: Current session only
- **Max Items**: Configurable (default: 50)
- **TTL**: Configurable (default: 60 minutes)
- **Features**: LRU eviction, automatic compression

### Tier 2: Episodic Memory
- **Purpose**: Session history, recent interactions
- **Storage**: SQLite + Vector index
- **Retention**: Configurable (default: 30 days)
- **Features**: Summarization, cross-session linking
- **Consolidation**: Auto-summarize older episodes after 7 days

### Tier 3: Semantic Memory
- **Purpose**: Entity knowledge, facts, relationships
- **Storage**: Vector DB (Chroma)
- **Retention**: Permanent until pruned
- **Features**: Entity extraction, knowledge graph, concept relationships
- **Consolidation**: 24-hour interval

### Tier 4: Archive
- **Purpose**: Long-term storage, historical data
- **Storage**: SQLite + Files (Markdown)
- **Retention**: Configurable (default: 365 days)
- **Features**: Compression, indexing, search
- **Auto-prune**: Optional based on relevance

## Memory Types

| Type | Description | Examples |
|------|-------------|----------|
| **Conversational** | Chat history, messages | User messages, responses |
| **Entity** | People, places, objects | Users, locations, items |
| **Procedural** | Skills and procedures learned from past tasks | Tool call patterns, task solutions |
| **Factual** | Verified information | Preferences, facts |
| **Emotional** | Sentiment, user state | Mood, tone |
| **Meta** | Memory about memory - staleness, consolidation state | Last access time, relevance scores |

## Persistent Long-Term Memory

### Semantic Memory
- **Purpose**: Deep knowledge storage with efficient retrieval
- **Storage**: Vector DB with embeddings
- **Retrieval**: Semantic similarity + keyword hybrid
- **Features**: 
  - Concept relationships (is-a, part-of, related-to)
  - Entity linking across sessions
  - Time-decay relevance scoring
- **Configuration**:
```json
{
  "semantic": {
    "storage": "chroma",
    "embeddings": {
      "provider": "local",
      "model": "sentence-transformers/all-MiniLM-L6-v2",
      "dimension": 384
    }
  }
}
```

### Procedural Memory
- **Purpose**: Skills and procedures learned from past tasks
- **Storage**: Structured task templates + code patterns
- **Features**:
  - Extract reusable workflows from successful tasks
  - Store tool call sequences that solved problems
  - Pattern matching for task classification
  - Automated skill generation (see Skill System)

### Meta Memory
- **Purpose**: Tracks memory state, staleness, and consolidation
- **Storage**: SQLite metadata tables
- **Features**:
  - Memory access timestamps
  - Staleness indicators (last accessed, relevance decay)
  - Consolidation status (needs consolidation, consolidated, archived)
  - Memory importance scoring
  - Automatic tier promotion/demotion

### Cross-Session Persistence
- All memory tiers survive session boundaries
- Daily memory consolidation at configurable intervals
- Memory snapshots for session recovery
- Export/import for backup and migration

## OpenClaw Memory Integration

Gnosys replaces OpenClaw's default memory system:

| OpenClaw Feature | Gnosys Equivalent |
|-----------------|-------------------|
| `memory-core` plugin | Gnosys memory tier |
| `memory_search` tool | Gnosys semantic search |
| `memory_get` tool | Gnosys retrieval |
| `MEMORY.md` | Gnosys semantic tier |
| `memory/YYYY-MM-DD.md` | Gnosys episodic tier |

## Tools

- `gnosys_search` - Semantic memory search
- `gnosys_store` - Explicit memory storage
- `gnosys_recall` - Context-aware retrieval
- `gnosys_memory_types` - List memory types
- `gnosys_stats` - Memory statistics

## Configuration

```json
{
  "memory": {
    "enabled": true,
    "tiers": {
      "working": {
        "max_items": 50,
        "ttl_minutes": 60
      },
      "episodic": {
        "retention_days": 30,
        "auto_summarize": true,
        "summarize_after_days": 7
      },
      "semantic": {
        "retention_days": -1,
        "auto_consolidate": true,
        "consolidation_interval_hours": 24
      },
      "archive": {
        "retention_days": 365,
        "auto_prune": true
      }
    },
    "embeddings": {
      "provider": "local",
      "model": "sentence-transformers/all-MiniLM-L6-v2"
    },
    "vector_db": {
      "type": "chroma",
      "persist_directory": "~/.openclaw/gnosys/vectors"
    }
  }
}
```

---

# Subsystem: Multi-Agent Pipeline

## Overview

The multi-agent pipeline orchestrates multiple specialized agents that work together to handle complex tasks.

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    Pipeline Controller                      │
├─────────────────────────────────────────────────────────────┤
│  Input → Router → Agent 1 → Agent 2 → ... → Agent N → Output│
│              ↑                                              │
│          Feedback Loop                                      │
└─────────────────────────────────────────────────────────────┘
```

## Agent Types

| Type | Purpose | Use Case |
|------|---------|----------|
| **Primary** | Main orchestrator, handles user interaction | Default handling |
| **Specialist** | Domain-specific tasks | Code review, research |
| **Worker** | Execute specific subtasks | Data processing |
| **Coordinator** | Manages sub-agents | Task delegation |

## Pipeline Flow

1. **Input Received** - Message enters Gnosys
2. **Router** - Determines if single or multi-agent
3. **Agent Selection** - Choose appropriate agents
4. **Execution** - Run agent(s) with context
5. **Aggregation** - Combine results
6. **Output** - Return response

## OpenClaw Integration

- Spawn sub-agents via `sessions_spawn` tool
- Use `sessions_send` for inter-agent communication
- Leverage OpenClaw's existing agent system

## Configuration

```json
{
  "pipeline": {
    "enabled": true,
    "default_agent": "primary",
    "max_depth": 3,
    "timeout_ms": 30000,
    "agents": {
      "primary": {
        "type": "primary",
        "model": "default",
        "description": "Main orchestration agent"
      },
      "specialist": {
        "type": "specialist",
        "model": "default",
        "description": "Domain expert agents"
      }
    }
  }
}
```

## Parallel Sub-Agents

### Spawning
- Ability to spawn multiple sub-agents with isolated contexts
- Each sub-agent has its own memory space, tools, and session
- Parent agent can coordinate multiple sub-agents simultaneously

### Isolation
- Sub-agents operate in isolated contexts
- No direct memory sharing (parent can share context explicitly)
- Tool access can be restricted per sub-agent
- Independent conversation history

### Use Cases
- Parallel research on multiple topics
- Multiple worker agents processing subtasks
- Independent specialists working on different aspects

### Implementation
```python
# Spawn parallel sub-agents
await gnosys.spawn(
    agent_id="worker_1",
    role="researcher",
    context={"topic": "LLM trends"},
    tools=["web_search", "web_fetch", "read"]
)
await gnosys.spawn(
    agent_id="worker_2", 
    role="coder",
    context={"task": "implement feature"},
    tools=["read", "write", "edit", "exec"]
)

# Wait for completion
results = await gnosys.wait_for_agents(["worker_1", "worker_2"])
```

## Multi-Agent Profiles

### Profile Definition
```json
{
  "profiles": {
    "development": {
      "agents": [
        {"id": "architect", "role": "coordinator", "weight": 1.0},
        {"id": "coder", "role": "worker", "weight": 2.0},
        {"id": "reviewer", "role": "specialist", "weight": 1.0}
      ],
      "coordination": "sequential"
    },
    "research": {
      "agents": [
        {"id": "lead", "role": "coordinator", "weight": 1.0},
        {"id": "web_searcher", "role": "worker", "weight": 1.0},
        {"id": "analyst", "role": "specialist", "weight": 1.0}
      ],
      "coordination": "parallel"
    }
  }
}
```

### Role-Based Coordination

| Role | Responsibility | Communication |
|------|---------------|---------------|
| **Coordinator** | Task breakdown, result aggregation | Receives output from all agents |
| **Worker** | Execute specific subtasks | Reports to coordinator |
| **Specialist** | Domain expertise | Provides recommendations |
| **Primary** | User interface, final output | Orchestrates all roles |

### Coordination Patterns

| Pattern | Description | Use Case |
|---------|-------------|----------|
| **Sequential** | Agent A → Agent B → Agent C | Pipeline tasks |
| **Parallel** | Agent A, B, C simultaneously | Independent subtasks |
| **Hierarchical** | Coordinator manages workers | Complex projects |
| **Debate** | Multiple agents propose, vote on best | Decision making |

## Parallel Autonomous Task Execution

- Multiple agents can execute tasks autonomously and in parallel
- Results aggregated when all complete or on first success
- Timeout handling for long-running tasks
- Error handling and retry logic per agent

---

# Subsystem: Scheduled Automation

## Overview

Built-in cron-like scheduler for autonomous recurring tasks with the ability to execute tasks and deliver results without user prompting.

## Scheduler Features

| Feature | Description |
|---------|-------------|
| **Cron Expressions** | Standard cron syntax for scheduling |
| **One-shot** | Single task at specific time |
| **Interval** | Repeating tasks (every X minutes/hours) |
| **Conditional** | Run when conditions are met |
| **Chained** | Task triggers next task |

## Scheduling Options

### Cron Syntax
```
┌───────────── minute (0 - 59)
│ ┌─────────── hour (0 - 23)
│ │ ┌───────── day of month (1 - 31)
│ │ │ ┌─────── month (1 - 12)
│ │ │ │ ┌───── day of week (0 - 6)
│ │ │ │ │
* * * * *
```

### Common Patterns
| Pattern | Example | Description |
|---------|---------|-------------|
| **Hourly** | `0 * * * *` | Every hour at minute 0 |
| **Daily** | `0 9 * * *` | Every day at 9 AM |
| **Weekly** | `0 9 * * 1` | Every Monday at 9 AM |
| **Interval** | `@every 30m` | Every 30 minutes |

## Task Types

| Type | Description | Delivery |
|------|-------------|----------|
| **Query** | Run search/query, return results | Message, webhook |
| **Action** | Execute tool/agent operation | Status, webhook |
| **Report** | Compile and send report | Email, message |
| **Check** | Health check, monitoring | Alert, log |

## Autonomous Execution

### Without User Prompting
- Tasks run on schedule without user interaction
- Results delivered via configured channel
- Can include context from memory

### Delivery Options
```json
{
  "delivery": {
    "announce": true,           // Post in chat
    "webhook": "https://...",   // POST to URL
    "email": "user@example.com", // Send email (if configured)
    "none": false               // Silent execution
  }
}
```

## Task Definition

```json
{
  "tasks": {
    "morning_briefing": {
      "schedule": "0 8 * * *",
      "enabled": true,
      "description": "Daily morning summary",
      "type": "report",
      "action": {
        "query_memory": true,
        "include_context": ["episodic", "semantic"],
        "compile": "summary"
      },
      "delivery": {
        "announce": true,
        "webhook": null
      }
    },
    "health_check": {
      "schedule": "@every 15m",
      "enabled": true,
      "type": "check",
      "action": {
        "checks": ["disk_space", "memory_usage", "openclaw_status"]
      },
      "delivery": {
        "announce": false,
        "alert_on_failure": true
      }
    }
  }
}
```

## Heartbeat Integration

Gnosys can use OpenClaw's heartbeat system for lightweight scheduling:
- Leverage existing heartbeat infrastructure
- Combine with Gnosys-specific tasks
- Unified task management

## Configuration

```json
{
  "scheduler": {
    "enabled": true,
    "max_concurrent": 5,
    "timeout_seconds": 300,
    "retry": {
      "enabled": true,
      "max_attempts": 3,
      "backoff": "exponential"
    },
    "persistence": {
      "store_completed": true,
      "retention_days": 30
    }
  }
}
```

## Tools

- `gnosys_schedule_list` - List scheduled tasks
- `gnosys_schedule_create` - Create new task
- `gnosys_schedule_edit` - Modify task
- `gnosys_schedule_delete` - Remove task
- `gnosys_schedule_run` - Run task immediately
- `gnosys_schedule_history` - View execution history

---

# Subsystem: Model-Agnostic LLM Integration

## Overview

Gnosys supports multiple LLM providers and can dynamically switch models, including local models. This provides flexibility in model selection without being tied to a single provider.

## Supported Providers

### Cloud Providers
| Provider | Models | API Type |
|----------|--------|----------|
| **OpenAI** | GPT-4, GPT-4 Turbo, GPT-3.5 Turbo | REST |
| **Anthropic** | Claude 3 Opus, Sonnet, Haiku | REST |
| **Google** | Gemini Pro, Ultra | REST |
| **Together AI** | Various open-source models | REST |
| **Cohere** | Command, Embed | REST |

### Local Providers
| Provider | Models | Requirements |
|----------|--------|---------------|
| **Ollama** | Llama 2, Mistral, Codellama | Local server |
| **LM Studio** | GGUF format models | Local server |
| **LocalAI** | Various | Local server |
| **KiloCode** | Custom models | Custom endpoint |

## Model Switching

### Dynamic Model Selection
```python
# Switch model at runtime
await gnosys.set_model("claude-3-sonnet")

# Switch based on task type
model_for_task = {
    "coding": "gpt-4",
    "reasoning": "claude-3-opus",
    "fast": "claude-3-haiku",
    "local": "llama2:7b"
}
result = await gnosys.execute(task, model=model_for_task[task.type])
```

### Model Configuration
```json
{
  "models": {
    "default": "claude-3-sonnet",
    "fallback": "gpt-3.5-turbo",
    "mapping": {
      "coding": "gpt-4",
      "analysis": "claude-3-opus",
      "quick": "claude-3-haiku"
    }
  }
}
```

## Provider Interface

### Abstract Provider
```python
class LLMProvider(ABC):
    @abstractmethod
    async def complete(self, prompt: str, **kwargs) -> str:
        pass
    
    @abstractmethod
    async def embed(self, text: str) -> List[float]:
        pass
    
    @abstractmethod
    def get_available_models(self) -> List[str]:
        pass
```

### Provider Implementation
- Each provider implements the abstract interface
- Automatic retry with exponential backoff
- Rate limiting per provider
- Token usage tracking

## Fallback Strategy

If a model fails:
1. Log error
2. Try fallback model (if configured)
3. If all fail, return error with options

```json
{
  "llm": {
    "primary": "claude-3-sonnet",
    "fallback": "gpt-3.5-turbo",
    "local_fallback": "llama2:7b",
    "retry": {
      "max_attempts": 3,
      "backoff_seconds": 2
    }
  }
}
```

## Embeddings

Gnosys can use different embeddings providers:
```json
{
  "embeddings": {
    "provider": "local",  // local, openai, anthropic
    "model": "sentence-transformers/all-MiniLM-L6-v2",
    "dimension": 384,
    "fallback": "text-embedding-3-small"
  }
}
```

## OpenClaw Integration

Gnosys can leverage OpenClaw's existing LLM providers:
- Use OpenClaw's provider configuration
- Add additional providers as needed
- Unified interface across all providers

---

# Subsystem: Self-Learning Loop (Memory-Driven)
- **Purpose**: Tracks memory state, staleness, and consolidation
- **Storage**: SQLite metadata tables
- **Features**:
  - Memory access timestamps
  - Staleness indicators (last accessed, relevance decay)
  - Consolidation status (needs consolidation, consolidated, archived)
  - Memory importance scoring
  - Automatic tier promotion/demotion

### Cross-Session Persistence
- All memory tiers survive session boundaries
- Daily memory consolidation at configurable intervals
- Memory snapshots for session recovery
- Export/import for backup and migration

## OpenClaw Memory Integration

Gnosys replaces OpenClaw's default memory system:

| OpenClaw Feature | Gnosys Equivalent |
|-----------------|-------------------|
| `memory-core` plugin | Gnosys memory tier |
| `memory_search` tool | Gnosys semantic search |
| `memory_get` tool | Gnosys retrieval |
| `MEMORY.md` | Gnosys semantic tier |
| `memory/YYYY-MM-DD.md` | Gnosys episodic tier |

## Tools

- `gnosys_search` - Semantic memory search
- `gnosys_store` - Explicit memory storage
- `gnosys_recall` - Context-aware retrieval
- `gnosys_memory_types` - List memory types
- `gnosys_stats` - Memory statistics

## Configuration

```json
{
  "memory": {
    "enabled": true,
    "tiers": {
      "working": {
        "max_items": 50,
        "ttl_minutes": 60
      },
      "episodic": {
        "retention_days": 30,
        "auto_summarize": true,
        "summarize_after_days": 7
      },
      "semantic": {
        "retention_days": -1,
        "auto_consolidate": true,
        "consolidation_interval_hours": 24
      },
      "archive": {
        "retention_days": 365,
        "auto_prune": true
      }
    },
    "embeddings": {
      "provider": "local",
      "model": "sentence-transformers/all-MiniLM-L6-v2"
    },
    "vector_db": {
      "type": "chroma",
      "persist_directory": "~/.openclaw/gnosys/vectors"
    }
  }
}
```

---

# Subsystem: Autonomous Skill System

## Overview

Gnosys automatically creates, refines, and manages reusable skills from past tasks, enabling continuous skill compounding over time.

## Skill Lifecycle

```
┌─────────────────────────────────────────────────────────────┐
│                    Skill Lifecycle                           │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  ┌─────────┐    ┌──────────┐    ┌─────────┐    ┌────────┐ │
│  │ Detect  │ →  │ Extract  │ →  │ Store   │ →  │ Refine │ │
│  └─────────┘    └──────────┘    └─────────┘    └────────┘ │
│       ↑                                                │    │
│       └────────────────── Loop ──────────────────────────┘   │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

## Skill Detection

### Triggers
- **Repeated patterns**: Same tool sequence used 3+ times
- **Successful solutions**: Task completed successfully, extract workflow
- **User request**: Explicit "/skill create" command
- **Template matching**: Common task structures detected

### Analysis
- Task context and goal
- Tool sequence used
- Parameters and variations
- Success/failure outcomes
- Frequency of reuse

## Skill Extraction

### What Gets Extracted
- Tool call sequences
- Parameter patterns
- Conditional logic
- Error handling patterns
- Success indicators

### Skill Format (SKILL.md Compatible)
```markdown
# Skill: Code Review

## Triggers
- Code review requests
- PR review tasks

## Workflow
1. Read changed files
2. Run linter/static analysis
3. Identify potential issues
4. Suggest improvements

## Tools
- read, exec, glob

## Parameters
- {repo_path}: Repository location
- {branch}: Branch to review
```

## Skill Storage

### Location
```
~/.openclaw/gnosys/skills/
├── code_review/
│   ├── SKILL.md
│   ├── metadata.json
│   └── examples/
├── github_issues/
│   ├── SKILL.md
│   └── ...
```

### Metadata
```json
{
  "name": "code_review",
  "version": "1.0.0",
  "created": "2024-01-15T10:30:00Z",
  "last_used": "2024-01-20T14:22:00Z",
  "use_count": 42,
  "success_rate": 0.95,
  "trigger_count": 3,
  "compounds_from": ["git_diff", "lint_check"]
}
```

## Skill Refinement

### Compounding
- Skills can build on other skills
- Detect skill dependencies
- Merge similar skills
- Version skills as they evolve

### Refinement Triggers
- New successful patterns emerge
- Partial skill matches found
- User provides corrections
- Success rate drops below threshold

### Versioning
- Semantic versioning for skills
- Rollback capability
- A/B testing for skill variants

## Skill Sharing (Future)

- Export skill as bundle
- Import from Gnosys skill library
- Community skill marketplace (optional)

## OpenClaw Skills Integration

Gnosys skills are OpenClaw-compatible:
- Follow AgentSkills `SKILL.md` format
- Discoverable via OpenClaw skill system
- Can be taught to other agents

## Configuration

```json
{
  "skills": {
    "enabled": true,
    "auto_detect": true,
    "detection": {
      "min_pattern_count": 3,
      "success_threshold": 0.8,
      "min_task_complexity": "medium"
    },
    "extraction": {
      "include_parameters": true,
      "include_context": true,
      "include_examples": 5
    },
    "storage": {
      "directory": "~/.openclaw/gnosys/skills",
      "max_skills": 100,
      "auto_cleanup": true,
      "delete_below_success_rate": 0.5
    },
    "refinement": {
      "enabled": true,
      "auto_compound": true,
      "merge_similar": true,
      "versioning": "semantic"
    }
  }
}
```

## Tools

- `gnosys_skills_list` - List all skills
- `gnosys_skills_create` - Manual skill creation
- `gnosys_skills_edit` - Edit existing skill
- `gnosys_skills_delete` - Remove skill
- `gnosys_skills_use` - Invoke skill for task

---

# Subsystem: Self-Learning Loop

## Overview

Continuous learning system that improves Gnosys based on interactions, outcomes, and feedback.

## Learning Mechanisms

### 1. Interaction Learning
- Track successful patterns
- Identify effective strategies
- Learn user preferences implicitly

### 2. Outcome Feedback
- Monitor tool execution success
- Track agent pipeline effectiveness
- Measure response quality

### 3. Explicit Feedback
- User corrections
- Rating/thumbs up/down
- Manual training data

## Learning Cycle

```
┌─────────────────────────────────────────────────────────────┐
│                    Self-Learning Loop                        │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  ┌─────────┐    ┌──────────┐    ┌────────────┐            │
│  │ Observe │ →  │ Analyze  │ →  │ Adapt      │            │
│  └─────────┘    └──────────┘    └────────────┘            │
│       ↑                                               │     │
│       └──────────────── Feedback ───────────────────────┘   │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

### Observe
- Capture interactions
- Record outcomes
- Track tool success rates

### Analyze
- Identify patterns
- Detect failures
- Measure effectiveness

### Adapt
- Update agent strategies
- Refine memory importance
- Adjust retrieval weights

## Learning Targets

| Target | What It Learns |
|--------|---------------|
| **Agent Strategies** | Which agents to use when |
| **Retrieval Weights** | Memory relevance scoring |
| **User Preferences** | Communication style, topics |
| **Tool Selection** | Best tools for task types |
| **Response Patterns** | Effective response formats |
| **Skill Refinement** | Optimize skill workflows |

## Trajectory Logging

### What Gets Logged
- Full task execution traces
- Tool calls with parameters and results
- Agent decisions and reasoning
- Context at each step
- Outcome success/failure

### Log Format
```json
{
  "trajectory_id": "task_2024_01_15_10_30_42",
  "task": "Review code in repo",
  "started_at": "2024-01-15T10:30:00Z",
  "completed_at": "2024-01-15T10:45:00Z",
  "success": true,
  "agents": ["primary", "specialist"],
  "steps": [
    {
      "step": 1,
      "agent": "primary",
      "action": "read_files",
      "params": {"files": ["src/main.py"]},
      "result": {"content": "..."},
      "duration_ms": 1200
    }
  ],
  "metrics": {
    "total_steps": 5,
    "total_duration_ms": 90000,
    "tool_calls": 12,
    "errors": 0
  }
}
```

### Storage
- Location: `~/.openclaw/gnosys/logs/trajectories/`
- Format: JSONL (one trajectory per line)
- Retention: Configurable (default: 90 days)
- Compression: Automatic after 7 days

## Dataset Generation

### Purpose
Generate training datasets from successful task executions for:
- Fine-tuning models
- RLHF (Reinforcement Learning from Human Feedback)
- Skill extraction
- Pattern analysis

### Dataset Types
| Type | Description | Use Case |
|------|-------------|----------|
| **Task-Response** | Input task → Output response | Fine-tuning |
| **Tool-Workflow** | Task → Tool sequence | Skill extraction |
| **Context-Relevance** | Query + Context → Relevant memories | Retrieval training |
| **Agent-Decision** | Situation → Agent choice | Strategy learning |

### Generation Pipeline
1. Filter successful trajectories (success_rate > 0.8)
2. Extract relevant data points
3. Format according to target use case
4. Store in `~/.openclaw/gnosys/datasets/`
5. Optionally export for external training

### Configuration
```json
{
  "datasets": {
    "enabled": true,
    "generation": {
      "success_threshold": 0.8,
      "min_trajectories": 100,
      "export_formats": ["jsonl", "arrow"]
    },
    "types": {
      "task_response": {
        "enabled": true,
        "output": "~/.openclaw/gnosys/datasets/task_response"
      },
      "tool_workflow": {
        "enabled": true,
        "output": "~/.openclaw/gnosys/datasets/tool_workflow"
      },
      "context_relevance": {
        "enabled": false,
        "output": "~/.openclaw/gnosys/datasets/context_relevance"
      }
    }
  }
}
```

## Reinforcement Learning Integration

### RL Loop
```
Task → Agent → Outcome → Reward → Update Strategy → Task
```

### Reward Signals
| Signal | Source | Weight |
|--------|--------|--------|
| Task Success | Outcome matches goal | 1.0 |
| Efficiency | Fewer steps = higher reward | 0.3 |
| Tool Efficiency | Fewer tool calls = higher | 0.2 |
| User Feedback | Thumbs up/down | 0.5 |
| Error Rate | Fewer errors = higher | 0.4 |

### Strategy Updates
- Track success rates per agent/strategy
- Weight selection toward higher-performing options
- Explore new strategies (epsilon-greedy)
- Confidence bounds for exploration

### Integration Points
- Hook into task completion for reward calculation
- Update agent strategy weights periodically
- Store learned strategies in memory
- Export strategy data for external RL training

## OpenClaw Integration

- Hook into `after_tool_call` for tool feedback
- Hook into `session:compact:after` for learning
- Use `sessions_history` for pattern analysis

## Configuration

```json
{
  "learning": {
    "enabled": true,
    "mode": "passive",  // passive, active, hybrid
    "observe": {
      "track_interactions": true,
      "track_outcomes": true,
      "track_tool_usage": true,
      "track_response_quality": true
    },
    "analyze": {
      "pattern_detection": true,
      "failure_detection": true,
      "interval_minutes": 60
    },
    "adapt": {
      "update_strategies": true,
      "update_retrieval": true,
      "update_preferences": true,
      "threshold": 0.8
    },
    "feedback": {
      "explicit_required": false,
      "implicit_weight": 0.3
    }
  }
}
```

---

# Context Engine

## Overview

Custom context engine that replaces OpenClaw's legacy context engine to build prompts with Gnosys memory.

## Context Flow

```
Query → Semantic Search → Memory Retrieval → Context Assembly → Prompt
```

## Retrieval Strategy

1. **Query Analysis** - Parse user intent
2. **Memory Search** - Semantic + keyword hybrid
3. **Relevance Scoring** - Multi-factor ranking
4. **Context Assembly** - Combine and truncate
5. **Prompt Injection** - Insert into system prompt

## Context Components

| Component | Source | Priority |
|-----------|--------|----------|
| Working Memory | Tier 1 | Highest |
| Recent Episodes | Tier 2 | High |
| Entity Knowledge | Tier 3 | Medium |
| User Profile | Semantic | High |
| System Memory | Archive | Low |

## Token Management

- Configurable max tokens (default: 4000)
- Priority-based allocation
- Automatic truncation

## Configuration

```json
{
  "context": {
    "enabled": true,
    "max_tokens": 4000,
    "include_tiers": ["working", "episodic", "semantic"],
    "priority_weights": {
      "working": 1.0,
      "episodic": 0.8,
      "semantic": 0.5,
      "archive": 0.2
    },
    "retrieval": {
      "semantic_weight": 0.7,
      "keyword_weight": 0.3,
      "temporal_decay": true
    }
  }
}
```

---

# OpenClaw Compliance

> Implementation correction: the runtime plugin must be authored as a JS/TS OpenClaw plugin with `openclaw.plugin.json` for manifest validation and a package entry declared through `package.json` `openclaw.extensions`. Python remains a backend implementation detail.

## Plugin Manifest

Gnosys must include `openclaw.plugin.json` for plugin discovery:

> Note: the example below reflects intent, not the exact current schema. In implementation, use current OpenClaw manifest fields such as `id`, `kind`, and `configSchema`, and register runtime behavior from the TS entrypoint via `definePluginEntry(...)`.

```json
{
  "name": "gnosys",
  "version": "0.1.0",
  "description": "Multi-agent pipeline, memory system, and self-learning framework",
  "author": "Gnosys",
  "openclaw_min_version": "0.5.0",
  "slots": {
    "memory": {
      "required": true,
      "description": "Primary memory backend"
    },
    "contextEngine": {
      "required": false,
      "description": "Context injection engine"
    }
  },
  "hooks": [
    "session:start",
    "session:end",
    "message:received",
    "message:sent",
    "before_tool_call",
    "after_tool_call"
  ],
  "tools": [
    "gnosys_search",
    "gnosys_store",
    "gnosys_recall",
    "gnosys_stats"
  ],
  "config_schema": {
    "type": "object",
    "properties": {
      "pipeline": { "type": "object" },
      "memory": { "type": "object" },
      "learning": { "type": "object" },
      "context": { "type": "object" }
    }
  }
}
```

## Version Compatibility

| Gnosys Version | OpenClaw Version |
|---------------|------------------|
| 0.1.x | 0.5.x - 0.6.x |

## Fallback Strategy

If Gnosys fails:
1. Log error to `~/.openclaw/gnosys/logs/error.log`
2. Fall back to OpenClaw default memory
3. Return error to user
4. Continue operation in degraded mode

## Update Resilience

- Semantic versioning for Gnosys releases
- Adapter pattern for OpenClaw internals
- Configuration versioning in `config.json`
- Migration scripts for schema changes

---

# Subsystem: Security

## Overview

Security features for protecting data, managing access, and safely executing agent operations.

## Data Security

### Encryption at Rest
```json
{
  "security": {
    "encryption": {
      "enabled": true,
      "algorithm": "AES-256-GCM",
      "key_storage": "system_keychain"
    }
  }
}
```
- SQLite database encryption
- Vector store encryption
- File encryption for sensitive data

### API Key Management
```json
{
  "security": {
    "secrets": {
      "storage": "system_keychain",  // or env, custom
      "providers": {
        "openai": "gnosys_openai_key",
        "anthropic": "gnosys_anthropic_key"
      }
    }
  }
}
```
- Secure storage in system keychain
- Environment variable fallback
- No plaintext secrets in config

## Agent Sandboxing

### Sub-Agent Isolation
```json
{
  "security": {
    "sandbox": {
      "enabled": true,
      "sub_agent": {
        "network_access": false,
        "file_system": "restricted",
        "allowed_paths": ["~/workspace", "~/.openclaw/gnosys/temp"]
      }
    }
  }
}
```
- Network access control
- File system restrictions
- Tool access limitations per agent
- Resource limits (memory, CPU)

### Execution Approval
```json
{
  "security": {
    "exec_approval": {
      "enabled": true,
      "auto_approve_safe": true,
      "dangerous_tools": ["exec", "process", "browser"],
      "require_approval": ["shell", "delete"]
    }
  }
}
```

---

# Subsystem: Monitoring & Observability

## Overview

Metrics, health checks, and dashboards for monitoring Gnosys operation.

## Metrics

### What Gets Measured
| Metric | Description |
|--------|-------------|
| **Request Latency** | Time for memory searches, context builds |
| **Agent Latency** | Multi-agent pipeline execution time |
| **Tool Usage** | Tools called per task, success rates |
| **Memory Stats** | Items per tier, storage size |
| **Learning** | Pattern detection rate, adaptation frequency |
| **Scheduler** | Task execution times, success rates |

### Metrics Storage
```json
{
  "monitoring": {
    "metrics": {
      "enabled": true,
      "backend": "prometheus",  // or sqlite, statsd
      "port": 9090,
      "retention_days": 30
    }
  }
}
```

## Health Checks

### Built-in Checks
- Database connectivity
- Vector store availability
- Memory tier health
- Agent pool status
- Scheduler health
- OpenClaw connection

### Health Endpoint
```
GET /__gnosys__/health
```

Response:
```json
{
  "status": "healthy",
  "components": {
    "database": "ok",
    "vector_store": "ok",
    "memory_tiers": "ok",
    "agents": "ok",
    "scheduler": "ok"
  },
  "metrics": {
    "requests_total": 1234,
    "errors_total": 5,
    "avg_latency_ms": 45
  }
}
```

## Dashboard

### Metrics Dashboard
- Visual charts for all metrics
- Alert configuration
- Performance trends

### Access
```json
{
  "monitoring": {
    "dashboard": {
      "enabled": true,
      "port": 8765,
      "auth_required": true
    }
  }
}
```

---

# Subsystem: Backup & Recovery

## Overview

Export, import, migration tools, and disaster recovery capabilities.

## Backup

### Full Backup
```bash
gnosys backup --output ~/backups/gnosys-2024-01-15.tar.gz
```
Includes:
- SQLite databases
- Vector stores
- Configuration
- Skills
- Trajectory logs

### Incremental Backup
- Only changed data since last backup
- Configurable schedule

### Selective Backup
```bash
# Backup only memory
gnosys backup --type memory --output memory.tar.gz

# Backup only skills
gnosys backup --type skills --output skills.tar.gz
```

## Recovery

### Restore from Backup
```bash
gnosys restore --input ~/backups/gnosys-2024-01-15.tar.gz
```

### Point-in-Time Recovery
- Restore to specific timestamp
- Useful for error recovery

## Migration

### Export Format
```json
{
  "version": "1.0.0",
  "exported_at": "2024-01-15T10:30:00Z",
  "components": ["memory", "skills", "config"],
  "checksum": "sha256:..."
}
```

### Migration Between Versions
```bash
gnosys migrate --from 0.1.0 --to 0.2.0
```

### OpenClaw Migration
- Migrate from default memory to Gnosys
- Import existing MEMORY.md files

## Disaster Recovery

### Backup Rotation
```json
{
  "backup": {
    "schedule": "daily",
    "retention": {
      "daily": 7,
      "weekly": 4,
      "monthly": 12
    },
    "location": "~/backups/gnosys"
  }
}
```

### Remote Backup (Optional)
- Cloud storage integration
- Off-site backup

---

# Subsystem: External API

## Overview

REST API for external access and programmatic control of Gnosys.

## API Endpoints

### Memory
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/memory/search` | Search memory |
| POST | `/api/memory/store` | Store memory |
| GET | `/api/memory/{id}` | Get memory item |
| DELETE | `/api/memory/{id}` | Delete memory |

### Agents
| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/agents/spawn` | Spawn sub-agent |
| GET | `/api/agents` | List agents |
| POST | `/api/agents/{id}/execute` | Execute task |

### Skills
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/skills` | List skills |
| POST | `/api/skills` | Create skill |
| PUT | `/api/skills/{id}` | Update skill |
| DELETE | `/api/skills/{id}` | Delete skill |

### Scheduler
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/scheduled` | List scheduled tasks |
| POST | `/api/scheduled` | Create task |
| POST | `/api/scheduled/{id}/run` | Run task immediately |

### System
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/health` | Health check |
| GET | `/api/metrics` | Get metrics |
| POST | `/api/config/reload` | Reload configuration |

## API Configuration

```json
{
  "api": {
    "enabled": true,
    "host": "127.0.0.1",
    "port": 8766,
    "auth": {
      "type": "bearer",  // or basic, api_key
      "token": "gnosys_api_token"
    },
    "cors": {
      "enabled": true,
      "allowed_origins": ["http://localhost:3000"]
    },
    "rate_limit": {
      "enabled": true,
      "requests_per_minute": 60
    }
  }
}
```

## SDK

### Python SDK
```python
import gnosys

client = gnosys.Client(api_key="...")

# Search memory
results = client.memory.search("query")

# Execute agent
result = client.agents.execute(task="review code")
```

---

# Subsystem: Testing

## Overview

Testing strategy including unit tests, integration tests, and performance benchmarks.

## Test Types

### Unit Tests
- Individual component testing
- Mock external dependencies
- Test coverage targets

| Component | Coverage Target |
|-----------|-----------------|
| Memory Tiers | 90%+ |
| Pipeline | 85%+ |
| Scheduler | 90%+ |
| Skills | 85%+ |
| Learning | 80%+ |

### Integration Tests
- OpenClaw integration
- Database connectivity
- Tool execution
- Agent spawning

### End-to-End Tests
- Full task execution
- Memory persistence
- Scheduler execution

## Test Infrastructure

### Test Configuration
```json
{
  "testing": {
    "enabled": true,
    "coverage": {
      "enabled": true,
      "min_coverage": 80,
      "report_format": "html"
    },
    "fixtures": {
      "mock_llm": true,
      "mock_vector_store": true,
      "test_data_path": "~/.openclaw/gnosys/tests/fixtures"
    }
  }
}
```

### Test Databases
- Separate test databases
- Automatic cleanup after tests
- Fixtures for common scenarios

## Performance Testing

### Benchmarks
```bash
# Run benchmarks
gnosys bench --suite memory

# Results
Memory Search: 45ms avg (p95: 120ms)
Context Build: 230ms avg (p95: 500ms)
Agent Spawn: 1.2s avg (p95: 3s)
```

### Load Testing
```bash
# Simulate concurrent requests
gnosys load-test --users 10 --duration 60s
```

### Performance Targets
| Metric | Target |
|--------|--------|
| Memory search | < 100ms (p95) |
| Context build | < 500ms (p95) |
| Agent spawn | < 2s (p95) |
| Scheduler tick | < 50ms |

---

# Subsystem: Performance Optimization

## Overview

Caching, batch processing, and memory optimization strategies.

## Caching

### Memory Cache
```json
{
  "performance": {
    "cache": {
      "enabled": true,
      "type": "memory",
      "max_size_mb": 512,
      "ttl_seconds": 3600,
      "strategies": {
        "semantic_search": "lru",
        "context": "ttl",
        "agent_results": "lru"
      }
    }
  }
}
```

### Cache Layers
1. **Query Cache** - Recent semantic searches
2. **Context Cache** - Built contexts for similar queries
3. **Agent Cache** - Sub-agent results for idempotent tasks
4. **Vector Cache** - Embedding cache

## Batch Processing

### Batch Operations
- Batch memory inserts
- Batch vector indexing
- Batch skill extraction

```python
# Batch memory store
await gnosys.memory.store_batch([
    {"type": "conversational", "content": "..."},
    {"type": "entity", "content": "..."},
])
```

### Parallel Processing
- Parallel agent execution
- Parallel memory retrieval
- Parallel vector searches

## Memory Optimization

### Working Memory
- LRU eviction
- Automatic compression
- Tier promotion thresholds

### Database Optimization
- Index maintenance
- Query optimization
- Vacuum scheduling

```json
{
  "performance": {
    "database": {
      "auto_vacuum": true,
      "cache_size_mb": 256,
      "wal_mode": true
    }
  }
}
```

---

# Subsystem: Tool Registry

## Overview

Dynamic tool loading, versioning, and discovery for Gnosys tools.

## Tool Registration

### Built-in Tools
- Auto-registered on Gnosys startup
- Version tracked

### External Tools
```json
{
  "tools": {
    "registry": {
      "scan_paths": [
        "~/.openclaw/gnosys/tools",
        "~/workspace/tools"
      ],
      "auto_load": true
    }
  }
}
```

## Tool Definition

### Manifest (tool.json)
```json
{
  "name": "custom_tool",
  "version": "1.0.0",
  "description": "Custom tool description",
  "parameters": {
    "type": "object",
    "properties": {...}
  },
  "returns": {
    "type": "object"
  },
  "requires": ["read"],
  "capabilities": ["file_ops"]
}
```

## Tool Versioning

- Semantic versioning per tool
- Dependency resolution
- Rollback capability

## Tool Discovery

```python
# List available tools
tools = await gnosys.tools.list()

# Find tools by capability
coding_tools = await gnosys.tools.find(capability="code_execution")

# Check tool compatibility
gnosys.tools.check_compatibility("custom_tool", "1.0.0")
```

---

# Subsystem: Error Handling

## Overview

Error codes, retry policies, and circuit breakers for resilient operation.

## Error Codes

| Code | Category | Description |
|------|----------|-------------|
| 1000-1099 | Memory | Memory tier errors |
| 1100-1199 | Pipeline | Agent/pipeline errors |
| 1200-1299 | Skills | Skill system errors |
| 1300-1399 | Learning | Learning system errors |
| 1400-1499 | Scheduler | Scheduling errors |
| 1500-1599 | External | API/tool errors |

## Retry Policies

### Configuration
```json
{
  "error_handling": {
    "retry": {
      "enabled": true,
      "max_attempts": 3,
      "backoff": {
        "type": "exponential",  // or linear, fixed
        "base_seconds": 1,
        "max_seconds": 30
      },
      "retryable_errors": ["timeout", "rate_limit", "temporary_failure"]
    }
  }
}
```

### Per-Operation Override
```python
await gnosys.memory.search(
    query="...",
    retry={"max_attempts": 5, "backoff": "linear"}
)
```

## Circuit Breaker

### Configuration
```json
{
  "error_handling": {
    "circuit_breaker": {
      "enabled": true,
      "failure_threshold": 5,
      "recovery_timeout_seconds": 60,
      "half_open_max_calls": 3
    }
  }
}
```

### States
- **Closed**: Normal operation
- **Open**: Failing, reject calls
- **Half-Open**: Test recovery

---

# Subsystem: Data Interoperability

## Overview

Import/export formats and compatibility with other systems.

## Export Formats

| Format | Use Case | Description |
|--------|----------|-------------|
| JSON | General | Structured data exchange |
| JSONL | Trajectories | Line-delimited JSON |
| Markdown | Memory | Human-readable export |
| SQL Dump | Database | Full database export |

## Import Compatibility

### Memory Systems
| System | Import Support |
|--------|----------------|
| OpenClaw default | Full (MEMORY.md, sessions) |
| Mem0 | Partial (JSON format) |
| Zep | Partial (JSON format) |
| Chroma | Full (embeddings + metadata) |

### Skill Formats
| Format | Import |
|--------|--------|
| OpenClaw SKILL.md | Full |
| AgentSkills | Full |
| Custom JSON | Partial |

## Data Transformation

### Transform Pipeline
```python
# Import from Mem0
data = await gnosys.import_(
    source="mem0",
    format="json",
    data=mem0_export
)

# Transform to Gnosys format
gnosys_data = gnosys.transform(data, from="mem0", to="gnosys")
```

### Custom Transformers
```json
{
  "interop": {
    "transformers": {
      "custom_format": {
        "path": "~/transformers/custom.py",
        "class": "CustomTransformer"
      }
    }
  }
}
```

---

# File Structure

```
docs/
├── SPEC.md                      # This file
├── architecture/
│   ├── overview.md              # System overview
│   ├── components.md            # Component details
│   └── data-flow.md             # Data flow diagrams
├── pipeline/
│   ├── agents.md                # Agent definitions
│   ├── router.md                # Routing logic
│   └── configuration.md         # Pipeline config
├── memory/
│   ├── tiers.md                 # Memory tier details
│   ├── storage.md               # Storage implementation
│   ├── retrieval.md             # Retrieval algorithms
│   └── configuration.md         # Memory config
├── skills/
│   ├── detection.md             # Skill detection logic
│   ├── extraction.md            # Skill extraction
│   ├── storage.md               # Skill storage
│   └── refinement.md            # Skill refinement
├── learning/
│   ├── mechanisms.md            # Learning mechanisms
│   ├── patterns.md              # Pattern detection
│   ├── adaptation.md            # Adaptation logic
│   └── trajectory.md            # Trajectory logging
├── scheduler/
│   ├── cron.md                   # Cron scheduling
│   ├── tasks.md                  # Task definitions
│   └── delivery.md               # Result delivery
├── models/
│   ├── providers.md             # LLM providers
│   ├── switching.md             # Dynamic model switching
│   └── embeddings.md            # Embeddings providers
├── context/
│   ├── engine.md                # Context engine
│   ├── retrieval.md             # Context retrieval
│   └── injection.md             # Prompt injection
├── security/
│   ├── encryption.md            # Data encryption
│   ├── secrets.md               # API key management
│   └── sandboxing.md            # Agent sandboxing
├── monitoring/
│   ├── metrics.md               # Metrics collection
│   ├── health.md                # Health checks
│   └── dashboard.md             # Dashboard
├── backup/
│   ├── backup.md                # Backup procedures
│   ├── restore.md               # Recovery procedures
│   └── migration.md             # Migration tools
├── api/
│   ├── endpoints.md             # API endpoints
│   ├── authentication.md         # API auth
│   └── sdk.md                   # SDK documentation
├── testing/
│   ├── unit.md                  # Unit tests
│   ├── integration.md           # Integration tests
│   └── benchmarks.md            # Performance benchmarks
├── performance/
│   ├── caching.md               # Caching strategies
│   ├── batch.md                 # Batch processing
│   └── optimization.md          # Memory optimization
├── tools/
│   ├── registry.md              # Tool registry
│   ├── versioning.md            # Tool versioning
│   └── discovery.md             # Tool discovery
├── errors/
│   ├── codes.md                 # Error codes
│   ├── retry.md                # Retry policies
│   └── circuit-breaker.md       # Circuit breaker
├── interop/
│   ├── import-export.md         # Import/export formats
│   ├── transformers.md          # Data transformers
│   └── compatibility.md         # System compatibility
└── integration/
    ├── openclaw.md              # OpenClaw integration
    ├── hooks.md                 # Hook implementation
    └── migration.md             # Migration guide
```

---

# API Reference

## Core Classes

### GnosysCore
Main entry point for the Gnosys plugin.

```python
class GnosysCore:
    def __init__(self, config: GnosysConfig):
        self.memory = MemorySystem(config.memory)
        self.pipeline = PipelineController(config.pipeline)
        self.skills = SkillSystem(config.skills)
        self.learning = LearningSystem(config.learning)
        self.scheduler = Scheduler(config.scheduler)
        self.context = ContextEngine(config.context)
    
    async def initialize(self) -> None:
        """Initialize all subsystems"""
    
    async def shutdown(self) -> None:
        """Clean shutdown of all subsystems"""
    
    async def process_message(self, message: Message) -> Response:
        """Process incoming message through pipeline"""
```

### MemorySystem
```python
class MemorySystem:
    def __init__(self, config: MemoryConfig):
        self.tiers = {
            "working": WorkingMemory(config.working),
            "episodic": EpisodicMemory(config.episodic),
            "semantic": SemanticMemory(config.semantic),
            "archive": ArchiveMemory(config.archive)
        }
    
    async def store(self, item: MemoryItem) -> str:
        """Store memory item, auto-tier based on type"""
    
    async def search(self, query: str, options: SearchOptions) -> List[MemoryItem]:
        """Search across all tiers"""
    
    async def retrieve(self, memory_id: str) -> MemoryItem:
        """Retrieve specific memory item"""
    
    async def consolidate(self) -> None:
        """Run consolidation across tiers"""
    
    async def get_stats(self) -> MemoryStats:
        """Get memory statistics"""
```

### PipelineController
```python
class PipelineController:
    async def process(self, task: Task) -> TaskResult:
        """Process task through pipeline"""
    
    async def spawn_agent(self, agent_config: AgentConfig) -> Agent:
        """Spawn sub-agent with isolated context"""
    
    async def coordinate(self, agents: List[Agent], pattern: CoordinationPattern) -> TaskResult:
        """Coordinate multiple agents"""
```

### SkillSystem
```python
class SkillSystem:
    async def detect_pattern(self, trajectory: Trajectory) -> Optional[SkillPattern]:
        """Detect skill-worthy patterns"""
    
    async def extract_skill(self, pattern: SkillPattern) -> Skill:
        """Extract skill from pattern"""
    
    async def store_skill(self, skill: Skill) -> None:
        """Store skill in registry"""
    
    async def refine_skill(self, skill_id: str, feedback: SkillFeedback) -> None:
        """Refine existing skill"""
    
    async def match_skill(self, task: Task) -> Optional[Skill]:
        """Find best matching skill for task"""
```

### LearningSystem
```python
class LearningSystem:
    async def observe(self, event: LearningEvent) -> None:
        """Observe and log learning event"""
    
    async def analyze(self) -> AnalysisResult:
        """Analyze collected observations"""
    
    async def adapt(self, analysis: AnalysisResult) -> Adaptation:
        """Apply adaptations based on analysis"""
    
    async def generate_dataset(self, dataset_type: DatasetType) -> Dataset:
        """Generate training dataset"""
```

### ContextEngine
```python
class ContextEngine:
    async def build_context(self, query: str, max_tokens: int) -> str:
        """Build context string from memory"""
    
    async def retrieve(self, query: str, options: RetrievalOptions) -> List[MemoryItem]:
        """Retrieve relevant memories"""
    
    async def inject_context(self, prompt: str, context: str) -> str:
        """Inject context into prompt"""
```

## Database Schema

### Core Tables

```sql
-- Memory items across all tiers
CREATE TABLE memory_items (
    id TEXT PRIMARY KEY,
    tier TEXT NOT NULL,              -- working, episodic, semantic, archive
    type TEXT NOT NULL,              -- conversational, entity, procedural, factual, emotional, meta
    content TEXT NOT NULL,
    embedding_id TEXT,
    metadata JSON,
    importance REAL DEFAULT 0.5,
    created_at INTEGER NOT NULL,
    accessed_at INTEGER,
    staleness REAL DEFAULT 0.0,
    consolidated BOOLEAN DEFAULT FALSE,
    session_id TEXT,
    user_id TEXT
);

-- Vector embeddings (Chroma integration)
CREATE TABLE embeddings (
    id TEXT PRIMARY KEY,
    memory_id TEXT NOT NULL,
    vector BLOB NOT NULL,
    model TEXT NOT NULL,
    dimension INTEGER NOT NULL,
    created_at INTEGER NOT NULL,
    FOREIGN KEY (memory_id) REFERENCES memory_items(id)
);

-- Semantic relationships between memories
CREATE TABLE memory_relations (
    id TEXT PRIMARY KEY,
    source_id TEXT NOT NULL,
    target_id TEXT NOT NULL,
    relation_type TEXT NOT NULL,    -- is-a, part-of, related-to, caused-by
    strength REAL DEFAULT 1.0,
    created_at INTEGER NOT NULL,
    FOREIGN KEY (source_id) REFERENCES memory_items(id),
    FOREIGN KEY (target_id) REFERENCES memory_items(id)
);

-- Session tracking
CREATE TABLE sessions (
    id TEXT PRIMARY KEY,
    agent_id TEXT NOT NULL,
    started_at INTEGER NOT NULL,
    ended_at INTEGER,
    memory_snapshot_id TEXT,
    context JSON
);

-- Skills registry
CREATE TABLE skills (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    version TEXT NOT NULL,
    description TEXT,
    workflow JSON NOT NULL,
    tools JSON NOT NULL,
    parameters JSON,
    examples JSON,
    trigger_count INTEGER DEFAULT 0,
    success_rate REAL DEFAULT 1.0,
    compounds_from JSON,
    created_at INTEGER NOT NULL,
    last_used_at INTEGER,
    refined_at INTEGER
);

-- Skill usage tracking
CREATE TABLE skill_usage (
    id TEXT PRIMARY KEY,
    skill_id TEXT NOT NULL,
    task_id TEXT NOT NULL,
    success BOOLEAN NOT NULL,
    feedback REAL,
    used_at INTEGER NOT NULL,
    FOREIGN KEY (skill_id) REFERENCES skills(id)
);

-- Trajectory logging for learning
CREATE TABLE trajectories (
    id TEXT PRIMARY KEY,
    task TEXT NOT NULL,
    started_at INTEGER NOT NULL,
    completed_at INTEGER,
    success BOOLEAN,
    agents JSON NOT NULL,
    steps JSON NOT NULL,
    metrics JSON,
    FOREIGN KEY (task) REFERENCES tasks(id)
);

-- Agent execution history
CREATE TABLE agent_history (
    id TEXT PRIMARY KEY,
    agent_id TEXT NOT NULL,
    role TEXT NOT NULL,
    task_id TEXT NOT NULL,
    started_at INTEGER NOT NULL,
    completed_at INTEGER,
    result TEXT,
    error TEXT,
    metrics JSON
);

-- Scheduled tasks
CREATE TABLE scheduled_tasks (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    schedule TEXT NOT NULL,          -- cron expression
    task_type TEXT NOT NULL,
    action JSON NOT NULL,
    delivery JSON,
    enabled BOOLEAN DEFAULT TRUE,
    last_run_at INTEGER,
    next_run_at INTEGER,
    created_at INTEGER NOT NULL
);

-- Task execution history
CREATE TABLE task_history (
    id TEXT PRIMARY KEY,
    task_id TEXT NOT NULL,
    scheduled_task_id TEXT,
    started_at INTEGER NOT NULL,
    completed_at INTEGER,
    result TEXT,
    error TEXT,
    delivered BOOLEAN DEFAULT FALSE,
    delivery_result TEXT
);

-- System metrics
CREATE TABLE metrics (
    id TEXT PRIMARY KEY,
    metric_type TEXT NOT NULL,
    value REAL NOT NULL,
    tags JSON,
    recorded_at INTEGER NOT NULL
);

-- Configuration versioning
CREATE TABLE config_versions (
    version TEXT PRIMARY KEY,
    config JSON NOT NULL,
    applied_at INTEGER NOT NULL,
    description TEXT
);

-- Backup records
CREATE TABLE backups (
    id TEXT PRIMARY KEY,
    backup_type TEXT NOT NULL,       -- full, incremental, selective
    components JSON NOT NULL,
    file_path TEXT NOT NULL,
    checksum TEXT NOT NULL,
    size_bytes INTEGER,
    created_at INTEGER NOT NULL
);
```

### Indexes

```sql
-- Memory search optimization
CREATE INDEX idx_memory_tier ON memory_items(tier);
CREATE INDEX idx_memory_type ON memory_items(type);
CREATE INDEX idx_memory_created ON memory_items(created_at);
CREATE INDEX idx_memory_session ON memory_items(session_id);
CREATE INDEX idx_memory_user ON memory_items(user_id);

-- Semantic search
CREATE INDEX idx_memory_embedding ON embeddings(memory_id);
CREATE INDEX idx_relations_source ON memory_relations(source_id);
CREATE INDEX idx_relations_target ON memory_relations(target_id);

-- Skills
CREATE INDEX idx_skill_name ON skills(name);
CREATE INDEX idx_skill_usage_skill ON skill_usage(skill_id);
CREATE INDEX idx_skill_usage_task ON skill_usage(task_id);

-- Scheduler
CREATE INDEX idx_scheduled_next ON scheduled_tasks(next_run_at);
CREATE INDEX idx_task_history_task ON task_history(task_id);
```

## Error Codes

| Code | Category | Message | Recovery |
|------|----------|---------|----------|
| 1000 | Memory | Tier not found | Use valid tier |
| 1001 | Memory | Memory item not found | Check ID |
| 1002 | Memory | Storage full | Clear old data |
| 1003 | Memory | Embedding failed | Retry with fallback |
| 1100 | Pipeline | Agent spawn failed | Check resources |
| 1101 | Pipeline | Agent timeout | Increase timeout |
| 1102 | Pipeline | Coordination failed | Retry |
| 1103 | Pipeline | Agent not found | Check agent ID |
| 1200 | Skills | Skill not found | Check skill ID |
| 1201 | Skills | Extraction failed | Retry |
| 1202 | Skills | Skill version conflict | Use correct version |
| 1300 | Learning | Analysis failed | Check data |
| 1301 | Learning | Dataset generation failed | Check trajectories |
| 1400 | Scheduler | Task not found | Check task ID |
| 1401 | Scheduler | Schedule invalid | Check cron syntax |
| 1402 | Scheduler | Delivery failed | Check delivery config |
| 1500 | External | API rate limited | Wait and retry |
| 1501 | External | Provider unavailable | Use fallback |
| 1502 | External | Model not found | Use available model |

# Implementation Phases

## Phase 1: Foundation (v0.1.0)
- [ ] Plugin structure and manifest
- [ ] Basic memory tier (working + episodic)
- [ ] Simple context engine
- [ ] Basic configuration
- [ ] OpenClaw hook integration

## Phase 2: Core Features (v0.2.0)
- [ ] Full memory tiers
- [ ] Semantic search
- [ ] Multi-agent pipeline basic
- [ ] Self-learning observation

## Phase 3: Advanced Features (v0.3.0)
- [ ] Self-learning analysis
- [ ] Context optimization
- [ ] Agent specialization

## Phase 4: Production (v1.0.0)
- [ ] Full self-learning loop
- [ ] Complete pipeline orchestration
- [ ] Performance optimization
- [ ] Documentation complete

---

# Status

**v0.1 Spec Complete** - Ready for implementation

## Next Steps

1. Create implementation plan for v0.1.0
2. Define detailed API specifications
3. Design database schemas
4. Plan testing strategy
