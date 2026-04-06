# Gnosys Milestone Roadmap

## Scope

This roadmap tracks the plugin/backend repository, not a desktop UI shell. The goal is to keep the OpenClaw integration stable, observable, and easy to extend.

## Current baseline

- TypeScript plugin wrapper: implemented
- Python backend: implemented
- Memory, context, learning, skills, scheduler, monitoring: implemented
- Documentation and repository hygiene: being tightened

## Milestone 1.0.1 - Repository hygiene

Goal:

- finish contributor, release, changelog, and repo overview docs
- keep package and backend version numbers aligned
- ensure the docs map points to the current repository structure

Exit criteria:

- contributor guide exists
- release guide exists
- changelog exists
- roadmap is concise and current

## Milestone 1.0.2 - Verification reliability

Goal:

- keep `npm run check` and `pytest python/tests` working in a clean checkout
- make setup steps explicit in the README
- document common environment requirements

Exit criteria:

- TypeScript check passes after install
- Python tests pass
- setup and verification steps are easy to follow

## Milestone 1.1.0 - Runtime hardening

Goal:

- reduce sharp edges in backend spawn and health-check behavior
- improve error reporting and operator guidance
- keep bridge/client failure modes explicit

Exit criteria:

- error handling is typed and logged clearly
- backend startup failures are actionable
- health checks produce useful diagnostics

## Milestone 1.2.0 - Observability polish

Goal:

- make memory, context, and tool traces easier to inspect
- improve command output and structured status reporting
- tighten the documentation around troubleshooting and diagnostics

Exit criteria:

- status reporting is stable
- docs describe how to diagnose common failures
- observability remains part of the public surface

## Milestone 1.3.0 - Workflow expansion

Goal:

- extend scheduling, learning, and skill-management workflows
- keep the plugin/backend contract stable while adding capability
- add tests for the new flows as they land

Exit criteria:

- new workflows are documented
- tests cover the new behavior
- versioning and changelog entries are updated

## Milestone 2.0.0 - Major platform shift

Goal:

- only when the repository needs a breaking architectural change
- treat this as a separate planning point, not a near-term target

Exit criteria:

- major release decision is justified by actual API or architecture breaks
- migration path is documented
- changelog and release notes capture the break
