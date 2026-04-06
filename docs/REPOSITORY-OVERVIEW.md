# Repository Overview

## Purpose

This repository houses the Gnosys OpenClaw integration and backend. It combines a TypeScript plugin wrapper with a Python service responsible for memory, context retrieval, learning, skills, scheduling, monitoring, and related runtime operations.

## Top-level layout

- `index.ts` - OpenClaw plugin entrypoint
- `src/` - TypeScript implementation for the plugin wrapper, bridge, memory layer, and tools
- `python/` - Python backend implementation and tests
- `docs/` - documentation for product scope, architecture, implementation, and operational guidance
- `openclaw.plugin.json` - plugin metadata
- `package.json` - TypeScript tooling and checks
- `tsconfig.json` - TypeScript compiler settings

## Key runtime areas

### TypeScript layer

- `src/config.ts` - config schema and normalization
- `src/service.ts` - service orchestration and backend client wrapper
- `src/bridge/` - HTTP bridge and child process management
- `src/memory/` - memory prompt, flush planning, and runtime helpers
- `src/tools/` - plugin tools for status, storage, search, learning, scheduler, backup, and migration

### Python layer

- `python/src/gnosys_backend/app.py` - backend application entrypoint
- `python/src/gnosys_backend/api/` - HTTP routes
- `python/src/gnosys_backend/memory_store.py` - memory persistence
- `python/src/gnosys_backend/vector_store.py` - embeddings and vector retrieval
- `python/src/gnosys_backend/context_retrieval.py` - context assembly
- `python/src/gnosys_backend/learning.py` - learning and pattern extraction
- `python/src/gnosys_backend/skills.py` - skill management
- `python/src/gnosys_backend/scheduler.py` - scheduling
- `python/src/gnosys_backend/monitoring.py` - observability

## Documentation intent

The new documentation files in `docs/` are meant to separate the product vision from the implementation details:

- `docs/PRD.md` captures the target product behavior and scope.
- `docs/ARCHITECTURE.md` describes the intended system architecture.
- `docs/REPOSITORY-OVERVIEW.md` explains how the repository is organized.

## Clean repository rules

- Commit source, docs, and lockfiles.
- Do not commit `node_modules/`, `dist/`, logs, or build artifacts.
- Keep product and architecture narrative in `docs/`, not in ad hoc root files.
