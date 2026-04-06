# Contributing to Gnosys

Gnosys is now a live scaffold for a desktop console, backend runtime, and shared domain package. Contributions should keep the foundation modular and easy to extend.

## Before you start

- Read [README.md](README.md) and [docs/INDEX.md](docs/INDEX.md).
- Run `npm install` and `python -m pip install -e "./apps/backend[test]"` once the workspace is bootstrapped.
- Check [CHANGELOG.md](CHANGELOG.md) to understand recent scaffolding changes.

## What to contribute

- Desktop shell work in `apps/desktop/`
- Backend routes and runtime scaffolding in `apps/backend/`
- Shared domain models in `packages/shared/`
- Documentation updates that keep the scaffold coherent

## Branching and commits

- Use a feature branch.
- Keep commits focused.
- Prefer one logical change per commit.

## Code expectations

- Keep TypeScript strict.
- Keep Python routes and models explicit and lightweight.
- Avoid coupling the desktop shell directly to backend implementation details.
- Prefer shared domain types over duplicated constants.

## Documentation expectations

- Update docs whenever the scaffold structure changes.
- Keep `README.md`, `docs/INDEX.md`, and `docs/REPOSITORY-OVERVIEW.md` aligned.
- If a file moves, update links in the same change.

## Testing expectations

- Run `npm run check` after TypeScript changes.
- Run `npm run build` before shipping the desktop scaffold.
- Run `python -m pytest apps/backend/tests -q` after backend changes.

## Release notes

- Record scaffold changes in `CHANGELOG.md`.
- Keep `RELEASE.md` aligned with the current package layout and versioning approach.
