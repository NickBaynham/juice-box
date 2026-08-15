# Plan review 0001: 0001-foundation.md

Reviewed 2026-08-14 against the dc-plan increment rubric: small,
independent, test-first, committed, no placeholders.

## Verdict

Ready with repairs. Both findings are dispositioned below; the plan on
disk already reflects them.

## Findings

### 1. Increment 6 named no failing test — repaired

Rubric item violated: test-first.

The original increment 6 added `docker-compose.yml` and changed the
Makefile with the note "none applies; increment 7 is the executable
check." That deferred verification to a later increment, which also broke
independence: increment 6 could not be shown correct on its own.

Repair applied: increments 6 and 7 were merged. The Compose increment now
carries `tests/integration/test_database_connection.py` as its failing
test, so the service definition and the proof it works land together. The
plan now has seven increments.

### 2. Increment 7 (CI workflow) names no failing test — accepted

Rubric item violated: test-first.

A GitHub Actions workflow cannot be tested before it exists without
introducing a workflow linter or act, which is disproportionate for one
generated file. The executable check is the first green run on the
branch, which is named in the increment's verify step.

Accepted as written. This is the only increment in the plan without a
preceding test, and the exception is recorded here rather than left
implicit.

## Rubric items passing

- Small: every increment is one deliverable with one test cycle. The
  largest, increment 1, creates several files but is a single
  indivisible unit — the project does not exist until all of them do.
- Independent: increments 1 through 6 are each buildable and testable at
  the point they are written; increment 7 depends only on the Make
  targets from increment 1.
- Committed: all seven name a commit message.
- No placeholders: no "TBD" or contentless steps. Every increment names
  exact file paths, and every test is specified as code or as an explicit
  assertion sequence.

## Notes for implementation

- Increment 5's container test builds an image and will be slow. Keep it
  behind the `integration` marker so `make test` stays fast.
- Increment 4's entrypoint test asserts `factory is True`; if uvicorn's
  factory argument is renamed in a current release, fix the assertion to
  match the installed API rather than pinning an older uvicorn.
