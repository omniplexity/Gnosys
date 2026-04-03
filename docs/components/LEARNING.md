# Learning Component

## Overview

The Learning system provides self-learning capabilities through trajectory analysis, pattern detection, and dataset generation.

## Files

- `python/src/gnosys_backend/learning.py` - Pattern detection
- `python/src/gnosys_backend/trajectory_store.py` - Trajectory logging

## Classes

### LearningStore

```python
class LearningStore:
    def __init__(self, db: Database, config: LearningConfig) -> None: ...
    
    def detect_patterns(self, request: PatternDetectRequest) -> PatternDetectResponse: ...
    
    def generate_dataset(self, request: DatasetGenerateRequest) -> DatasetGenerateResponse: ...
```

### TrajectoryStore

```python
class TrajectoryStore:
    def __init__(self, db: Database, config: AppConfig) -> None: ...
    
    def create(self, request: TrajectoryCreateRequest) -> TrajectoryRecord: ...
    
    def update(self, trajectory_id: str, 
               request: TrajectoryUpdateRequest) -> TrajectoryRecord | None: ...
    
    def get(self, trajectory_id: str) -> TrajectoryRecord | None: ...
    
    def list_recent(self, limit: int = 50, 
                    agent_type: str | None = None) -> TrajectoryListResponse: ...
    
    def get_stats(self) -> LearningStatsResponse: ...
```

## Features

### Trajectory Logging

Full execution traces for learning:

```python
trajectory = {
    "id": "uuid",
    "task": "Fix bug in authentication",
    "started_at": "ISO datetime",
    "completed_at": "ISO datetime",
    "success": true,
    "agent_type": "coder",
    "steps": [
        {
            "step": 1,
            "tool": "read",
            "params": {"filePath": "auth.py"},
            "result": "...",
            "success": true,
            "duration_ms": 150
        }
    ],
    "metrics": {
        "total_steps": 5,
        "total_duration_ms": 1200,
        "tool_calls": 5,
        "errors": 0
    }
}
```

### Pattern Detection

Analyzes trajectories to find repeated tool sequences:

| Pattern | Description |
|---------|-------------|
| `tool_sequence` | Repeated tool call patterns |
| `success_indicator` | Steps that indicate success |
| `error_recovery` | Error handling patterns |

### Dataset Generation

Creates training datasets from successful trajectories:

| Dataset Type | Description |
|--------------|-------------|
| `task_response` | Task → Response pairs |
| `tool_workflow` | Task → Tool sequence |
| `context_relevance` | Context → Relevance scores |
| `agent_decision` | Decision point → Choice |

## Usage

```python
from gnosys_backend.learning import LearningStore
from gnosys_backend.trajectory_store import TrajectoryStore

learning = LearningStore(db, config)
trajectory_store = TrajectoryStore(db, config)

# Create trajectory
traj = trajectory_store.create(TrajectoryCreateRequest(
    task="Fix authentication bug",
    agent_type="coder"
))

# Update with results
trajectory_store.update(traj.id, TrajectoryUpdateRequest(
    success=True,
    steps=[...],
    metrics={"total_steps": 5, "total_duration_ms": 1200}
))

# Detect patterns
patterns = learning.detect_patterns(PatternDetectRequest(
    trajectory_limit=100
))

# Generate dataset
dataset = learning.generate_dataset(DatasetGenerateRequest(
    dataset_type="tool_workflow",
    min_success_rate=0.8
))
```

## Database Schema

```sql
CREATE TABLE trajectories (
    id TEXT PRIMARY KEY,
    task TEXT NOT NULL,
    started_at TEXT NOT NULL,
    completed_at TEXT,
    success INTEGER,
    agent_type TEXT NOT NULL,
    query TEXT,
    response_preview TEXT,
    steps_json TEXT NOT NULL,
    metrics_json TEXT NOT NULL,
    error TEXT
);

CREATE TABLE learning_patterns (
    id TEXT PRIMARY KEY,
    pattern_type TEXT NOT NULL,
    description TEXT NOT NULL,
    frequency INTEGER NOT NULL,
    success_rate REAL NOT NULL,
    tools_json TEXT NOT NULL,
    metadata_json TEXT NOT NULL,
    detected_at TEXT NOT NULL
);
```
