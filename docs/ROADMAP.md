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

- persistent orchestrator and specialist runtime
- bounded worker spawning with recursion and child-count limits
- task decomposition, reporting, and run summaries
- approval gates for sensitive objectives
- inspectable task-run and agent-run trees

Exit criteria:

- tasks can move through agent-driven execution
- child agents are bounded, inspectable, and logged

## Phase 4 - CRUD surfaces

- task editing, project management, agent administration, skill management, and schedule control
- list/create/update/delete flows for the core operational entities
- inline desktop forms backed by the same SQLite store
- event logging for entity lifecycle changes

Exit criteria:

- core entities can be created, edited, and removed through the UI
- entity state remains consistent with the backend store
- the CRUD workspace is the final major foundation layer before product specialization

## Notes

- The roadmap should be updated whenever the scaffold meaningfully changes.
