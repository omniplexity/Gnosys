# Repository Overview

## Purpose

This repository is a clean scaffold for the next Gnosys build.

## Top-level layout

- `README.md` - repository overview
- `CHANGELOG.md` - notable changes
- `CONTRIBUTING.md` - contribution guidance
- `RELEASE.md` - versioning and release policy
- `apps/desktop/` - desktop console app
- `apps/backend/` - Python backend scaffold
- `packages/shared/` - shared domain package
- `docs/` - architecture, roadmap, and project docs

## Workspace roles

### Desktop app

- renders the operator console
- consumes shared domain data
- provides the primary chat/work surface

### Backend scaffold

- exposes health and status endpoints
- becomes the runtime home for memory, orchestration, and persistence

### Shared package

- centralizes navigation and domain types
- keeps the desktop and backend aligned on data shape

## Notes

- This file is a codebase map for the scaffolded repo.
- It should be updated as new packages and apps are added.
