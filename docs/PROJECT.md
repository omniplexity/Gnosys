# Gnosys Project

## Summary

Gnosys is a local-first OpenClaw plugin and backend repository for memory, context retrieval, learning, skills, scheduling, and observability.

## Current version

- `package.json`: `1.0.0`
- `python/pyproject.toml`: `1.0.0`

## Current status

- TypeScript wrapper implemented
- Python backend implemented
- CLI implemented
- Memory storage and retrieval implemented
- Context assembly implemented
- Learning, skills, scheduler, monitoring, backup, and migration implemented
- Documentation aligned to the current repository structure

## Docs

- [README.md](../README.md)
- [docs/INDEX.md](./INDEX.md)
- [docs/README.md](./README.md)
- [docs/ROADMAP.md](./ROADMAP.md)
- [CHANGELOG.md](../CHANGELOG.md)
- [CONTRIBUTING.md](../CONTRIBUTING.md)
- [RELEASE.md](../RELEASE.md)

## Architecture

- The TypeScript layer acts as the OpenClaw plugin wrapper and bridge.
- The Python layer provides the backend service and CLI.
- The repo uses local HTTP between the wrapper and backend rather than embedding all runtime logic in the plugin entrypoint.

## Notes

- This repository is not a desktop UI project.
- The current focus is on backend capability, reliability, and clean documentation.
