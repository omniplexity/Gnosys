# Scheduler Component

## Overview

The Scheduler system provides cron-like task scheduling with autonomous execution capabilities.

## File

`python/src/gnosys_backend/scheduler.py`

## Class: Scheduler

```python
class Scheduler:
    def __init__(self, db: Database, config: SchedulerConfig,
                 execute_callback: Callable | None = None) -> None: ...
    
    async def create_task(request: ScheduledTaskCreateRequest) -> ScheduledTaskRecord: ...
    
    async def list_tasks(enabled_only: bool = False) -> ScheduledTaskListResponse: ...
    
    async def get_task(task_id: str) -> ScheduledTaskRecord | None: ...
    
    async def update_task(task_id: str, enabled: bool | None = None) -> ...: ...
    
    async def delete_task(task_id: str) -> bool: ...
    
    async def run_task(task_id: str) -> ScheduledTaskRunResponse: ...
    
    async def get_task_history(task_id: str, limit: int = 50) -> ...: ...
    
    async def get_due_tasks() -> list[ScheduledTaskRecord]: ...
    
    async def process_due_tasks() -> dict[str, Any]: ...
    
    async def get_scheduler_stats() -> dict[str, Any]: ...
```

## Scheduling Options

### Cron Syntax

Standard cron format:
```
┌───────────── minute (0 - 59)
│ ┌─────────── hour (0 - 23)
│ │ ┌───────── day of month (1 - 31)
│ │ │ ┌─────── month (1 - 12)
│ │ │ │ ┌───── day of week (0 - 6)
* * * * *
```

### Interval Syntax

```
@every 30m    # Every 30 minutes
@every 1h     # Every hour
@every 2h     # Every 2 hours
```

### Common Patterns

| Pattern | Example | Description |
|---------|---------|-------------|
| Hourly | `0 * * * *` | Every hour at minute 0 |
| Daily | `0 9 * * *` | Every day at 9 AM |
| Weekly | `0 9 * * 1` | Every Monday at 9 AM |
| Interval | `@every 30m` | Every 30 minutes |

## Task Types

| Type | Description | Delivery |
|------|-------------|----------|
| `query` | Run search/query, return results | Message, webhook |
| `action` | Execute tool/agent operation | Status, webhook |
| `report` | Compile and send report | Email, message |
| `check` | Health check, monitoring | Alert, log |

## Delivery Options

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
  "name": "morning_briefing",
  "schedule": "0 8 * * *",
  "task_type": "report",
  "enabled": true,
  "description": "Daily morning summary",
  "action": {
    "query_memory": true,
    "include_context": ["episodic", "semantic"],
    "compile": "summary"
  },
  "delivery": {
    "announce": true,
    "webhook": null
  }
}
```

## Features

### Due Task Processing

Automatically process tasks when they're due:

```python
# Get due tasks
due_tasks = await scheduler.get_due_tasks()

# Process all due tasks
results = await scheduler.process_due_tasks()
# Returns: { "processed": 3, "succeeded": 2, "failed": 1, "errors": [] }
```

### Execution History

Track all task executions:

```python
history = await scheduler.get_task_history(task_id, limit=50)
# Returns execution records with success, result, error, duration_ms
```

### Statistics

```python
stats = await scheduler.get_scheduler_stats()
# Returns: { "total_tasks": 10, "active_tasks": 8, "due_now": 2, "executions_24h": 50 }
```

## Configuration

```json
{
  "scheduler": {
    "enabled": true,
    "max_concurrent": 5,
    "timeout_seconds": 300,
    "retry_enabled": true,
    "retry_max_attempts": 3,
    "retry_backoff": "exponential"
  }
}
```

## Usage

```python
from gnosys_backend.scheduler import Scheduler

scheduler = Scheduler(db, config)

# Create scheduled task
task = await scheduler.create_task(ScheduledTaskCreateRequest(
    name="daily_backup",
    schedule="0 2 * * *",
    task_type="action",
    action={"backup_database": True},
    delivery={"announce": True}
))

# List tasks
tasks = await scheduler.list_tasks(enabled_only=True)

# Run immediately
result = await scheduler.run_task(task.id)

# Get history
history = await scheduler.get_task_history(task.id)
```

## Database Schema

```sql
CREATE TABLE scheduled_tasks (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL UNIQUE,
    schedule TEXT NOT NULL,
    task_type TEXT NOT NULL,
    enabled INTEGER NOT NULL DEFAULT 1,
    description TEXT,
    action_json TEXT NOT NULL,
    delivery_json TEXT NOT NULL,
    created_at TEXT NOT NULL,
    last_run_at TEXT,
    next_run_at TEXT,
    run_count INTEGER NOT NULL DEFAULT 0
);

CREATE TABLE scheduled_task_executions (
    id TEXT PRIMARY KEY,
    task_id TEXT NOT NULL,
    executed_at TEXT NOT NULL,
    success INTEGER NOT NULL,
    result_json TEXT,
    error TEXT,
    duration_ms INTEGER NOT NULL DEFAULT 0,
    FOREIGN KEY (task_id) REFERENCES scheduled_tasks(id)
);
```
