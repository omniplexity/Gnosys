# Gnosys Documentation Index

## Overview

Gnosys is an operational-core desktop agent platform with implemented persistence, memory, orchestration, policy, CRUD, and diagnostics layers. The remaining work is about hardening, deepening automation, and improving intelligence rather than creating the initial skeleton.

## Canonical docs

- [README.md](../README.md) - repository overview and quick start
- [IMPLEMENTATION-STATUS.md](./IMPLEMENTATION-STATUS.md) - current implementation stage and gaps
- [DELIVERY-PLAN.md](./DELIVERY-PLAN.md) - phased near-term backlog and execution order
- [PRD.md](./PRD.md) - product goals and requirements
- [ARCHITECTURE.md](./ARCHITECTURE.md) - subsystem architecture and implementation mapping
- [ROADMAP.md](./ROADMAP.md) - completed phases and next build layers
- [GNOSYS_AUDIT_REPORT.md](./GNOSYS_AUDIT_REPORT.md) - repository audit and gap review
- [REPOSITORY-OVERVIEW.md](./REPOSITORY-OVERVIEW.md) - codebase map
- [PROJECT.md](./PROJECT.md) - project summary and status

## Supporting docs

- [docs/README.md](./README.md)
- [CONTRIBUTING.md](../CONTRIBUTING.md)
- [RELEASE.md](../RELEASE.md)
- [CHANGELOG.md](../CHANGELOG.md)

## Workspace structure

- [apps/desktop/](../apps/desktop/) - desktop UI
- [apps/backend/](../apps/backend/) - backend runtime
- [packages/shared/](../packages/shared/) - shared types and seed data

## Current stage in one line

Phase 2 is complete: the control plane, scheduling maturity, context-aware diagnostics, project threads, and standalone chat sessions are live, and the next work is deeper project/session behavior on top of that core.
