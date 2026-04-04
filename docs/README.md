# Gnosys v1.1.0

Gnosys is a unified intelligence framework for OpenClaw that combines:
- Multi-agent multi-layer pipeline orchestration
- Advanced multi-tier memory system with semantic search
- Self-learning loop for continuous improvement
- Autonomous skill system for workflow automation
- Cron-like task scheduler
- Full observability through monitoring
- Command-line interface for backend management

## What it currently does

### Core Features (v1.0)

- **Memory System**: 4-tier memory (Working, Episodic, Semantic, Archive) with SQLite persistence
- **Semantic Search**: Hybrid keyword + vector embeddings search with cosine similarity
- **Context Engine**: Multi-tier context retrieval with token budget management
- **Multi-Agent Pipeline**: Spawn, delegate, and coordinate multiple agents
- **Self-Learning**: Pattern detection from trajectory data, dataset generation
- **Skills System**: Auto-detect, extract, store, and refine skills from trajectories
- **Scheduler**: Cron-like task scheduling with autonomous execution
- **Monitoring**: Health checks, metrics, and observability

### Architecture

- **TypeScript wrapper**: `index.ts` and `src/` - Plugin integration with OpenClaw
- **Python backend**: `python/src/gnosys_backend/` - FastAPI server
- **HTTP bridge**: Local HTTP communication between OpenClaw and backend

### Plugin Slots

- `memory` - Primary memory backend
- `contextEngine` - Context injection and management

## Install

1. Install Node dependencies:

```bash
npm install
```

2. Install Python backend dependencies:

```bash
python -m pip install -e "./python[test]"
```

3. Install additional dependencies for v1.0 features:

```bash
pip install croniter
```

## OpenClaw Config

Set the plugin slot to `gnosys`:

```json
{
  "plugins": {
    "slots": {
      "memory": "gnosys",
      "contextEngine": "gnosys"
    },
    "entries": {
      "gnosys": {
        "enabled": true,
        "config": {
          "mode": "spawn-local-python-backend",
          "requestTimeoutMs": 10000,
          "healthcheckTimeoutMs": 3000,
          "spawn": {
            "command": "python",
            "args": ["-m", "gnosys_backend.app"],
            "cwd": "./python",
            "host": "127.0.0.1",
            "port": 8766,
            "dbPath": "./python/data/gnosys.db",
            "vectorsPath": "./python/data/vectors.db"
          },
          "retention": {
            "episodicDays": 30,
            "archiveDays": 365,
            "defaultSearchLimit": 10
          },
          "embeddings": {
            "provider": "local",
            "model": "sentence-transformers/all-MiniLM-L6-v2",
            "dimension": 384
          },
          "context": {
            "enabled": true,
            "maxTokens": 4000,
            "budgetFraction": 0.5,
            "includeTiers": ["working", "episodic", "semantic", "archive"]
          },
          "pipeline": {
            "enabled": true,
            "maxAgents": 10,
            "defaultTimeoutSeconds": 300
          },
          "learning": {
            "enabled": true
          },
          "skills": {
            "enabled": true,
            "autoDetect": true
          },
          "scheduler": {
            "enabled": true,
            "maxConcurrent": 5
          },
          "monitoring": {
            "enabled": true
          }
        }
      }
    }
  }
}
```

## Verify

```bash
# TypeScript check
npm run check

# Python tests
pytest python/tests

# Start backend
python -m uvicorn gnosys_backend.app:app --app-dir python/src --host 127.0.0.1 --port 8766

# Health check
curl http://127.0.0.1:8766/health

# Memory search
curl "http://127.0.0.1:8766/memories/search?q=test"

# Stats
curl http://127.0.0.1:8766/stats

# Skills (v0.8)
curl http://127.0.0.1:8766/skills

# Scheduled tasks (v0.8)
curl http://127.0.0.1:8766/scheduled

# Monitoring metrics (v0.8)
curl http://127.0.0.1:8766/monitoring/metrics
```

## Tools

| Tool | Description |
|------|-------------|
| `gnosys_status` | Diagnostic tool for backend connectivity |
| `gnosys_store_memory` | Store memory to backend |
| `gnosys_get_memory` | Fetch memory by ID |
| `gnosys_delete_memory` | Delete memory by ID |
| `memory_search` | Keyword search memories |
| `gnosys_semantic_search` | Hybrid semantic + keyword search |
| `gnosys_context_preview` | Context preview with token budget |
| `gnosys_pipeline` | Multi-agent pipeline client |
| `gnosys_learning` | Learning client for pattern detection |
| `gnosys_skills` | Skill management (v0.8) |
| `gnosys_scheduler` | Scheduler tool (v0.8) |

## Commands

- `/gnosys status` - Show backend status

## CLI

The Gnosys CLI provides command-line access to the backend:

```bash
# Install CLI
pip install -e "./python"

# Show status
gnosys status

# Store a memory
gnosys store --content "Remember this"

# Search memories
gnosys search project

# Get memory by ID
gnosys get <memory-id>

# Show help
gnosys help
```

See **[docs/guides/CLI.md](guides/CLI.md)** for full CLI reference.

## Documentation

See the `docs/` directory for detailed documentation:

- **[docs/INDEX.md](docs/INDEX.md)** - Documentation index
- **[docs/IMPLEMENTATION.md](docs/IMPLEMENTATION.md)** - Implementation summary
- **[docs/guides/CONFIGURATION.md](docs/guides/CONFIGURATION.md)** - Full configuration guide
- **[docs/api/ENDPOINTS.md](docs/api/ENDPOINTS.md)** - API endpoint reference

## Version

- **Gnosys**: v1.1.0
- **OpenClaw**: v0.5+ required
