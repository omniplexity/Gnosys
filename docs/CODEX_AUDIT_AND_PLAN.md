# Codex Audit And Plan

## Current strengths

- Gnosys already has a working desktop shell, FastAPI backend, SQLite persistence, event logging, bounded orchestration, schedule history, approval controls, and memory workflows.
- The repo is not a scaffold. Core product surfaces and tests already exist and support incremental refactor instead of architectural replacement.
- Scheduling, approvals, replay, and diagnostics already have usable product behavior, which makes service extraction practical.

## Current architectural bottlenecks

- [`app.py`](/Users/storm/Desktop/Gnosys/apps/backend/src/gnosys_backend/app.py) had become both composition root and backend control plane implementation.
- Schedule policy, dispatch, retry, and daemon behavior were tightly coupled.
- Approval replay and diagnostics/replay assembly were centralized in one backend file.
- The frontend remains relatively monolithic in [`App.tsx`](/Users/storm/Desktop/Gnosys/apps/desktop/src/App.tsx), even though module extraction has started.

## Immediate risks

- Scheduler behavior can drift when manual run, retry, approval resolution, and daemon polling each own part of the lifecycle.
- Approval execution logic becomes harder to extend safely when every mutation action is handled inline.
- Replay and diagnostics logic is high-value operational infrastructure and should not stay embedded in route registration code.
- Broad backend growth without service/router boundaries increases regression risk for every future feature pass.

## Recommended implementation order

1. Extract scheduler service and runner foundation
2. Extract approval execution and replay services
3. Split backend routes into domain routers while preserving API contracts
4. Expand scheduler and replay test coverage
5. Update docs to match the new backend structure and maturity
6. Continue frontend maintainability work after backend Phase 1 is stable

## Now / Next / Later

### Now

- Introduce `services/` and `routers/` on the backend
- Move scheduler lifecycle logic into a dedicated scheduler service
- Move approval execution into an approval service
- Move replay timeline/comparison and diagnostics helpers into a replay service
- Keep manual run, retry, approval gating, replay visibility, and SQLite persistence behavior intact

### Next

- Refactor desktop state and fetch logic out of [`App.tsx`](/Users/storm/Desktop/Gnosys/apps/desktop/src/App.tsx) into domain hooks and focused modules
- Deepen memory governance with explicit promotion and contradiction semantics

### Later

- Improve richer recurring execution semantics and background runner durability
- Expand skill lifecycle maturity, project scoping, and promotion/rollback workflow depth
- Continue memory and diagnostics productization

## Mapping from current code to target architecture

- Backend composition root:
  - current: `apps/backend/src/gnosys_backend/app.py`
  - target: thin app factory plus router inclusion and service wiring
- Scheduler lifecycle:
  - current: `apps/backend/src/gnosys_backend/scheduler.py`
  - target: `apps/backend/src/gnosys_backend/services/scheduler_service.py`
- Approval replay:
  - current: inline in `app.py`
  - target: `apps/backend/src/gnosys_backend/services/approval_service.py`
- Replay and diagnostics helpers:
  - current: inline in `app.py`
  - target: `apps/backend/src/gnosys_backend/services/replay_service.py`
- Route registration:
  - current: one large FastAPI file
  - target: `apps/backend/src/gnosys_backend/routers/` by domain

## Incremental implementation note

This phase is a maturity pass, not a rewrite. It preserves the current Gnosys architecture, local-first persistence model, approval semantics, orchestration behavior, and API shape while introducing the service and router seams needed for deeper scheduling, governance, and UI decomposition work.

## Phase 2 progress note

Frontend maintainability work is now underway:

- shared response/error handling is centralized under `apps/desktop/src/lib/`
- `App.tsx` is being reduced to a composition shell over domain hooks
- desktop state for snapshot loading, orchestration launch, chat, memory, policy, CRUD, schedules, replay, and skill lifecycle has begun moving into `apps/desktop/src/hooks/`
- isolated rendering helpers are beginning to move into `apps/desktop/src/components/`

This is still an incremental refactor. The goal is to preserve the current product behavior while making the desktop shell safer to evolve.

## Phase 3 progress note

Skill learning and recursive improvement now have a first governed foundation:

- backend skill metadata now tracks provenance, evidence count, success signals, invocation hints, promotion notes, and rollback notes
- learned execution evidence is persisted separately from authored skill definitions so source episodes stay inspectable
- `services/skill_learning_service.py` can analyze repeated successful task runs and derive learned candidate skills with explicit provenance links
- the skills API now exposes learned-skill extraction and lifecycle evidence without changing the broader workspace snapshot contract
- orchestration keeps the current bounded routing behavior but now sees both active skills and candidate learned procedures as routing context
- the desktop skills workspace now distinguishes learned lifecycle states and shows provenance/evidence metadata

This remains governed learning rather than automatic mutation. Learned skills land as `candidate` records and still require explicit testing, promotion, or rollback decisions.
