# Gnosys Roadmap

## Purpose

This roadmap tracks the build-out of the new Gnosys scaffold.

## Phase 0 - Foundation

- workspace root tooling
- desktop shell scaffold
- backend scaffold
- shared domain package
- documentation alignment

Exit criteria:

- repository installs cleanly
- desktop app boots
- backend health endpoint responds
- shared package compiles

## Phase 1 - Local persistence and event log

- SQLite-backed workspace state
- append-only event log
- backend API reads and writes
- desktop refreshes from persisted state

Exit criteria:

- workspace data survives restart
- events can be appended and re-read
- the desktop reflects backend-backed state

## Phase 2 - Memory engine

- active, episodic, semantic, and procedural layers
- scoped retrieval and explanation trace
- candidate and validated memory states
- consolidation and deduplication foundations

Exit criteria:

- memory can be stored, queried, and inspected
- retrieval behavior differs by scope and role

## Phase 3 - Orchestration and agents

- orchestrator and specialist runtime
- bounded worker spawning
- task decomposition and reporting
- execution controller and approvals

Exit criteria:

- tasks can move through agent-driven execution
- child agents are bounded and observable

## Phase 4 - CRUD surfaces

- tasks
- projects
- agents
- skills
- schedules

Exit criteria:

- core entities can be created and edited through the UI
- entity state remains consistent with the backend store

## Notes

- The roadmap should be updated whenever the scaffold meaningfully changes.
