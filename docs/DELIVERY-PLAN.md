# Gnosys Delivery Plan

Generated: 2026-04-09

## Purpose

This is the concrete near-term execution order from the current state of the repo.

The first four roadmap slices are already landed:

- `v0.0.1` real master chat
- `v0.0.2` master-agent execution loop
- `v0.0.3` self-learning session core
- `v0.0.4` project/thread productivity foundation plus routed attachments

The next work should deepen capability and product clarity rather than broaden the shell again.

## Current priorities

### Priority 1 - `v0.0.5` skill learning and recursive improvement

Why this is next:

- the orchestration loop exists, but specialist behavior is still mostly heuristic
- the product now needs reusable learned capabilities, not just richer metadata

Concrete issues:

1. Detect repeatable workflow patterns from task runs and session activity
2. Create learned-skill draft records from those patterns
3. Connect learned-skill proposals to scenario-based testing
4. Add recursive revision and comparison for learned skills
5. Surface skill invocation in orchestration decisions and replay

Exit criteria:

- repeated work can become a governed skill proposal
- promoted skills affect future execution

### Priority 2 - `v0.0.6` memory browser

Why this is next:

- reflection and daily memory now exist
- users need a product surface to inspect and manage what the system is learning

Concrete issues:

1. Add browse-oriented memory API groupings
2. Build daily / long-term / pinned / candidate memory segmentation
3. Add searchable memory browser UI
4. Add contradiction-resolution UI flows
5. Add provenance and "why surfaced" affordances throughout the memory surface

Exit criteria:

- memory is a usable product surface, not only an operational subsystem

### Priority 3 - personal session management UX

Why this is next:

- the chat product model is now intentionally personal and persistent
- the user needs a clean way to continue, reset, and start new sessions without losing continuity

Concrete issues:

1. Add clean session switcher for the personal chat surface
2. Add "new session" flow with previous-session summary carryover
3. Add clearer indicators of current vs previous session state
4. Add session archive/history behavior without cluttering the thread

Exit criteria:

- the chat surface feels like a stable persistent presence

### Priority 4 - `v0.0.7` extensibility layer

Why this follows:

- custom tools should come after the core agent loop and memory/skill systems are stable enough to use them coherently

Concrete issues:

1. Define the tool registry schema
2. Add local-first tool registration and validation
3. Add policy and approval metadata for tools
4. Add replay and diagnostics visibility for tool calls
5. Integrate tool discovery into orchestration decisions

Exit criteria:

- custom tools can be added cleanly without weakening inspectability

## Supporting maintenance work

These should continue in parallel when low-risk:

- keep `App.tsx` moving toward composition-only ownership
- keep transport contracts aligned between backend, shared package, and desktop
- preserve backend integration-style tests for each milestone
- continue shell polish only when it directly supports behavior milestones

## What should not lead the next pass

Do not prioritize these ahead of the current queue:

- broad new admin surfaces
- nonessential dashboard expansion
- project-thread UI complexity inside the personal chat surface
- heavy plugin/tool expansion before the skill loop is ready

## Immediate recommendation

Start with `v0.0.5` and keep the implementation order:

1. learned-skill proposal generation
2. learned-skill test/evaluation loop
3. promoted-skill invocation inside orchestration
4. recursive improvement and rollback

That is the highest-leverage next move for turning the current system from a persistent orchestrator into a genuinely improving master-agent product.
