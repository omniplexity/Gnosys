# Gnosys Audit Report

Generated: 2026-04-06

## Overall assessment

The repository now contains a functioning local-first product core rather than a bare scaffold. The desktop shell, backend runtime, persistence layer, memory system, orchestration runtime, policy layer, CRUD workspace, schedule controls, replay diagnostics, and memory review workflow are all represented in the codebase.

## Verified checks

| Check | Result |
|---|---|
| `npm run check` | PASS |
| `npm run build` | PASS |
| `python -m pytest apps/backend/tests -q` | PASS |

## Architecture review

### Workspace root

- workspace scripts coordinate the desktop app, backend, and shared package
- Node, Python, and build artifacts are ignored appropriately
- repository docs now describe the current implementation rather than an archive state
- lockfile is checked in and aligned with the workspace

### Desktop app

- `apps/desktop/` provides the main console shell
- the app exposes chat, tasks, projects, agents, skills, scheduled, sessions, and settings
- the inspector and diagnostics surfaces are already present
- the UI is functional, but still intentionally dense and operational rather than polished

### Shared package

- `packages/shared/` defines the common domain types used by desktop and backend
- shared models now include policy modes, schedule policies, replay structures, and project-scoped fields

### Backend runtime

- `apps/backend/` contains the FastAPI app, store, memory engine, runtime, and policy layer
- the backend is no longer minimal
- the backend now persists the core entities and orchestrates memory, approvals, schedule runs, and replay data

## Findings

### No blocking structural issues found

The repository is organized well enough to continue layering product behavior without needing to rebuild the foundation.

### Residual gaps

The main gaps are capability gaps, not structural gaps:

- schedule execution still needs an always-on runner and better retry visibility
- memory governance needs clearer promotion, contradiction, and forgetting rules
- skills still need authoring, testing, promotion, and rollback workflows
- diagnostics still need deeper diffing and replay analytics
- policy UX still needs better inheritance and risk explanation surfaces

## Risk assessment

### Memory quality risk

Memory can still become noisy or stale unless promotion and contradiction handling are disciplined.

### Automation risk

Schedules and approval replay are in place, but the system still needs a stronger background execution model to avoid relying on manual triggers.

### UX complexity risk

The application already exposes many operational surfaces. Without careful hierarchy and defaults, it could become difficult to use.

### Tooling risk

The local execution layer exists conceptually and in policy form, but deeper sandboxing and tool integration remain to be completed.

## Recommendation

Treat the repository as an operational core that is ready for maturation work, not as a completed mature product.

The highest-value next steps are:

1. schedule daemon and retry maturity
2. memory governance and promotion rules
3. skill lifecycle workflows
4. richer diagnostics and replay analysis
5. formal evaluation and regression coverage

## Conclusion

Gnosys is now a real implementation with a strong foundation. The remaining work is to deepen the product’s intelligence, automation, and trust surfaces rather than to assemble the system from scratch.
