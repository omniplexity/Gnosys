# Gnosys

Gnosys is a local-first OpenClaw plugin and Python backend for memory, context retrieval, learning, skills, scheduling, and observability.

## Current version

- `package.json`: `1.0.0`
- `python/pyproject.toml`: `1.0.0`

## What lives here

- `index.ts` is the OpenClaw plugin entrypoint.
- `src/` contains the TypeScript plugin wrapper, HTTP bridge, memory runtime, and tools.
- `python/src/gnosys_backend/` contains the FastAPI backend, CLI, storage, search, skills, scheduler, and monitoring services.
- `docs/` contains the product, architecture, implementation, and repo hygiene documentation.

## Key docs

- [docs/INDEX.md](docs/INDEX.md)
- [docs/README.md](docs/README.md)
- [docs/PRD.md](docs/PRD.md)
- [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md)
- [docs/REPOSITORY-OVERVIEW.md](docs/REPOSITORY-OVERVIEW.md)
- [docs/ROADMAP.md](docs/ROADMAP.md)
- [CHANGELOG.md](CHANGELOG.md)
- [CONTRIBUTING.md](CONTRIBUTING.md)
- [RELEASE.md](RELEASE.md)

## Setup

```bash
npm install
python -m pip install -e "./python[test]"
pip install croniter
```

## Verify

```bash
npm run check
pytest python/tests
python -m uvicorn gnosys_backend.app:app --app-dir python/src --host 127.0.0.1 --port 8766
```

## Current repo posture

- The TypeScript and Python stacks are intentionally separated by a local HTTP bridge.
- The repo is structured around a memory-first plugin, not a desktop UI shell.
- Documentation now distinguishes product intent, implementation detail, release policy, and milestone planning.
