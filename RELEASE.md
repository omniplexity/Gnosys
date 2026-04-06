# Release and Versioning

Gnosys uses semantic versioning across the repository.

## Versioning rules

- Keep `package.json` and `python/pyproject.toml` on the same release version.
- Use `major.minor.patch`.
- Increment `patch` for fixes and documentation-only changes.
- Increment `minor` for new capabilities or notable workflow changes.
- Increment `major` for architectural or compatibility breaks.

## Release stages

### Patch release

- documentation updates
- small bug fixes
- test or build reliability improvements

### Minor release

- new tools or backend endpoints
- new workflows or runtime capabilities
- meaningful docs updates that describe new behavior

### Major release

- breaking config changes
- backend or plugin contract changes
- architectural shifts

## Release checklist

1. Confirm the branch is up to date with `origin/main`.
2. Run `npm run check`.
3. Run `pytest python/tests`.
4. Update `CHANGELOG.md`.
5. Update docs that describe behavior or version numbers.
6. Commit the release change.
7. Create a tag that matches the release version.
8. Push the commit and tag.

## Changelog policy

- Record user-visible changes in `CHANGELOG.md`.
- Keep the `Unreleased` section current during active work.
- Include the date when cutting a release entry.

## Current baseline

- Repository package version: `1.0.0`
- Python backend version: `1.0.0`
- Current main branch should always reflect the latest validated state.
