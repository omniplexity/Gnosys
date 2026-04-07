# Gnosys Roadmap

## Purpose

This roadmap tracks the transition from the operational core to a more mature autonomous desktop platform.

## Completed layers

- repository and workspace scaffold
- desktop shell and shared package setup
- SQLite persistence and event log
- memory retrieval and consolidation
- orchestration and worker spawning
- tasks, projects, agents, skills, and schedules CRUD
- autonomy and approval controls
- project-scoped policy routing
- schedule execution and retry flows
- replay diagnostics and memory review workflows

## Current stage

Gnosys is now past the scaffolding phase and into the operational core stage.

- the product already works end-to-end for core workflows
- the missing pieces are depth, hardening, and automation maturity
- the remaining layers should refine behavior rather than define the product from scratch

## Next roadmap layers

### Layer 1 - Schedule automation maturity

- always-on schedule runner
- recurring execution lifecycle
- retries, backoff, and failure notifications
- schedule history and execution visibility
- approval-aware scheduled launches

Exit criteria:

- schedules can run without manual triggering
- failures are visible and actionable
- scheduled tasks are observable in the same run history model as interactive work

### Layer 2 - Memory governance

- explicit candidate review rules
- contradiction detection and resolution
- pinning and forgetting controls
- promotion thresholds and validation scoring
- memory regression checks

Exit criteria:

- durable memory promotion is explainable and repeatable
- stale or conflicting memories can be handled intentionally
- memory behavior can be tested

### Layer 3 - Skill lifecycle

- authored skill editor improvements
- learned skill drafts
- skill testing pipeline
- promotion and rollback
- project-scoped skill routing

Exit criteria:

- skills can move through a visible lifecycle
- failed skill experiments do not contaminate the stable skill set

### Layer 4 - Diagnostics and replay

- richer run timelines
- output diffing across runs
- agent-by-agent replay views
- search and filtering over historical runs
- metrics around latency, failures, and cost

Exit criteria:

- users can inspect how a run unfolded without opening raw logs only
- comparisons across runs are actionable

### Layer 5 - Policy UX

- project policy inheritance editor
- explicit risk labels for actions
- better approval reasons and remediation notes
- clearer autonomy mode state in the desktop UI

Exit criteria:

- policy behavior is understandable without reading backend code
- users can tell why an action was gated or allowed

### Layer 6 - Evaluation and intelligence

- formal memory retrieval benchmarks
- delegation quality benchmarks
- procedural learning evals
- skill promotion tests
- memory and agent regression suites

Exit criteria:

- changes to the system can be measured against a repeatable baseline
- product improvements can be validated instead of inferred

### Layer 7 - Advanced automation

- browser automation
- desktop action automation
- deeper recursive planning modes
- branch comparison and arbitration among worker outputs
- learned workflow extraction

Exit criteria:

- the platform can support more autonomous operational work without losing inspectability

## Notes

- The roadmap should be kept aligned with the implementation status document.
- If a layer becomes partially implemented, mark it there first and update this roadmap second.
