# Release and Versioning for the Archive

The live Gnosys plugin/backend implementation has been removed from `main`. This branch now acts as a documentation archive.

## Current policy

- There is no active software release process for this branch.
- Repository updates should be treated as archive revisions.
- If code is ever reintroduced, restore semantic versioning for the runtime and backend.

## Archive revision checklist

1. Update the docs that changed.
2. Update `CHANGELOG.md`.
3. Keep `README.md` and `docs/INDEX.md` aligned.
4. Confirm the repository still contains only archive material.
5. Commit and push the revision.

## Future note

- If the repository becomes runnable again, replace this archive policy with a standard release policy and version the runtime/backends together.
