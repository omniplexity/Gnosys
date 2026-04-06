# Contributing to Gnosys

This repository is maintained as a local-first OpenClaw plugin and backend. Contributions should preserve that structure and keep the TypeScript wrapper, Python backend, and documentation in sync.

## Before you start

- Read [README.md](README.md), [docs/INDEX.md](docs/INDEX.md), and [RELEASE.md](RELEASE.md).
- Install dependencies with `npm install` and `python -m pip install -e "./python[test]"`.
- Verify the baseline with `npm run check` and `pytest python/tests`.

## Branching and commits

- Work on a feature branch.
- Keep commits focused and descriptive.
- Prefer one logical change per commit.
- Do not rewrite or remove user changes unless the user asks you to.

Recommended commit style:

- `docs: ...`
- `fix: ...`
- `feat: ...`
- `refactor: ...`
- `test: ...`

## Code expectations

- Keep TypeScript strict and explicit.
- Preserve the current plugin architecture and Python backend separation.
- Avoid adding dependencies unless they clearly reduce complexity or unblock a feature.
- Keep filesystem and process operations bounded and logged.
- Prefer small, composable modules over broad utility files.

## Documentation expectations

- Update docs whenever behavior changes.
- Keep `README.md`, `docs/INDEX.md`, `CHANGELOG.md`, and `docs/ROADMAP.md` consistent.
- If a feature moves from planned to implemented, reflect that in both docs and code comments where relevant.

## Testing expectations

- Run the TypeScript check after relevant TypeScript edits.
- Run Python tests after backend changes.
- Add or update tests for bug fixes and behavior changes.
- If a check fails, fix the code or document the limitation explicitly before merging.

## Release checklist

- Ensure the working tree is clean.
- Update `CHANGELOG.md`.
- Confirm version numbers in `package.json` and `python/pyproject.toml`.
- Run the verification commands from `README.md`.
- Tag the release according to `RELEASE.md`.

## Pull request checklist

- Describe what changed and why.
- Mention any compatibility or migration impact.
- Call out documentation updates.
- Include verification results.
