# Pipeline Component

## Overview

The Pipeline system provides multi-agent orchestration with various coordination modes.

## File

`python/src/gnosys_backend/pipeline.py`

## Class: PipelineStore

```python
class PipelineStore:
    def __init__(self, db: Database, config: PipelineConfig) -> None: ...
    
    def spawn_agent(self, request: AgentSpawnRequest) -> AgentSpawnResponse: ...
    
    def delegate_task(self, request: TaskDelegateRequest) -> TaskDelegateResponse: ...
    
    def get_agent(self, agent_id: str) -> AgentSpawnResponse | None: ...
    
    def list_active_agents(self, parent_id: str | None = None) -> list[AgentSpawnResponse]: ...
    
    def execute_pipeline(self, request: PipelineExecuteRequest) -> PipelineExecuteResponse: ...
```

## Coordination Modes

| Mode | Description | Flow |
|------|-------------|------|
| `sequential` | Agent A → Agent B → Agent C | Sequential execution |
| `parallel` | All agents execute simultaneously | Parallel execution |
| `hierarchical` | Coordinator manages workers | Tree structure |
| `debate` | Multiple agents propose, vote on best | Consensus |

## Agent Roles

| Role | Description |
|------|-------------|
| `primary` | Main agent handling user request |
| `coordinator` | Manages sub-agents |
| `specialist` | Domain-specific agent |
| `worker` | Task execution agent |

## Agent Types

| Type | Description |
|------|-------------|
| `primary` | Main task handler |
| `worker` | Task worker |
| `researcher` | Information gathering |
| `coder` | Code generation |
| `reviewer` | Code/task review |

## Features

### Agent Spawning

- Create isolated agent contexts
- Assign roles and types
- Track parent-child relationships
- Manage agent lifecycle

### Task Delegation

- Delegate tasks to sub-agents
- Pass context and tools
- Track delegation chain

### Pipeline Profiles

Store and execute named pipeline configurations:

```python
profile = {
    "name": "code_review",
    "agents": [
        {"role": "coordinator", "type": "primary"},
        {"role": "worker", "type": "researcher", "weight": 1.0},
        {"role": "worker", "type": "reviewer", "weight": 1.0}
    ],
    "coordination": "parallel"
}
```

## Usage

```python
from gnosys_backend.pipeline import PipelineStore

pipeline = PipelineStore(db, config)

# Spawn agent
agent = pipeline.spawn_agent(AgentSpawnRequest(
    role="worker",
    agent_type="researcher",
    context={"task": "find information"}
))

# Execute pipeline
result = pipeline.execute_pipeline(PipelineExecuteRequest(
    profile_name="code_review",
    task="Review PR #123"
))
```

## Database Schema

```sql
CREATE TABLE pipeline_profiles (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL UNIQUE,
    agents_json TEXT NOT NULL,
    coordination TEXT NOT NULL,
    created_at TEXT NOT NULL
);

CREATE TABLE agents (
    id TEXT PRIMARY KEY,
    role TEXT NOT NULL,
    agent_type TEXT NOT NULL,
    context_json TEXT NOT NULL,
    tools_json TEXT NOT NULL,
    status TEXT NOT NULL,
    result TEXT,
    parent_id TEXT,
    created_at TEXT NOT NULL
);
```
