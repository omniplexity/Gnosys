# Gnosys v1.0.0

Gnosys is a unified intelligence framework for OpenClaw that combines:

- multi-agent pipeline orchestration
- multi-tier memory with semantic search
- self-learning loop for continuous improvement
- autonomous skill management
- cron-like task scheduling
- monitoring and observability
- a CLI for backend management

## Repository status

- `package.json` version: `1.0.0`
- `python/pyproject.toml` version: `1.0.0`
- TypeScript plugin wrapper: implemented
- Python backend: implemented
- Repository documentation: aligned to the current codebase

## What the repository currently does

### TypeScript wrapper

- normalizes plugin configuration
- bridges OpenClaw to the local Python backend
- registers memory, search, skills, scheduler, backup, and migration tools
- exposes the plugin command and CLI helper

### Python backend

- serves the FastAPI backend
- persists and retrieves memories
- performs hybrid semantic and keyword search
- builds prompt context within token budgets
- stores trajectories for learning
- manages skills and schedules
- exposes monitoring and backup endpoints

## Documentation

- [README.md](../README.md) - repository overview and setup
- [INDEX.md](./INDEX.md) - documentation index
- [PRD.md](./PRD.md) - product requirements
- [ARCHITECTURE.md](./ARCHITECTURE.md) - technical architecture
- [REPOSITORY-OVERVIEW.md](./REPOSITORY-OVERVIEW.md) - codebase map
- [ROADMAP.md](./ROADMAP.md) - milestone roadmap
- [GNOSYS_AUDIT_REPORT.md](./GNOSYS_AUDIT_REPORT.md) - codebase audit

## Setup

```bash
npm install
python -m pip install -e "./python[test]"
pip install croniter
```

## Verification

```bash
npm run check
pytest python/tests
python -m uvicorn gnosys_backend.app:app --app-dir python/src --host 127.0.0.1 --port 8766
```

## Notes

- The repo is intentionally local-first.
- The plugin/backend boundary is kept explicit.
- Documentation separates product intent, implementation, release policy, and roadmap planning.
