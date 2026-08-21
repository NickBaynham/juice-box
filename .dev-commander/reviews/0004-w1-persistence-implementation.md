# Review 0004: W1 persistence implementation

Scope: commits `39b0d62..8b2cca3`, twenty commits, the whole of workstream
W1 as delivered by plan 0002.

Verdict: approve. Nine increments, each reviewed against its own brief as
it landed, then the workstream reviewed as a whole. Every blocker and
major found during those reviews was repaired before this record was
written; the repairs are named per finding below. The remaining items are
minors carried into W2 and W3.

## Method

Reviews here are verification-based rather than reading-based, and that
distinction earned its cost repeatedly in this workstream. Reviewers built
the next increment's world in throwaway projects, reproduced claimed
failures independently, mutation-tested assertions, and in three cases
proved a shipped test could not fail. Findings below cite what was run.

## Correctness

No blocker or major findings outstanding.

**Repaired, was a spec failure.** The increment 8 implementer reported all
three of its ordering tests discriminating, verified five runs each. Two
did. `IterationRepository.list_for_run` filters on `run_id`, the leading
column of the `(run_id, iteration)` unique index, so PostgreSQL returns
index-order rows with no sort node and the assertion held whether or not
the query ordered anything. Its proof block queried the table directly
rather than calling the method, so it guarded nothing. Repaired in
`298c798`: the test now calls `list_for_run` again with index scans
disabled inside its own transaction, and fails five runs out of five when
the `ORDER BY` is deleted.

**Repaired, was a major.** `AgentRepository.list` ordered by `created_at`
with no tiebreaker. `now()` is transaction-scoped, so agents created in one
transaction share a timestamp and their relative order is arbitrary;
`limit`/`offset` paging over an unstable sort skips and repeats rows.
Nothing creates agents that way today, which is why no test caught it, but
W3's list endpoint pages over this table. Repaired in `2ba867c` with `id`
as a secondary key and a test that creates three agents in one transaction.

**Repaired, was a major.** The query-locality test matched any call whose
final identifier was `select`. An aliased sqlalchemy import escaped it,
while a `selectors` object and a local helper of the same name were
flagged, and its docstring claimed the reverse. It also matched only
`session.execute`, one call site out of thirteen in the repository layer.
Repaired in `8b2cca3`: `select` now resolves against each module's imports,
and the session methods the layer actually uses are matched.

**Repaired, was a major.** `migrations/env.py` passed the database URL
through configparser interpolation, so a percent-encoded password raised
before the driver saw it. Repaired in `edc975e`.

Every other claim in the plan's increments is backed by a passing test.
The schema was verified against `information_schema` rather than against
intent: all timestamp columns are `timestamp with time zone`, `cost_usd` is
`numeric(12,6)` round-tripping as `Decimal`, every CHECK constraint rejects
an invalid value, no native enum type exists, and all twelve foreign keys
carry the cascade behaviour documented.

## Simplicity

No findings. Six repository classes of static methods, no base class, no
generic CRUD helper. The one arithmetic expression in the layer,
`create_attempt`'s next-attempt computation, records its read-then-write
race in its own docstring rather than defending against a concurrency the
MVP does not have.

## DRY

No findings. `status_check()` and the `Annotated` column aliases are reused
across all seven models. The status lists duplicated between the lowercase
migration and `models.py` are correct as duplication: a migration is a
frozen historical record and must not import live model code.

## Size

One minor. `repositories.py` is 293 lines and six classes. Coherent today;
worth splitting per aggregate if W3 grows it. Recorded in
`docs/persistence.md`.

## Clarity

No findings. No emojis. Docstrings are one to three lines and carry the
reasoning that would otherwise be lost — why `NullPool`, why `seq` exists,
why `started_at` has no default, why the attempt race is recorded rather
than fixed.

## Tests

No findings outstanding, after the repairs above. This deserves its own
note, because it was the workstream's recurring defect.

Six tests passed for the wrong reason before being caught, each by a
different mechanism: PostgreSQL returning timestamp-tied rows in insertion
order by coincidence; an index whose key began with the filtered column
returning sorted rows with no sort step; a discrimination proof that only
held with `enable_indexscan=off`, which CI never uses; a proof block that
queried the table instead of calling the method under test; `seq`
auto-assignment asserted nowhere because every test set it by hand; and
data migrations exercised by nothing because every table is empty during a
normal run.

Two rules now sit in the plan's global constraints as a result. An ordering
test must filter on a column the ordering index does not cover, and must be
proven by deleting its `ORDER BY` and watching it fail under default
planner settings. When the method's contract fixes the filter column and an
index covers it, the committed test must disable index scans itself —
doing that only in a throwaway proof leaves the shipped test unable to fail.

## Minor findings carried into W2 and W3

1. `task` has no index on `run_id`, so `TaskRepository.list_for_run`
   sequential-scans. Correctness is unaffected.
2. `repositories.py` is six classes in one module.
3. `run.current_task_id` carries no foreign key, so a deleted task leaves
   it dangling. Documented; W3 or W9 should decide whether that is right.
4. `artifact` has no repository writer and `MessageRepository` cannot
   create. W9 and W10 own those writers.
5. The query-locality test cannot catch a query issued through a name only
   resolvable at runtime. Stated in its docstring.
6. The `Dockerfile` copies `src` before installing the project, so a source
   edit invalidates the dependency layer. The two-stage form shipped in
   increment 3 fixed the ordering; the caching note stands.

## Documents needing amendment

Carried from review 0003 and still outstanding. None block W1.

- ADR-0001 states CI must provide a PostgreSQL service container. CI runs
  `make test`, which brings it up through Compose.
- Design 0002 workstream criterion 2 requires an acceptance suite that does
  not exist until W12, and contradicts criterion 3. Plan 0002 records an
  exemption; the exemption should live in the design instead.
- Design 0002 increment criterion 7 requires one commit per increment. It
  penalised a self-review correction found after committing three times in
  this workstream.
- ADR-0002's durability list includes every state transition. The schema
  stores current status only, with no transition history. W3 owns the state
  machine and should decide deliberately.
