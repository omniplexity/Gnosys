# Gnosys v0.1 Implementation Plan

## Goal

Ship a real OpenClaw-compatible v0.1 that provides a custom memory plugin with a TypeScript plugin wrapper and a Python backend service. The wrapper owns OpenClaw registration and lifecycle; Python owns storage, retrieval, and consolidation logic.

## Architecture Decision

- Native OpenClaw plugins are JS/TS modules loaded in-process by the Gateway.
- Gnosys v0.1 should therefore be a small TypeScript plugin wrapper, not a pure-Python plugin.
- The wrapper talks to a local Python backend over a narrow RPC boundary; prefer localhost HTTP for v0.1 because it is easier to debug on Windows.
- v0.1 should target the `memory` slot first and register memory-specific runtime pieces. A custom `contextEngine` can wait until the memory path is stable.

## Realistic v0.1 Scope

- Replace the active OpenClaw memory slot with `gnosys`.
- Support explicit store, search, and fetch flows through a Python backend.
- Persist memory in SQLite with a simple embedding adapter abstraction.
- Register memory runtime, prompt section, and flush plan from the TS wrapper.
- Provide one small diagnostic tool or command for health/status.
- Keep configuration small: backend URL/process config, SQLite path, embedding provider settings, and retention defaults.

## Out Of Scope

- Full four-tier memory implementation.
- Multi-agent orchestration.
- Autonomous skill extraction.
- Scheduler / cron execution.
- RL or adaptive learning loops.
- Third-party REST API.
- Full dashboarding, backup UX, or encryption-at-rest.
- Replacing the full OpenClaw `contextEngine` unless memory-slot integration proves insufficient.

## Milestones

### M1 - Plugin Skeleton

- Create `package.json`, `openclaw.plugin.json`, `tsconfig.json`, and `index.ts`.
- Use current OpenClaw conventions: manifest-driven config, `definePluginEntry(...)`, and JS/TS runtime loading.
- Mark the plugin as `kind: "memory"`.

### M2 - Python Backend And Bridge

- Add a Python service with health, store, fetch, and search endpoints.
- Implement the TS bridge client and startup/shutdown handling.
- Support both explicit `backendUrl` mode and spawned local process mode.

### M3 - Memory Slot Integration

- Register memory runtime, prompt section builder, and flush plan resolver.
- Map OpenClaw memory operations onto backend endpoints.
- Keep prompt contribution conservative and bounded.

### M4 - Persistence And Retrieval

- Add SQLite schema for memories and metadata.
- Implement exact + keyword search first.
- Keep embeddings pluggable but optional for initial delivery.

### M5 - Verification And Docs

- Add wrapper unit tests and backend tests.
- Add one integration test or manual verification script for store -> restart -> search.
- Document install, config, and verification steps.

## Proposed File Structure

```text
gnosys/
├── package.json
├── openclaw.plugin.json
├── tsconfig.json
├── index.ts
├── src/
│   ├── config.ts
│   ├── bridge/
│   │   ├── client.ts
│   │   └── process.ts
│   ├── memory/
│   │   ├── runtime.ts
│   │   ├── prompt-section.ts
│   │   └── flush-plan.ts
│   └── tools/
│       └── gnosys_status.ts
├── python/
│   ├── pyproject.toml
│   ├── src/gnosys_backend/
│   │   ├── app.py
│   │   ├── config.py
│   │   ├── db.py
│   │   ├── embeddings.py
│   │   ├── memory_store.py
│   │   └── api/routes.py
│   └── tests/
└── tests/
    ├── plugin/
    └── integration/
```

## Dependency Plan

### TypeScript wrapper

- `openclaw` plugin SDK subpaths, especially `openclaw/plugin-sdk/plugin-entry` and memory registration surfaces.
- `@sinclair/typebox` only where schemas are needed.
- Native `fetch` for backend calls when possible.

### Python backend

- Python 3.11+.
- `fastapi` + `uvicorn` for local RPC.
- `pydantic` for payload validation.
- `sqlite3` or a very thin DB layer; avoid heavy ORM complexity in v0.1.
- `pytest` for backend tests.

## Acceptance Criteria

- OpenClaw discovers `gnosys` via `openclaw.plugin.json` with no manifest/schema errors.
- `plugins.slots.memory = "gnosys"` activates the plugin cleanly.
- The TS wrapper can reach or launch the Python backend on startup.
- A stored memory survives restart and is retrievable through the plugin runtime.
- Memory search returns deterministic SQLite-backed results.
- Backend failures produce actionable diagnostics instead of silent fallback.
- Project docs clearly state that Gnosys is a TS wrapper plus Python backend, not a pure-Python native plugin.

## Test And Verification Steps

1. Install Node and Python dependencies.
2. Run backend tests: `pytest python/tests`.
3. Run plugin tests: `pnpm test`.
4. Enable the plugin and set `plugins.slots.memory = "gnosys"`.
5. Verify discovery with `openclaw plugins inspect gnosys`.
6. Store a test memory through the plugin path.
7. Restart the Gateway and confirm the memory is still returned.
8. Stop the backend and verify the plugin reports a clear health/error state.

## Risks

- JS/Python bridge complexity; mitigate by keeping the RPC contract tiny and versioned.
- Windows subprocess behavior; mitigate with an explicit `backendUrl` override for development.
- OpenClaw SDK drift; mitigate by pinning to a tested plugin SDK/gateway version and documented SDK subpaths.
- Search quality expectations; mitigate by shipping keyword retrieval first and treating embeddings as follow-on work.
- Scope creep from the broader spec; mitigate by keeping v0.1 centered on memory-slot replacement, persistence, and retrieval.

## Practical Notes

- Prefer one plugin package with an embedded `python/` backend directory for the first release.
- Keep the first release operationally simple: one memory slot plugin, one local backend, one SQLite database.
- Treat `contextEngine`, skills, scheduler, and learning features as later milestones after the memory path is stable.
