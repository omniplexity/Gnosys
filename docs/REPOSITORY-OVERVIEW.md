# Repository Overview

## Purpose

This repository houses the current Gnosys implementation: a desktop agent workspace with a backend runtime and shared domain model.

## Top-level layout

- `README.md` - repository overview and quick start
- `CHANGELOG.md` - notable changes
- `CONTRIBUTING.md` - contribution guidance
- `RELEASE.md` - release and versioning policy
- `apps/desktop/` - desktop console application
- `apps/backend/` - FastAPI backend, store, memory, runtime, policy, routers, and services
- `packages/shared/` - shared domain package and seed data
- `docs/` - product, architecture, roadmap, status, and audit documentation

## Workspace roles

### Desktop app

- renders the operator console
- provides the primary chat and workspace surface
- exposes policy, CRUD, replay, and memory review controls

### Backend

- persists core entities to SQLite
- enforces policy and approval controls
- runs memory, orchestration, scheduling, and diagnostics APIs
- separates HTTP routers from backend services so scheduler, approval, and replay logic can evolve without further centralizing `app.py`

### Shared package

- centralizes shared domain types
- keeps backend and desktop aligned on entity shape and seed data

## Current assessment

This repository is no longer a blank scaffold.

- the core product loop is implemented
- the remaining work is to deepen automation and intelligence
- the docs should be updated alongside each new layer
