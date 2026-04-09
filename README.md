# Gnosys

Gnosys is a desktop-native, chat-first agent IDE and operating console focused on durable memory, bounded multi-agent execution, inspectable automation, and local-first persistence.

The repository currently contains a working operational-core build with implemented foundation layers:

- desktop console shell with dedicated section workspaces
- FastAPI backend runtime
- SQLite persistence and event log
- memory retrieval and consolidation
- orchestration and worker spawning
- tasks, projects, agents, skills, and schedules operational surfaces
- autonomy and approval controls
- diagnostics replay and memory review workflows
- schedule daemon, retry guardrails, deferred backoff, and a scheduler service foundation
- project workspace folders and project threads
- standalone chat sessions with durable identity files

## Current stage

The project is past the initial scaffold phase. Backend Phase 1, frontend Phase 2, and the first governed skill-learning layer of Phase 3 are now in place.

- implemented: core workspace, persistence, memory, orchestration, policy controls, schedule automation maturity, context-aware diagnostics, desktop section surfaces, and a first learned-skill extraction/provenance workflow
- in progress: project-thread productivity flow, file and attachment routing, main-agent identity behavior, deeper memory governance, and stronger skill validation/promotion depth
- planned: advanced memory intelligence, formal evaluation, and deeper tool execution

## Running locally

From the repository root:

- `npm install`
- `npm run dev`
- `npm run check`
- `npm run build`
- `npm run test:backend`

`npm run dev` starts the desktop app and backend together.

Recommended validation flow:

1. run `npm run dev`
2. open the desktop shell and verify:
   - `Chat` can create and switch standalone sessions
   - `Projects` can create a project thread and show its workspace path
   - `Sessions` can filter diagnostics by project, thread, and chat session
   - `Scheduled` shows linked run context in history and recovery
3. run `npm run check`
4. run `npm run build`
5. run `npm run test:backend`

## Repository layout

- `apps/desktop/` - React desktop shell and console UI
- `apps/backend/` - FastAPI backend, persistence, policy, memory, orchestration, routers, and services
- `packages/shared/` - shared domain types and seed data
- `docs/` - product, architecture, roadmap, and status documentation

## Documentation

- [docs/INDEX.md](docs/INDEX.md)
- [docs/IMPLEMENTATION-STATUS.md](docs/IMPLEMENTATION-STATUS.md)
- [docs/DELIVERY-PLAN.md](docs/DELIVERY-PLAN.md)
- [docs/PRD.md](docs/PRD.md)
- [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md)
- [docs/ROADMAP.md](docs/ROADMAP.md)
- [docs/CODEX_AUDIT_AND_PLAN.md](docs/CODEX_AUDIT_AND_PLAN.md)
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

1. turn project threads into fuller productivity flows with explicit file and attachment routing
2. deepen main-chat session identity and self-learning behavior around `AGENT.md`, `SOUL.md`, `IDENTITY.md`, and `HEARTBEAT.md`
3. remove the remaining legacy fallback shell from the desktop and finish the section-first composition cleanup
4. deepen memory governance and promotion rules
5. deepen learned-skill validation, routing quality, and rollback governance
6. extend diagnostics into richer historical analysis and diffing
