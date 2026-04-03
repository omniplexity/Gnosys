# Gnosys API Endpoints

Base URL: `http://127.0.0.1:8766`

## Memory Endpoints

### POST /memories
Store a new memory.

**Request Body:**
```json
{
  "content": "string (required)",
  "memory_type": "string (default: conversational)",
  "tier": "working | episodic | semantic | archive",
  "tags": ["string"],
  "metadata": {},
  "expires_at": "ISO datetime (optional)"
}
```

**Response:**
```json
{
  "memory": {
    "id": "uuid",
    "content": "string",
    "memory_type": "string",
    "tier": "string",
    "tags": [],
    "metadata": {},
    "created_at": "ISO datetime",
    "updated_at": "ISO datetime"
  }
}
```

### GET /memories/{id}
Fetch a memory by ID.

**Response:**
```json
{
  "memory": { ... }
}
```

### DELETE /memories/{id}
Delete a memory.

**Response:**
```json
{
  "deleted": "uuid",
  "success": true
}
```

### GET /memories/search
Keyword search memories.

**Query Parameters:**
- `q` (required): Search query
- `limit`: Results limit (1-100)
- `memory_type`: Filter by memory type
- `tier`: Filter by tier

**Response:**
```json
{
  "query": "string",
  "count": 0,
  "results": [
    {
      "memory": { ... },
      "score": 0,
      "matched_keywords": []
    }
  ]
}
```

### POST /memories/semantic-search
Hybrid semantic + keyword search.

**Request Body:**
```json
{
  "query": "string (required)",
  "limit": 10,
  "memory_type": "string (optional)",
  "tier": "string (optional)",
  "semantic_weight": 0.7,
  "include_entities": false
}
```

**Response:**
```json
{
  "query": "string",
  "count": 0,
  "results": [
    {
      "memory": { ... },
      "score": 0.0,
      "semantic_score": 0.0,
      "keyword_score": 0.0,
      "matched_keywords": []
    }
  ],
  "used_semantic_search": true,
  "truncated": false
}
```

### GET /stats
Get memory statistics.

**Response:**
```json
{
  "total_memories": 0,
  "counts_by_type": {},
  "counts_by_tier": {},
  "database_path": "string"
}
```

---

## Context Endpoints

### POST /context/retrieve
Retrieve context with token budget management.

**Request Body:**
```json
{
  "query": "string (required)",
  "max_tokens": 4000,
  "include_tiers": ["working", "episodic", "semantic", "archive"]
}
```

**Response:**
```json
{
  "query": "string",
  "items": [
    {
      "rank": 1,
      "memory": { ... },
      "score": 0.0,
      "matched_keywords": [],
      "estimated_tokens": 0
    }
  ],
  "tiers_included": [],
  "token_budget": 0,
  "used_tokens": 0,
  "remaining_tokens": 0,
  "truncated": false,
  "dropped_count": 0,
  "assembly_text": "string"
}
```

---

## Entity Endpoints

### GET /entities/memory/{memory_id}
Get all entities extracted from a memory.

**Response:**
```json
{
  "memory_id": "uuid",
  "entities": []
}
```

### GET /entities/search
Search entities by value.

**Query Parameters:**
- `q` (required): Search query
- `entity_type`: Filter by entity type
- `limit`: Results limit (1-100)

**Response:**
```json
{
  "query": "string",
  "entity_type": "string",
  "count": 0,
  "results": []
}
```

### GET /entities/stats
Get entity extraction statistics.

**Response:**
```json
{
  "total_entities": 0,
  "by_type": {},
  "by_value": {}
}
```

---

## Agent & Pipeline Endpoints

### POST /agents/spawn
Spawn a sub-agent.

**Request Body:**
```json
{
  "role": "string (required)",
  "agent_type": "string (optional)",
  "context": {},
  "tools": [],
  "parent_id": "string (optional)"
}
```

**Response:**
```json
{
  "agent_id": "uuid",
  "role": "string",
  "agent_type": "string",
  "status": "pending",
  "created_at": "ISO datetime"
}
```

### POST /agents/delegate
Delegate a task to a sub-agent.

**Request Body:**
```json
{
  "role": "string (required)",
  "agent_type": "string (optional)",
  "context": {},
  "tools": [],
  "parent_id": "string (optional)"
}
```

**Response:**
```json
{
  "agent_id": "uuid",
  "status": "pending",
  "delegated_at": "ISO datetime"
}
```

### GET /agents/{agent_id}
Get agent by ID.

**Response:**
```json
{
  "agent_id": "uuid",
  "role": "string",
  "agent_type": "string",
  "status": "string",
  "created_at": "ISO datetime"
}
```

### GET /agents
List active agents.

**Query Parameters:**
- `parent_id`: Filter by parent agent

**Response:**
```json
[
  { ... }
]
```

### POST /pipeline/execute
Execute a multi-agent pipeline.

**Request Body:**
```json
{
  "profile_name": "string (required)",
  "task": "string (required)",
  "coordinator_id": "string (optional)"
}
```

**Response:**
```json
{
  "pipeline_id": "uuid",
  "profile_name": "string",
  "agents_spawned": 0,
  "results": [],
  "executed_at": "ISO datetime"
}
```

---

## Learning Endpoints

### POST /learning/detect-patterns
Detect patterns from recent trajectories.

**Request Body:**
```json
{
  "trajectory_limit": 100
}
```

**Response:**
```json
{
  "patterns": [
    {
      "id": "uuid",
      "pattern_type": "string",
      "description": "string",
      "frequency": 0,
      "success_rate": 0.0,
      "tools": [],
      "metadata": {}
    }
  ],
  "total_analyzed": 0,
  "generated_at": "ISO datetime"
}
```

### POST /learning/generate-dataset
Generate training dataset.

**Request Body:**
```json
{
  "dataset_type": "task_response | tool_workflow | context_relevance | agent_decision",
  "min_success_rate": 0.8
}
```

**Response:**
```json
{
  "dataset_type": "string",
  "records": [],
  "total_records": 0,
  "generated_at": "ISO datetime"
}
```

### GET /learning/metrics
Get learning metrics.

**Response:**
```json
{
  "total_trajectories": 0,
  "success_rate": 0.0,
  "avg_duration_ms": 0.0,
  "tool_usage": {},
  "agent_stats": {}
}
```

---

## Trajectory Endpoints

### POST /trajectories
Create a new trajectory.

**Request Body:**
```json
{
  "task": "string (required)",
  "agent_type": "string (default: primary)",
  "query": "string (optional)",
  "response_preview": "string (optional)"
}
```

**Response:**
```json
{
  "trajectory": {
    "id": "uuid",
    "task": "string",
    "started_at": "ISO datetime",
    ...
  }
}
```

### PUT /trajectories/{id}
Update a trajectory.

**Request Body:**
```json
{
  "completed_at": "ISO datetime",
  "success": true,
  "steps": [],
  "metrics": {},
  "error": "string (optional)"
}
```

### GET /trajectories/{id}
Get trajectory by ID.

### GET /trajectories
List recent trajectories.

**Query Parameters:**
- `limit`: Results limit (1-100)
- `agent_type`: Filter by agent type

---

## Skills Endpoints

### GET /skills
List all skills.

**Response:**
```json
{
  "count": 0,
  "skills": [
    {
      "id": "uuid",
      "name": "string",
      "version": "1.0.0",
      "triggers": [],
      "workflow": [],
      "tools": [],
      "use_count": 0,
      "success_rate": 0.0,
      "created_at": "ISO datetime"
    }
  ]
}
```

### POST /skills
Create a new skill.

**Request Body:**
```json
{
  "name": "string (required)",
  "triggers": [],
  "workflow": ["step1", "step2"],
  "tools": [],
  "parameters": {},
  "description": "string (optional)",
  "compounds_from": []
}
```

### GET /skills/{id}
Get a skill by ID.

### POST /skills/match
Match a task to the best skill.

**Request Body:**
```json
{
  "task": "string (required)",
  "context": {} (optional)
}
```

**Response:**
```json
{
  "matched": true,
  "skill": { ... },
  "confidence": 0.85
}
```

### POST /skills/{id}/refine
Refine a skill based on feedback.

**Request Body:**
```json
{
  "feedback": "string (required)",
  "success": true,
  "improvements": []
}
```

**Response:**
```json
{
  "skill": { ... },
  "previous_version": "1.0.0",
  "new_version": "1.1.0"
}
```

### DELETE /skills/{id}
Delete a skill.

### GET /skills/stats
Get skills statistics.

**Response:**
```json
{
  "total_skills": 0,
  "total_uses": 0,
  "avg_success_rate": 0.0,
  "top_skills": []
}
```

---

## Scheduler Endpoints

### GET /scheduled
List all scheduled tasks.

**Query Parameters:**
- `enabled_only`: Filter by enabled status

**Response:**
```json
{
  "count": 0,
  "tasks": [
    {
      "id": "uuid",
      "name": "string",
      "schedule": "0 * * * *",
      "task_type": "query",
      "enabled": true,
      "description": "string",
      "next_run_at": "ISO datetime",
      "run_count": 0
    }
  ]
}
```

### POST /scheduled
Create a new scheduled task.

**Request Body:**
```json
{
  "name": "string (required)",
  "schedule": "cron expression (required)",
  "task_type": "query | action | report | check",
  "enabled": true,
  "description": "string (optional)",
  "action": {},
  "delivery": {}
}
```

### GET /scheduled/{id}
Get a scheduled task.

### POST /scheduled/{id}/run
Run a task immediately.

**Response:**
```json
{
  "task_id": "uuid",
  "executed": true,
  "result": {},
  "executed_at": "ISO datetime"
}
```

### DELETE /scheduled/{id}
Delete a scheduled task.

### GET /scheduled/{id}/history
Get task execution history.

**Query Parameters:**
- `limit`: Results limit (default: 50)

**Response:**
```json
{
  "count": 0,
  "executions": [
    {
      "id": "uuid",
      "executed_at": "ISO datetime",
      "success": true,
      "result": {},
      "error": "string",
      "duration_ms": 0
    }
  ]
}
```

### GET /scheduler/stats
Get scheduler statistics.

**Response:**
```json
{
  "total_tasks": 0,
  "active_tasks": 0,
  "due_now": 0,
  "executions_24h": 0,
  "success_rate_24h": 0.0
}
```

---

## Monitoring Endpoints

### GET /monitoring/health
Get health status.

**Response:**
```json
{
  "status": "healthy",
  "service": "gnosys",
  "version": "0.8.0",
  "components": {
    "database": "healthy"
  }
}
```

### GET /monitoring/metrics
Get system metrics.

**Response:**
```json
{
  "memory_stats": {},
  "pipeline_stats": {},
  "learning_stats": {},
  "skills_stats": {},
  "scheduler_stats": {},
  "uptime_seconds": 0.0,
  "timestamp": "ISO datetime"
}
```

---

## System Endpoints

### GET /health
Backend health check.

**Response:**
```json
{
  "status": "healthy",
  "service": "gnosys-backend",
  "version": "0.8.0",
  "database": "string"
}
```
