# Changelog

All notable changes to Gnosys will be documented in this file.

## [Unreleased]

### Added

- Contributor guide at `CONTRIBUTING.md`
- Release/versioning guide at `RELEASE.md`
- Repository overview at `docs/REPOSITORY-OVERVIEW.md`
- Milestone roadmap cleanup in `docs/ROADMAP.md`
- Updated repo-level documentation pointers

### Changed

- Aligned the root README to the actual OpenClaw plugin/backend repository structure
- Updated the docs index to surface repo hygiene and release docs

### Fixed

- TypeScript spawn-process error handling now safely narrows the `code` property before accessing it

## [1.0.0] - 2026-04-03

### Added

- OpenClaw plugin entrypoint
- Python FastAPI backend
- memory storage and retrieval
- context assembly
- learning pipeline
- skills management
- scheduler support
- monitoring support
- backup and migration tools
- CLI surface for backend management

### Notes

- This is the repository baseline version reflected in `package.json` and `python/pyproject.toml`.
