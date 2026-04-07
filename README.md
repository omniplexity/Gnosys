# Gnosys

Gnosys is a desktop-native, chat-first agent IDE and operating console focused on durable memory, bounded multi-agent execution, inspectable automation, and local-first persistence.

The repository currently contains a working product scaffold with implemented foundation layers:

- desktop console shell
- FastAPI backend runtime
- SQLite persistence and event log
- memory retrieval and consolidation
- orchestration and worker spawning
- tasks, projects, agents, skills, and schedules CRUD
- autonomy and approval controls
- diagnostics replay and memory review workflows

## Current stage

The project is past the initial scaffold phase and is now in the operational core stage.

- implemented: core workspace, persistence, memory, orchestration, policy controls, CRUD, and diagnostics
- in progress: schedule automation, memory governance, skill lifecycle, and richer replay analysis
- planned: advanced memory intelligence, learned skills, formal evaluation, and deeper tool execution

## Running locally

From the repository root:

- `npm install`
- `npm run dev`
- `npm run check`
- `npm run build`
- `npm run test:backend`

`npm run dev` starts the desktop app and backend together.

## Repository layout

- `apps/desktop/` - React desktop shell and console UI
- `apps/backend/` - FastAPI backend, persistence, policy, memory, and orchestration
- `packages/shared/` - shared domain types and seed data
- `docs/` - product, architecture, roadmap, and status documentation

## Documentation

- [docs/INDEX.md](docs/INDEX.md)
- [docs/IMPLEMENTATION-STATUS.md](docs/IMPLEMENTATION-STATUS.md)
- [docs/PRD.md](docs/PRD.md)
- [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md)
- [docs/ROADMAP.md](docs/ROADMAP.md)
- [docs/GNOSYS_AUDIT_REPORT.md](docs/GNOSYS_AUDIT_REPORT.md)
- [docs/REPOSITORY-OVERVIEW.md](docs/REPOSITORY-OVERVIEW.md)
- [CONTRIBUTING.md](CONTRIBUTING.md)
- [RELEASE.md](RELEASE.md)
- [CHANGELOG.md](CHANGELOG.md)

## What this repo is not

- not a legacy OpenClaw plugin archive
- not a cloud-only assistant
- not a multi-channel chat integration product
- not a fully autonomous unrestricted agent system

## Next focus areas

The next layers to deepen are:

1. schedule daemon and retry automation
2. memory governance and promotion rules
3. skill authoring, testing, and rollback
4. richer diagnostics replay and diffing
5. formal evaluation and regression benchmarks
