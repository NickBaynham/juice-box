# ADR-0008: Test Commander owns requirements traceability and acceptance
testing; dev-commander plans own unit and integration tests

## Status

Accepted — 2026-08-14. Establishes the boundary between the two test
systems now present in the project.

## Context

Test Commander is now initialized in this repository at
`.test-commander/`, and the intent is to use it for analysis, test
generation, test automation, and verification at each step. Dev Commander
plans already require a failing test before every increment.

Without a boundary the project ends up with two test suites that overlap,
two definitions of coverage, and increments that are blocked waiting for
a BDD artifact that adds nothing to a unit test. The reverse failure is
equally likely: acceptance criteria from the spec never get traced to
anything, because unit tests are written against the implementation
rather than against section 24 and section 25.

A complication: Test Commander's exploration commands drive Playwright
against a live web application. Juice Box has no user interface in the
MVP — spec section 26 puts a web dashboard in Phase 2. Much of Test
Commander's exploratory surface therefore has nothing to point at yet.

Note also that Test Commander appears in this project in two unrelated
roles: as the quality system used to build Juice Box, which is what this
record governs, and as the first agent Juice Box runs in the section 25
acceptance test. These must not be conflated.

## Decision

The two systems divide by altitude, not by overlap.

**Dev Commander plans own the inner loop.** Every increment in every plan
under `.dev-commander/plans/` is test-first with pytest, at unit or
integration level, testing the code the increment writes. This is
unchanged, and no Test Commander artifact gates an increment.

**Test Commander owns the outer loop.** It works from the specification
rather than the code, and produces:

- Requirements inventory and review, from `docs/specs/juice-box-spec.md`
  via `/tc:learn-from-specs` and `/tc:review-requirements`. Section 24's
  MVP list and section 25's twelve steps are the requirement set.
- Traceability from those requirements to the workstreams and plans that
  satisfy them, maintained in `.test-commander/traceability/`.
- API-level acceptance scenarios in Gherkin under `.test-commander/bdd/`,
  written against the section 21 HTTP surface, not against internals.
- A quality report per phase via `/tc:quality-report`.

**At the workstream boundary, both run.** A workstream is not done until
its plan's increments are green and the acceptance scenarios traced to it
pass. This is added to design 0002's workstream criteria.

**Applicability limits, stated rather than discovered.** Until a web
dashboard exists in Phase 2, `/tc:explore` and the charter-driven
exploratory commands have no target and are not used. The Test Commander
surface in use for the MVP is: `learn-from-specs`, `learn-from-code`,
`learn-from-api`, `review-requirements`, `requirements-coverage`,
`requirements-to-tests`, `test-ideas`, `generate-bdd`, `automation-plan`,
`automate`, `run`, `evidence`, `traceability`, and `quality-report`.

**One automation framework, not two.** Test Commander's generated
acceptance tests are pytest tests under `tests/acceptance/`, driving the
API over HTTP with httpx. No second runner, no Cucumber or Behave
runtime. The Gherkin files are specification artifacts that the pytest
acceptance tests reference by scenario name.

## Consequences

- Requirements from the spec are traceable to tests, which neither system
  achieved alone.
- Increments stay fast, because the outer loop runs at workstream
  boundaries rather than per commit.
- One test command still runs everything:
  `make lint test && pdm run pytest -m integration && pdm run pytest tests/acceptance`.
- Duplication is possible at the seam — an acceptance scenario may cover
  ground an integration test already covers. This is accepted; the
  acceptance test asserts the requirement, the integration test asserts
  the mechanism, and they fail for different reasons.
- Most of Test Commander's exploratory surface sits unused until Phase 2.
  That is a deliberate consequence of building a headless service first,
  not a gap.
