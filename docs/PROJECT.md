# Gnosys Project

Gnosys is a unified intelligence framework for OpenClaw combining:
- Multi-agent multi-layer pipeline orchestration
- Advanced multi-tier memory system
- Self-learning loop for continuous improvement
- Autonomous skill system
- Cron-like task scheduler
- Full observability through monitoring

## Version

- **Gnosys**: v1.1.0 (current)
- **OpenClaw**: v0.5+ required

## Status

**Production Ready** - v1.1.0 implemented with:
- ✅ Multi-agent pipeline orchestration
- ✅ Self-learning trajectory logging
- ✅ Autonomous skill system
- ✅ Scheduler/cron integration
- ✅ External API (REST + SDK)
- ✅ Monitoring/dashboard
- ✅ Security subsystem
- ✅ Backup & Recovery
- ✅ Error Handling
- ✅ Data Interoperability
- ✅ Performance Caching
- ✅ Batch Processing
- ✅ Tool Registry & Versioning
- ✅ System Keychain Integration
- ✅ Incremental Backup
- ✅ CLI Foundation

## Documentation

- **[README.md](../README.md)** - Install and run guide
- **[IMPLEMENTATION.md](./IMPLEMENTATION.md)** - Implementation summary
- **[INDEX.md](./INDEX.md)** - Documentation index
- **[guides/CONFIGURATION.md](./guides/CONFIGURATION.md)** - Full configuration
- **[api/ENDPOINTS.md](./api/ENDPOINTS.md)** - API endpoint reference
- **[SPEC.md](./SPEC.md)** - Full product spec

## Subsystems

| # | Subsystem | Status | Description |
|---|-----------|--------|-------------|
| 1 | [Multi-Agent Pipeline](docs/SPEC.md#subsystem-multi-agent-pipeline) | ✅ Implemented | Orchestration, parallel agents, role-based coordination |
| 2 | [Memory System](docs/SPEC.md#subsystem-memory-system) | ✅ Implemented | 4-tier memory with semantic, procedural, meta memory |
| 3 | [Autonomous Skill System](docs/SPEC.md#subsystem-autonomous-skill-system) | ✅ Implemented v0.8 | Auto skill creation, refinement, compounding |
| 4 | [Self-Learning Loop](docs/SPEC.md#subsystem-self-learning-loop) | ✅ Implemented | Observe → Analyze → Adapt cycle, trajectory logging |
| 5 | [Scheduled Automation](docs/SPEC.md#subsystem-scheduled-automation) | ✅ Implemented v0.8 | Cron scheduler, autonomous task execution |
| 6 | [Model-Agnostic LLM](docs/SPEC.md#subsystem-model-agnostic-llm-integration) | ✅ Implemented | Multiple providers, dynamic switching, local models |
| 7 | [Context Engine](components/CONTEXT-RETRIEVAL.md) | ✅ Implemented | Memory retrieval, prompt injection, token management |
| 8 | [Security](SPEC.md#subsystem-security) | ✅ Implemented v0.9 | Encryption, secrets, agent sandboxing |
| 9 | [Monitoring](components/MONITORING.md) | ✅ Implemented v0.8 | Metrics, health checks, dashboard |
| 10 | [Backup & Recovery](docs/SPEC.md#subsystem-backup--recovery) | ✅ Implemented v0.9 | Export/import, migration, disaster recovery |
| 11 | [External API](docs/api/ENDPOINTS.md) | ✅ Implemented v0.8 | REST API, SDK |
| 12 | [Testing](docs/SPEC.md#subsystem-testing) | ✅ Basic | Unit, integration, benchmarks |
| 13 | [Performance](docs/SPEC.md#subsystem-performance-optimization) | ✅ Implemented v1.0 | Caching, batch processing |
| 14 | [Tool Registry](docs/SPEC.md#subsystem-tool-registry) | ✅ Implemented v1.0 | Dynamic tool loading, versioning |
| 15 | [Error Handling](docs/SPEC.md#subsystem-error-handling) | ✅ Implemented v0.9 | Error codes, retry, circuit breaker |
| 16 | [Data Interoperability](docs/SPEC.md#subsystem-data-interoperability) | ✅ Implemented v0.9 | Import/export, compatibility |
| 17 | [CLI](guides/CLI.md) | ✅ Implemented v1.1.0 | Command-line interface |

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                        OpenClaw Gateway                          │
├─────────────────────────────────────────────────────────────────┤
│   Memory Slot │ ContextEngine │ Tools │ Commands │ Hooks        │
└────────────────────────────┬────────────────────────────────────┘
                             │
                    HTTP Bridge (TypeScript)
                             │
                    ┌────────▼────────┐
                    │  GnosysService │
                    └────────┬────────┘
                             │ HTTP
                    ┌────────▼────────┐
                    │ Python Backend │
                    │    FastAPI     │
                    └────────┬────────┘
                             │
  ┌────────────┬────────────┬┴┬────────────┬────────────┐
  │            │            │ │            │            │
┌─▼───┐  ┌─────▼────┐  ┌───▼─▼─┐  ┌───▼──┐  ┌───▼─────┐
│Memory│  │ Context  │  │Pipeline│  │Learning│  │ Skills  │
└──┬───┘  └────┬────┘  └───┬───┘  └───┬───┘  └───┬─────┘
   │           │            │          │          │
┌──▼───┐  ┌───▼────┐  ┌───▼────┐  ┌──▼────┐  ┌──▼─────┐
│SQLite│  │Vector   │  │ Agents │  │Traject│  │ Skills │
│      │  │ Store   │  │ Table  │  │Store  │  │Storage │
└──────┘  └─────────┘  └────────┘  └───────┘  └────────┘
```

## Component Files

### TypeScript (`src/`)

| File | Purpose |
|------|---------|
| `index.ts` | Plugin entrypoint |
| `service.ts` | Service orchestration |
| `config.ts` | Configuration |
| `bridge/client.ts` | HTTP client |
| `bridge/process.ts` | Process manager |
| `tools/*.ts` | Agent tools |

### Python (`python/src/gnosys_backend/`)

| File | Purpose |
|------|---------|
| `app.py` | FastAPI app |
| `cli.py` | CLI (v1.1.0) |
| `config.py` | Configuration |
| `db.py` | Database |
| `models.py` | Pydantic models |
| `memory_store.py` | Memory storage |
| `vector_store.py` | Vector storage |
| `embeddings.py` | Embeddings |
| `entity_extraction.py` | Entity extraction |
| `context_retrieval.py` | Context retrieval |
| `pipeline.py` | Pipeline |
| `learning.py` | Learning |
| `trajectory_store.py` | Trajectories |
| `skills.py` | Skills (v0.8) |
| `scheduler.py` | Scheduler (v0.8) |
| `monitoring.py` | Monitoring (v0.8) |

## Quick Start

```bash
# Install
npm install
pip install -e "./python[test]"
pip install croniter

# Run backend
python -m uvicorn gnosys_backend.app:app --app-dir python/src --port 8766

# Health check
curl http://127.0.0.1:8766/health

# Store memory
curl -X POST http://127.0.0.1:8766/memories \
  -H "Content-Type: application/json" \
  -d '{"content": "test memory", "tier": "episodic"}'

# Search
curl "http://127.0.0.1:8766/memories/search?q=test"

# Context
curl -X POST http://127.0.0.1:8766/context/retrieve \
  -H "Content-Type: application/json" \
  -d '{"query": "what was I working on", "max_tokens": 2000}'

# Pipeline
curl -X POST http://127.0.0.1:8766/agents/spawn \
  -H "Content-Type: application/json" \
  -d '{"role": "researcher", "agent_type": "worker"}'

# Skills
curl http://127.0.0.1:8766/skills

# Scheduler
curl http://127.0.0.1:8766/scheduled

# Monitoring
curl http://127.0.0.1:8766/monitoring/metrics
```
