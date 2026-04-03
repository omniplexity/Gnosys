# Monitoring Component

## Overview

The Monitoring system provides health checks, metrics collection, and observability for the Gnosys backend.

## File

`python/src/gnosys_backend/monitoring.py`

## Class: MonitoringSystem

```python
class MonitoringSystem:
    def __init__(self, db: Database, config: MonitoringConfig) -> None: ...
    
    @property
    def uptime_seconds(self) -> float: ...
    
    async def check_health() -> dict[str, Any]: ...
    
    async def get_metrics() -> dict[str, Any]: ...
```

## Features

### Health Checks

Checks all system components:

```python
health = await monitoring.check_health()
# Returns: {
#   "status": "healthy",
#   "service": "gnosys",
#   "version": "0.8.0",
#   "components": {
#     "database": "healthy"
#   }
# }
```

### Metrics Collection

Collects metrics from all subsystems:

| Subsystem | Metrics |
|-----------|---------|
| Memory | total_memories, by_type, by_tier |
| Pipeline | total_agents, by_status, by_role |
| Learning | total_trajectories, success_rate, tool_usage |
| Skills | total_skills, total_uses, avg_success_rate |
| Scheduler | total_tasks, active_tasks, due_now, success_rate |

### System Metrics

```python
metrics = await monitoring.get_metrics()
# Returns: {
#   "memory_stats": {...},
#   "pipeline_stats": {...},
#   "learning_stats": {...},
#   "skills_stats": {...},
#   "scheduler_stats": {...},
#   "uptime_seconds": 3600.0,
#   "timestamp": "2024-01-15T10:00:00Z"
# }
```

## Configuration

```json
{
  "monitoring": {
    "enabled": true,
    "metrics_port": 8767,
    "health_check_interval_seconds": 60
  }
}
```

## Usage

```python
from gnosys_backend.monitoring import MonitoringSystem

monitoring = MonitoringSystem(db, config)

# Check health
health = await monitoring.check_health()

# Get metrics
metrics = await monitoring.get_metrics()

# Get uptime
uptime = monitoring.uptime_seconds
```

## Performance Targets

| Metric | Target |
|--------|--------|
| Memory search | < 100ms (p95) |
| Context build | < 500ms (p95) |
| Agent spawn | < 2s (p95) |
| Scheduler tick | < 50ms |
| Health check | < 100ms |

## Integration with OpenClaw

The monitoring system integrates with OpenClaw's heartbeat:

```typescript
// In gnosys_status.ts tool
const status = await service.getStatusReport({ includeStats: true });
// Includes health and stats from monitoring
```

## Alert Conditions

| Condition | Action |
|-----------|--------|
| Database unreachable | Mark unhealthy |
| Memory usage > 90% | Alert |
| Agent failure > 3 | Alert |
| Success rate < 70% | Alert |
| Scheduler overdue | Execute recovery |
