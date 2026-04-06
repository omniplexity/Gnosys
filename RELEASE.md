# Release and Versioning

Gnosys uses a simple foundation-first release policy while the scaffold is being built.

## Versioning

- Keep the root workspace, desktop app, shared package, and backend package aligned on the same scaffold version unless a subpackage is intentionally split.
- Use semantic versioning once real feature delivery starts.
- For now, `0.1.0` represents the initial scaffold.

## Release checklist

1. Run `npm run check`.
2. Run `npm run build`.
3. Run `python -m pytest apps/backend/tests -q`.
4. Update `CHANGELOG.md`.
5. Update docs if the structure changes.
6. Commit and push the scaffold revision.

## Release notes

- Add a changelog entry for every meaningful scaffold change.
- Keep package manifests and docs consistent.
- Once features land, use tags and release notes for user-visible milestones.
