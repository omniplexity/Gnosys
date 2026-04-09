# Gnosys Roadmap

## Purpose

This document tracks the directional roadmap from the current local-first master-agent product core to the first usable "agentic OS" beta.

Use `IMPLEMENTATION-STATUS.md` for factual status and `DELIVERY-PLAN.md` for the concrete next execution order.

## Product north star

Gnosys should become:

- a local-first master-agent workstation
- centered on a persistent personal chat presence
- backed by durable memory, identity, reflection, and semantic retrieval
- able to delegate work across a fixed specialist team
- eventually expandable through skills and custom tools without losing inspectability

## Completed roadmap slices

### v0.0.1 - Real master chat

Completed.

- persistent chat sessions and chat messages
- session send/respond flow
- canonical chat thread rendering

### v0.0.2 - Master agent execution loop

Completed at the first product level.

- master-agent decision object
- structured delegation steps
- fixed specialist team routing
- in-thread delegation visibility

### v0.0.3 - Self-learning session core

Completed at the first governed level.

- session reflections
- candidate memory generation
- daily memory rollups
- governed identity proposals

### v0.0.4 - Project/thread productivity foundation

Completed at the backend foundation level, intentionally narrowed at the primary chat UX level.

- routed attachments
- context-aware storage paths
- personal/project/project-thread backend mode support
- personal-only primary chat product model

## Active roadmap slices

### v0.0.5 - Skill learning and recursive improvement

Goal:

Turn repeated successful work into governed reusable skills that affect future execution.

Scope:

- detect repeatable workflows from runs and chat sessions
- generate learned-skill drafts from repeated patterns
- test learned drafts against scenarios
- promote passing skills into the stable set
- support recursive skill revision with comparison and rollback

Exit criteria:

- repeated work can produce a skill proposal
- proposed skills can be tested and promoted
- promoted skills are visible in future orchestration decisions

### v0.0.6 - Memory browser and memory operations

Goal:

Expose memory as a clear product surface instead of only a review/diagnostics subsystem.

Scope:

- dedicated memory browser
- daily vs long-term vs pinned vs candidate segmentation
- searchable and explainable memory results
- contradiction review and resolution UX

Exit criteria:

- users can browse and manage memory intentionally
- surfaced memories explain why they were retrieved

### Personal session management pass

Goal:

Make the chat surface feel like a real persistent presence that users can leave and return to.

Scope:

- cleaner session switching
- start-new-session flow
- previous-session context preservation and summary cues
- clearer continuity between archived/previous/current session state

Exit criteria:

- switching or starting a new session feels deliberate and low-friction
- the product preserves continuity without cluttering the thread

### v0.0.7 - Extensibility layer

Goal:

Let Gnosys register and invoke custom tools through a stable local-first contract.

Scope:

- tool registry
- typed input/output schemas
- execution scope and approval metadata
- replay and diagnostics visibility for tool calls

Exit criteria:

- tools can be added without changing the orchestration core
- tool use remains auditable and policy-aware

### v0.1.0 - Agentic OS beta

Goal:

Ship the first version that coherently combines:

- personal persistent chat
- memory continuity
- skill-backed execution
- governed extensibility
- supporting operational surfaces

Exit criteria:

- the product feels like one workstation rather than a set of admin surfaces
- the master agent can maintain continuity, do work, learn, and improve over time

## Roadmap notes

- Keep the personal chat model central.
- Do not turn the main chat into a project/thread control panel.
- Push project and thread productivity into supporting workflows unless they can be integrated without clutter.
- Prefer behavior depth over UI breadth.
