# Project Metadata

Name: Juice Box
Description: Containerized orchestration platform for autonomous AI agents.
Initialized: 2026-08-14
Specification: docs/specs/juice-box-spec.md
Implementation workspace: .dev-commander/

## Role in this project

Per ADR-0008 in `.dev-commander/design/`, Test Commander owns the outer
quality loop and works from the specification, not the code:

- requirements inventory and review from the specification
- traceability from requirements to workstreams, plans, and tests
- API-level acceptance scenarios under `tests/acceptance/`
- a quality report per phase

Dev Commander plans own the inner loop: every implementation increment is
test-first with pytest at unit or integration level. No Test Commander
artifact gates an increment. Acceptance scenarios run at workstream
boundaries.

## Applicability limits

Juice Box is a headless HTTP service in the MVP; a web dashboard is a
Phase 2 item in specification section 26. Until it exists, the
exploratory and UI-driven commands have no target and are not used:
`/tc:create-charter`, `/tc:explore`, `/tc:session-summary`.

Commands in use for the MVP: `learn-from-specs`, `learn-from-code`,
`learn-from-api`, `review-requirements`, `requirements-coverage`,
`requirements-to-tests`, `test-ideas`, `generate-bdd`, `automation-plan`,
`automate`, `run`, `evidence`, `traceability`, `quality-report`.

## Automation

One runner. Acceptance tests are pytest driving the API over HTTP with
httpx, under `tests/acceptance/`. Gherkin files under
`.test-commander/bdd/features/` are specification artifacts referenced by
scenario name; there is no Cucumber or Behave runtime.

## Note on naming

Test Commander appears in this project in two unrelated roles. It is the
quality system used to build Juice Box, which is what this workspace
governs. It is also the name of the first agent Juice Box runs, in the
specification section 25 acceptance test. These are not the same thing.
