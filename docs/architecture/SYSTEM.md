# Gnosys Architecture

## Overview

Gnosys is a unified intelligence framework for OpenClaw that combines:
- Multi-agent multi-layer pipeline orchestration
- Advanced multi-tier memory system
- Self-learning loop for continuous improvement
- Autonomous skill system
- Cron-like scheduler
- Full observability through monitoring

## Version

**v1.0** - Production Ready

## Architecture Diagram

```
┌─────────────────────────────────────────────────────────────────────────┐
│                           OpenClaw Gateway                              │
├─────────────────────────────────────────────────────────────────────────┤
│  Memory Slot │ ContextEngine Slot │ Tools │ Commands │ Lifecycle Hooks │
└────────────────────────────┬────────────────────────────────────────────┘
                             │
                    HTTP Bridge (TypeScript)
                             │
                    ┌────────▼────────┐
                    │  GnosysService  │
                    │   (service.ts)  │
                    └────────┬────────┘
                             │ HTTP
                    ┌────────▼────────┐
                    │ Python Backend  │
                    │   FastAPI       │
                    └────────┬────────┘
                             │
     ┌───────────────────────┼───────────────────────┐
     │           │           │           │           │
┌────▼───┐  ┌────▼───┐  ┌───▼────┐  ┌──▼────┐  ┌───▼────┐
│Memory  │  │Context │  │ Pipeline│  │Learning│  │Skills  │
│Store   │  │Retrieval│  │  Store │  │ Store │  │ System │
└────┬───┘  └────┬───┘  └───┬────┘  └───┬────┘  └───┬────┘
     │           │           │           │           │
┌────▼───┐  ┌────▼───┐  ┌───▼────┐  ┌──▼────┐  ┌───▼────┐
│SQLite  │  │Vector  │  │ Agents │  │Traject│  │ Skills │
│(core)  │  │ Store  │  │ Table  │  │ Store │  │ Storage│
└────────┘  └────────┘  └────────┘  └────────┘  └────────┘
```

## Core Components

### TypeScript Plugin Wrapper (`src/`)

| File | Purpose |
|------|---------|
| `index.ts` | Plugin entrypoint with OpenClaw integration |
| `service.ts` | GnosysService - orchestration layer |
| `config.ts` | Configuration normalization and validation |
| `bridge/client.ts` | HTTP client to Python backend |
| `bridge/process.ts` | Spawn-local backend process manager |

### Tools (`src/tools/`)

| Tool | Description |
|------|-------------|
| `gnosys_status.ts` | Diagnostic tool for backend connectivity |
| `gnosys_store_memory.ts` | Store memory to backend |
| `gnosys_get_memory.ts` | Fetch memory by ID |
| `gnosys_delete_memory.ts` | Delete memory by ID |
| `memory_search.ts` | Keyword search memories |
| `gnosys_semantic_search.ts` | Hybrid semantic + keyword search |
| `gnosys_context_preview.ts` | Context preview with token budget |
| `gnosys_pipeline.ts` | Multi-agent pipeline client |
| `gnosys_learning.ts` | Learning client for pattern detection |
| `gnosys_skills.ts` | Skill management tool |
| `gnosys_scheduler.ts` | Scheduler tool |

### Memory Integration (`src/memory/`)

| File | Purpose |
|------|---------|
| `runtime.ts` | Memory runtime registration |
| `prompt-section.ts` | Prompt contribution |
| `flush-plan.ts` | Flush plan registration |

### Context Engine (`src/context-engine/`)

| File | Purpose |
|------|---------|
| `engine.ts` | Context engine for prompt assembly |
| `message-utils.ts` | Message utilities for context |

### Python Backend (`python/src/gnosys_backend/`)

| File | Purpose |
|------|---------|
| `app.py` | FastAPI app + uvicorn entrypoint |
| `config.py` | Runtime configuration |
| `db.py` | SQLite connection and schema |
| `models.py` | Pydantic request/response models |
| `memory_store.py` | MemoryStore with keyword search + pruning |
| `embeddings.py` | Embeddings provider abstraction |
| `vector_store.py` | Vector storage with cosine similarity |
| `entity_extraction.py` | Entity extraction and storage |
| `context_retrieval.py` | Multi-tier context retrieval |
| `pipeline.py` | Multi-agent pipeline orchestration |
| `learning.py` | Self-learning pattern detection |
| `trajectory_store.py` | Trajectory logging for learning |
| `skills.py` | Skill detection, extraction, storage |
| `scheduler.py` | Cron-like task scheduling |
| `monitoring.py` | Health checks and metrics |
| `api/routes.py` | HTTP route handlers |

## Memory Tiers

```
┌─────────────────────────────────────────────────────────────┐
│                      Memory Core                            │
├─────────────────────────────────────────────────────────────┤
│  Tier 1: Working   ←→  Tier 2: Episodic  ←→  Tier 3: Semantic│
│       ↓                                    ↓                │
│  Tier 4: Archive ←──────────────────────────────────────────│
└─────────────────────────────────────────────────────────────┘
```

| Tier | Purpose | Storage | Retention |
|------|---------|---------|-----------|
| Working | Immediate context, current conversation | In-memory (RAM) | Current session |
| Episodic | Session history, recent interactions | SQLite + Vector | Configurable (default: 30 days) |
| Semantic | Entity knowledge, facts, relationships | Vector DB | Permanent until pruned |
| Archive | Long-term storage, historical data | SQLite + Files | Configurable (default: 365 days) |

## Data Flow

### 1. Memory Storage
```
User Message → OpenClaw → gnosys_store_memory → HTTP Client → /memories POST
                                                            ↓
                                                    SQLite + Vector Store
```

### 2. Context Retrieval
```
Query → /context/retrieve → ContextRetrievalStore → Memory/Vector Search
                                                       ↓
                                            Token Budget Management
                                                       ↓
                                            Assembly → Prompt
```

### 3. Pipeline Execution
```
Task → /pipeline/execute → PipelineStore → Agent Coordination Modes
                                                      ↓
                                          Sequential/Parallel/Hierarchical/Debate
                                                      ↓
                                          Results Aggregation
```

### 4. Skill Learning
```
Trajectories → Pattern Detection → Skill Extraction → SKILL.md Storage
                                                                  ↓
                                              Skill Matching ← Task Query
```

### 5. Scheduled Tasks
```
Cron Schedule → Due Tasks → Task Execution → History Recording
                  ↓
           Delivery (announce/webhook)
```

## Technology Stack

| Layer | Technology |
|-------|------------|
| Plugin Wrapper | TypeScript + OpenClaw SDK |
| Backend | Python 3.11+ + FastAPI |
| Database | SQLite (core) + Vector (embeddings) |
| Scheduler | croniter |
| Embeddings | sentence-transformers (local) or OpenAI |
| Server | uvicorn |

## Configuration

See [Configuration Guide](../guides/CONFIGURATION.md) for full details.
