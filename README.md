# Gnosys

Gnosys is a local-first plugin and backend framework for OpenClaw that provides memory, context retrieval, learning, skills, scheduling, and observability.

## What this repository contains

- `index.ts` and `src/` implement the TypeScript OpenClaw plugin wrapper.
- `python/src/gnosys_backend/` implements the Python backend service.
- `docs/` contains product, architecture, implementation, and operational documentation.

## Documentation map

- [docs/INDEX.md](docs/INDEX.md) - documentation landing page
- [docs/README.md](docs/README.md) - current project summary and quick start
- [docs/PRD.md](docs/PRD.md) - product requirements document
- [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) - technical architecture specification
- [docs/REPOSITORY-OVERVIEW.md](docs/REPOSITORY-OVERVIEW.md) - repository structure and codebase map

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

## Runtime overview

- The OpenClaw plugin entrypoint is `index.ts`.
- Plugin configuration is normalized in `src/config.ts`.
- The backend bridge and process orchestration live under `src/bridge/`.
- Memory/context/learning/skill/scheduler implementations live under `src/` and `python/src/gnosys_backend/`.

## Notes

- The repository is intentionally local-first.
- Documentation has been separated into dedicated files so the repo remains navigable as it grows.
