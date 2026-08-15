# Design 0002: Definition of done

## Goal

Define one definition of done at the increment, workstream, and phase
level so every plan can reference it instead of restating it.

## Context

Plan 0001 was written test-first with workstream exit criteria, but it
carried no explicit obligation to update documentation as behavior
changed, no feature list, and no analysis step. CLAUDE.md requires a
change log, a feature list, and a to-do list to be maintained, and
requires a second pass that statically checks validity, complexity, and
readability. Without a written definition those obligations get skipped
under delivery pressure and are noticed only at review.

This document is normative. Every plan under `.dev-commander/plans/`
states "Definition of done: design 0002" in its Global Constraints and
adds only workstream-specific criteria on top.

## Approach

Three nested gates. An increment is the unit of commit, a workstream is
the unit of plan, and a phase is the unit of release.

### Increment done

An increment is done when all seven hold. Every increment in every plan
inherits these; plans do not restate them.

1. **Test first.** A test naming the intended behavior was written and
   observed failing before the implementation existed. Observed failing
   means the failure was seen, not assumed.
2. **Implementation is minimal.** Enough to pass the test and no more.
   No speculative interfaces, no defensive branches for conditions that
   cannot occur, no exception handling without a caller that recovers.
3. **Suite green.** `make lint test` passes. If the increment touched
   anything requiring services, its integration tests pass too.
4. **Documented at the level it changed.** Public functions and classes
   carry a docstring saying what they do and what they return. Behavior
   visible to a caller — an endpoint, a CLI command, a configuration key,
   a schema field — is reflected in `README.md` or the relevant file
   under `docs/`, in the same commit. A user-visible change adds a
   `CHANGELOG.md` entry under Unreleased. A completed capability moves
   from `TODO.md` to `FEATURES.md`.
5. **Analysed.** Before committing, re-read the diff as a reviewer would
   and check four things: the code does what the test claims; nothing is
   duplicated that should be factored out; no function or module has
   grown past one clear purpose; names read the way the surrounding code
   reads. Act on what this finds in the same increment.
6. **No placeholders.** No `TODO` comments, commented-out code, stubbed
   returns, or `pass` bodies left behind.
7. **Committed.** One commit, message as named in the plan, working tree
   clean afterwards.

### Workstream done

A workstream is done when every increment is done and all of the
following hold.

1. The plan's own exit criteria pass.
2. The full suite passes including integration and acceptance tests:
   `make lint test && pdm run pytest -m integration && pdm run pytest tests/acceptance`.
3. Every Test Commander acceptance scenario traced to this workstream
   passes, and `.test-commander/traceability/requirements-map.md` shows
   no requirement traced to this workstream left uncovered. Per ADR-0008,
   these run at the workstream boundary, never per increment.
4. A code review is recorded under `.dev-commander/reviews/` via
   `/dc:review`, and every finding is either fixed or answered in
   writing.
5. The interfaces the workstream owns, as listed in design 0001, are
   documented under `docs/` with their names, types, and one usage
   example each. Consumers must not need to read the implementation.
6. `CHANGELOG.md`, `FEATURES.md`, and `TODO.md` reflect the workstream's
   result.
7. A journal entry is written with `/dc:journal` recording what was
   built, what was learned, and any decision that deviated from the plan.
8. Every checkbox in the plan file is ticked.

### Phase done

A phase is done when every workstream in it is done and all of the
following hold.

1. The phase's acceptance criteria pass. For Phase 1 that is the spec
   section 25 scenario, automated in W12.
2. CI is green on the branch, including the dependency and secret scans.
3. A security scan is recorded via `/dc:scan` under
   `.dev-commander/security/`, and every finding is fixed or accepted in
   writing.
4. `README.md` describes the system as it now behaves and remains under
   400 lines, linking out rather than growing.
5. Any decision taken during the phase that changed the specification is
   recorded as an ADR and reflected in the spec's section 31 table.
6. Lessons are captured with `/dc:learn`.

## Alternatives considered

**Restate the criteria in every plan.** Rejected: it duplicates a dozen
lines across thirteen files and guarantees drift.

**Rely on the dc-plan increment rubric alone.** Rejected: that rubric
covers small, independent, test-first, and committed, but says nothing
about documentation or analysis, which is exactly the gap found.

**A pull-request checklist instead of a design doc.** Rejected for the
MVP: there is no pull-request flow until Phase 2, and the criteria must
bind now.

## Interfaces

Documentation artifacts this document obliges every plan to maintain:

- `README.md` — what the system is and how to run it, under 400 lines.
- `CHANGELOG.md` — user-visible changes, newest first, Unreleased at top.
- `FEATURES.md` — capabilities that exist and work today.
- `TODO.md` — capabilities not yet built or under construction.
- `docs/` — interface documentation, one file per owned interface.

## Risks

- **Ceremony outweighing delivery on small increments.** Mitigated by
  scoping criterion 4 to the level that actually changed: most increments
  need a docstring and nothing else.
- **The analysis pass degrading into a rubber stamp.** Mitigated by
  naming four specific checks rather than asking for a general review.
- **FEATURES.md drifting into a duplicate of the spec.** It lists what
  works today; the spec describes what is intended. A capability appears
  in FEATURES.md only when its tests pass.
