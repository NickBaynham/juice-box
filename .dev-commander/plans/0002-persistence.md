# Plan 0002: W1 Persistence

## Goal

Persist every Juice Box entity in PostgreSQL through async SQLAlchemy
with Alembic migrations, so state survives process death as ADR-0002
requires.

## Architecture

One async engine and session factory built from settings. Declarative
models and `Base` together in `persistence/models.py`, one migration per
model increment, and async repository functions that own every query. No
other layer issues SQL or holds a session.

## Tech Stack

Plan 0001's stack plus SQLAlchemy 2.x with asyncio, asyncpg, Alembic.

## Global Constraints

- Definition of done: design 0002, with one exemption recorded below.
- Consumes ADR-0001 (PostgreSQL from the first increment), ADR-0002
  (durable state), ADR-0006 (agent id is the handle, runs are attempts).
- Every table has `created_at`. Mutable tables also have `updated_at`.
  Every timestamp column is
  `mapped_column(DateTime(timezone=True), server_default=func.now())`, and
  `updated_at` adds `onupdate=func.now()`. A bare `Mapped[datetime]`
  produces `TIMESTAMP WITHOUT TIME ZONE` and silently violates this.
- Primary keys are `uuid4` UUID columns. Structured columns are `JSONB`.
- Status and type columns are `String` with a Python enum supplying the
  values and a `CHECK` constraint, not PostgreSQL native enum types.
  Native enums survive `DROP TABLE`, so `downgrade base` followed by
  `upgrade head` fails with `DuplicateObjectError`, which on a persistent
  `db-data` volume poisons the developer's database until they drop the
  type by hand. Proven during the pre-flight scan of this plan.
- Every entity table carries both `agent_id` and `run_id`, per ADR-0006,
  so run-scoped endpoints can be added later without a migration.
- Model tests are integration tests and run against Compose PostgreSQL.
  Every increment also adds unit tests for what does not need a database,
  so `make test` keeps covering this workstream's work.
- `now()` is transaction-scoped in PostgreSQL. Rows inserted in one
  transaction share an identical `created_at`, so any test asserting
  ordering must either commit separately or order by a monotonic column.
- Requires W0 complete.
- Exemption: design 0002's workstream criterion 2 runs
  `pdm run pytest tests/acceptance`, which exits 4 because that directory
  does not exist until W12, and contradicts criterion 3, which correctly
  traces no requirement to W1. Close-out verifies
  `make lint test && pdm run pytest -m integration` instead. Review 0003
  records the amendment design 0002 needs.

## Increments

### 1. Async engine, session factory, and the integration test harness

- [x] Open and close async sessions against the configured database, and
      give every later increment an isolated database to test against.

Files: `src/juicebox/persistence/__init__.py`,
`src/juicebox/persistence/database.py`,
`tests/integration/conftest.py`, `tests/integration/test_database.py`,
`tests/unit/test_session_scope.py`, `Makefile`

Failing test first: `session_scope()` yields a session where
`await session.scalar(text("SELECT 1"))` returns 1; a second test creates
a temporary table inside the context manager, raises, and asserts both
that the exception propagates and that the row is gone. A unit test
asserts `session_scope` rolls back and re-raises against a stub session,
with no database involved.

Minimal implementation: `create_async_engine(settings.database_url,
poolclass=NullPool)`, an `async_sessionmaker` with
`expire_on_commit=False`, and an `asynccontextmanager` `session_scope()`
that commits on clean exit and rolls back on exception. Move
`asyncpg>=0.30` to project dependencies and add
`sqlalchemy[asyncio]>=2.0`.

`NullPool` is required, not a preference. `asyncio_mode = "auto"` gives
each test its own event loop, and a pooled asyncpg connection cached on
one loop fails on the next test with `RuntimeError: Event loop is
closed`. Proven during the pre-flight scan; `pool_pre_ping` makes the
failure look like a network fault. Revisit pooling when the API is
serving real traffic, not before.

`tests/integration/conftest.py` provides a session-scoped autouse fixture
that brings the database to `head`, and a function-scoped autouse fixture
that truncates every table in `Base.metadata` with
`TRUNCATE ... RESTART IDENTITY CASCADE` before each test. Truncation
rather than an enclosing transaction, because the repository layer
commits through `session_scope` and would escape it. Without this the
suite is green on the first run and red on the second, because `db-data`
is a persistent volume: leftover rows break the message, event, and
`list` offset assertions in later increments.

Add a `test-integration` Make target that runs
`docker compose up -d --wait db` before `pdm run pytest -m integration`.
Every Verify line below assumes it; a bare pytest invocation does not
start the database.

Verify: `make lint test && make test-integration`

Commit: `Add async engine, session factory, and integration test harness`

### 2. Alembic and the first schema

- [x] Manage the schema with Alembic and store agents and their run
      attempts.

Files: `alembic.ini`, `migrations/env.py`, `migrations/script.py.mako`,
`migrations/versions/<hash>_add_agent_and_run.py`,
`src/juicebox/persistence/models.py`,
`tests/integration/test_migrations.py`,
`tests/integration/test_models_agent.py`,
`tests/unit/test_model_enums.py`

This increment merges what were separate Alembic and first-model
increments. They cannot be split along that line: an Alembic increment
with no revision cannot assert anything about `alembic_version`, which
holds zero rows until a revision exists, and a model increment cannot
autogenerate a migration until env.py imports the models. Proven during
the pre-flight scan, where the literal sequence produced an empty
migration and a green run that proved nothing.

Failing test first: `alembic upgrade head` exits 0 and `alembic_version`
holds exactly one row; `alembic downgrade base` leaves no application
tables in `information_schema.tables`, excluding `alembic_version`, which
always remains; `alembic upgrade head` then succeeds a second time. That
final re-upgrade is the assertion that catches the native-enum trap, and
the fixture must leave the database at `head` in a `finally`, because
every later test file needs the schema. Then: insert an `Agent` with a
definition and objective as dicts, read it back in a new session, and
assert the JSON round-trips and `status` defaults to `CREATED`; insert
two `Run` rows with the same `(agent_id, attempt)` and assert
`IntegrityError`, rolling the session back afterwards since a session is
unusable following one. A unit test asserts each enum's member set
equals the spec's list exactly, with no database.

Minimal implementation: `pdm add alembic`, then `alembic init -t async
migrations`. In `migrations/env.py`, take the URL from
`Settings().database_url` rather than `alembic.ini`, set
`target_metadata = Base.metadata`, and import the models module. That
import is what populates the metadata; without it `--autogenerate` emits
an empty `upgrade()` and exits 0. `Base` lives in `models.py` alongside
the models so there is one module to import. Leave `sqlalchemy.url` empty
in `alembic.ini` so the database URL is never committed.

Delete the two guards in `tests/integration/conftest.py` that increment 1
needed while no schema existed, and hoist their imports to module level.
Once migrations and models land, both branches are permanently dead, which
the definition of done forbids. Keep `script_location` in the `%(here)s`
form Alembic generates; a bare relative path resolves against pytest's
working directory instead of the ini file.

Add the tripwire the harness otherwise lacks: assert
`Base.metadata.sorted_tables` is non-empty. A truncation fixture that
silently stops firing leaves every later increment testing against dirty
data with nothing going red, and the first assertions that would notice
are the ordering and offset tests three increments later. The migration
test's `alembic_version` assertion covers the other fixture.

Edit `migrations/script.py.mako` before generating any revision: replace
`from typing import Sequence, Union` with
`from collections.abc import Sequence`, and `Union[str, Sequence[str],
None]` with `str | Sequence[str] | None`. Alembic's stock template fails
`make lint` on `UP007`, `UP035`, and `I001`, so every generated revision
would otherwise be uncommittable under the definition of done. Fix
`env.py`'s import order for the same reason.

`AgentStatus` holds the eight section 6 states. `RunStatus` holds the
subset a run can occupy: a run is never `CREATED`, since it is created by
`start`. `Agent` with `id`, `name`, `definition`, `objective`,
`repository_url`, `base_branch`, `work_branch`, `status`,
`failure_reason`, `created_at`, `updated_at`, `started_at`,
`finished_at`. `Run` with `id`, `agent_id` foreign key with
`ondelete="CASCADE"`, `attempt`, `status`, `iteration_count`,
`current_task_id`, `checkpoint` as `JSONB`, `failure_reason`,
`started_at`, `finished_at`, `created_at`, `updated_at`, and a unique
constraint on `(agent_id, attempt)`. `checkpoint` is required by spec
section 12, which ADR-0002 keeps in force for the MVP in full; only the
resume behaviour is deferred to Phase 2.

Generate the migration with `alembic revision --autogenerate`, then read
it before committing.

Verify: `make lint test && make test-integration`

Commit: `Wire Alembic and add agent and run models`

### 3. Migrations in the container image

- [ ] Ship an image that can apply its own migrations.

Files: `Dockerfile`, `docker-compose.yml`, `Makefile`,
`tests/integration/test_container_migrations.py`

Failing test first: build the image, run `alembic upgrade head` inside a
container against the Compose database, and assert it exits 0 and creates
the tables.

Minimal implementation: the Dockerfile copies `alembic.ini` and
`migrations/` alongside `src/`, and adopts the two-stage install review
0003 carried into this workstream: copy `pyproject.toml` and `pdm.lock`,
run `pdm install --prod --no-self`, copy the source and migrations, then
run `pdm install --prod --no-editable`. Dependencies stop being
reinstalled on every source edit, which starts to matter now that
SQLAlchemy and Alembic are in the set. Add a `migrate` Make target.
Alembic therefore belongs in project dependencies, not the dev group.

This increment sits here rather than at close-out so the following four
increments do not accumulate an image that has been broken since the
schema landed.

Verify: `make lint test && make test-integration`

Commit: `Ship migrations in the container image`

### 4. Task model

- [ ] Store the task graph an agent decomposes its objective into.

Files: `src/juicebox/persistence/models.py`,
`migrations/versions/<hash>_add_task.py`,
`tests/integration/test_models_task.py`, `tests/unit/test_model_enums.py`

Failing test first: insert a `Task` with two dependency ids, read it back
and assert the list survives; assert `status` defaults to `PENDING` and
`attempts` to 0; assert deleting the parent agent deletes the task. A
unit test asserts the `TaskStatus` and `TaskPriority` member sets.

Minimal implementation: `TaskStatus` with the eight section 11 states and
`TaskPriority` of low, medium, high. `Task` with `id`, `agent_id`,
`run_id`, `title`, `status`, `priority`, `dependencies` as `JSONB`,
`attempts`, `result`, `error`, `created_at`, `updated_at`, `started_at`,
`finished_at`, both foreign keys cascading. The task timestamps are what
W10's report needs for per-task duration.

Verify: `make lint test && make test-integration`

Commit: `Add task model`

### 5. Message and Event models

- [ ] Store messages sent to a running agent and events it emits.

Files: `src/juicebox/persistence/models.py`,
`migrations/versions/<hash>_add_message_and_event.py`,
`tests/integration/test_models_messaging.py`,
`tests/unit/test_model_enums.py`

Failing test first: insert three `Message` rows, assert a query for
unconsumed messages returns them oldest first and excludes one whose
`consumed_at` is set. Insert `Event` rows and assert they are returned in
insertion order for a given agent. Both orderings use the `seq` column,
not `created_at`: rows written in one transaction share an identical
`now()`, so ordering by `created_at` is arbitrary. A unit test asserts
the `MessageType` member set and, specifically, that the values are the
spec's wire forms.

Minimal implementation: `MessageType` with the seven section 7 types.
Three of them contain hyphens and are not valid Python identifiers, so
members are named `PRIORITY_CHANGE`, `CANCEL_TASK`, `NEW_TASK` with
values `"priority-change"`, `"cancel-task"`, `"new-task"`. The value is
the wire form and is what W4's API accepts; the unit test exists so this
does not silently diverge. `Message` with `id`, `seq` as `BIGSERIAL`,
`agent_id`, `run_id`, `type`, `body`, `created_at`, `updated_at`,
`consumed_at`. `Event` with `id`, `seq`, `agent_id`, `run_id`, `name`,
`payload` as `JSONB`, `created_at`, and an index on
`(agent_id, seq)`. The `seq` column is also the cursor W4 and W10 need.

Verify: `make lint test && make test-integration`

Commit: `Add message and event models`

### 6. Artifact and IterationRecord models

- [ ] Store run outputs and the per-iteration execution history.

Files: `src/juicebox/persistence/models.py`,
`migrations/versions/<hash>_add_artifact_and_iteration.py`,
`tests/integration/test_models_execution.py`

Failing test first: insert two `IterationRecord` rows with the same
`(run_id, iteration)` and assert `IntegrityError`; insert records out of
order and assert a run-scoped query returns them ordered by `iteration`.
Insert an `Artifact` and assert it round-trips.

Minimal implementation: `Artifact` with `id`, `agent_id`, `run_id`,
`kind`, `name`, `path`, `content_type`, `size_bytes`, `created_at`.
`IterationRecord` with `id`, `agent_id`, `run_id`, `iteration`,
`task_id`, `action`, `command`, `result`, `next_action`, `model`,
`input_tokens`, `output_tokens`, `cost_usd`, `created_at`, and a unique
constraint on `(run_id, iteration)`. `agent_id` is required by ADR-0006
like every other entity table. `model` and `cost_usd` are what section
18's minimum metrics require; token counts alone cannot produce an
estimated cost.

Verify: `make lint test && make test-integration`

Commit: `Add artifact and iteration record models`

### 7. Agent and run repositories

- [ ] Provide the accessors carrying the ADR-0006 attempt logic.

Files: `src/juicebox/persistence/repositories.py`,
`tests/integration/test_repositories_agent.py`

Failing test first: `AgentRepository.create` returns an agent with an id;
`get` returns it and returns `None` for an unknown id; `list` returns
newest first and honours limit and offset; `set_status` persists the new
status and advances `updated_at`, which requires separate `session_scope`
blocks since `now()` is transaction-scoped and both writes would
otherwise share a timestamp; `delete` removes the agent and cascades to
its runs and tasks. `RunRepository.create_attempt` computes the next
attempt number and `get_current` returns the latest.

Minimal implementation: `AgentRepository` with `create`, `get`, `list`,
`delete`, and `set_status`; `RunRepository` with `create_attempt` and
`get_current`. Each takes an `AsyncSession`; none opens its own.
`create_attempt` reads then writes, which races under concurrent
starters. The MVP has one orchestrator and the unique constraint fails
loudly rather than corrupting, so this is recorded, not fixed.

Verify: `make lint test && make test-integration`

Commit: `Add agent and run repositories`

### 8. Remaining repositories

- [ ] Provide the accessors for tasks, messages, events, and iterations.

Files: `src/juicebox/persistence/repositories.py`,
`tests/integration/test_repositories.py`

Failing test first: `MessageRepository.list_unconsumed` returns oldest
first by `seq` and `mark_consumed` sets `consumed_at`;
`EventRepository.list_for_agent` returns events in `seq` order;
`IterationRepository.list_for_run` returns records ordered by
`iteration`; `TaskRepository` round-trips a task and lists by run.

Minimal implementation: `TaskRepository`, `MessageRepository` with
`list_unconsumed` and `mark_consumed`, `EventRepository` with `append`
and `list_for_agent`, and `IterationRepository` with `append` and
`list_for_run`. These are mechanical, which is why they are split from
increment 7.

Verify: `make lint test && make test-integration`

Commit: `Add task, message, event, and iteration repositories`

### 9. Workstream close-out

- [ ] Document the persistence layer and close out W1.

Files: `docs/persistence.md`, `README.md`, `CHANGELOG.md`, `FEATURES.md`,
`TODO.md`, `tests/unit/test_query_locality.py`

Failing test first: a unit test asserting no module under `src/juicebox`
outside `persistence/` contains `select(` or `session.execute`. This is
the executable form of the exit criterion below, which nothing otherwise
enforces, and it will catch W2 through W4 regressions rather than only
this workstream's.

Minimal implementation: `docs/persistence.md` with an entity list, the
status enums and their legal values, the repository API with signatures,
how to create a migration, and a note that adding a `relationship()`
later requires `passive_deletes=True` so the database keeps performing
the cascades these tests assert. Update the tracking documents. Run
`/dc:review` and `/dc:journal` in the controller session; they are not
available to an implementer.

Verify: `make lint test && make test-integration`

Commit: `Document the persistence layer and close out W1`

## Exit Criteria

Design 0002's workstream criteria, less the acceptance-test criterion
exempted above, plus: migrations apply to an empty database, roll back
cleanly, and apply again; every model round-trips through a session; the
repository layer is the only module issuing queries, enforced by the
increment 9 test.

## Corrections to this plan

Recorded after a pre-flight scan and before implementation. Plan 0001
went the other way, and each of its four errors cost a round trip to
discover. Five of the following were proven by execution in a throwaway
project rather than by reading.

1. Increments 2 and 3 were mutually dependent and have been merged.
   Alembic with no revision leaves `alembic_version` holding zero rows,
   so the original increment 2's central assertion could not pass; and
   `--autogenerate` with no model import emits an empty `upgrade()` and
   exits 0, so the original increment 3 would have committed a no-op
   migration and failed at the first insert.
2. `Base` moved from `database.py` to `models.py`, and env.py must import
   that module. The two-file arrangement was the mechanism of the
   autogenerate failure above.
3. Native PostgreSQL enum types survive `DROP TABLE`, so the mandated
   `downgrade base` then `upgrade head` cycle failed with
   `DuplicateObjectError: type "agentstatus" already exists`, permanently
   on a persistent volume. Status columns are now `String` with a `CHECK`
   constraint.
4. The migration test left the database at `base`, and pytest collects
   `test_migrations.py` before every model test file. The whole
   integration suite would have run against a dropped schema. The test
   now restores to `head` in a `finally`.
5. Nothing created the schema the model tests insert into, and nothing
   isolated them from each other. `tests/integration/conftest.py` now
   owns both, added in increment 1.
6. A module-level engine with the default pool fails on the second test
   in any file under `asyncio_mode = "auto"`, with `RuntimeError: Event
   loop is closed`. `NullPool` is now specified.
7. Alembic's stock `script.py.mako` fails this project's ruff on
   `UP007`, `UP035`, and `I001`, so no generated revision could be
   committed under the definition of done. The template is now edited
   first.
8. `IterationRecord` lacked `agent_id`, contradicting ADR-0006 verbatim
   and requiring exactly the migration that ADR exists to avoid.
9. `Run` and `Message` are mutable and lacked `updated_at`, contradicting
   this plan's own constraint.
10. `TIMESTAMPTZ`, required by the constraints, does not happen by
    default; a bare `Mapped[datetime]` yields a naive timestamp.
11. `updated_at` was asserted to advance with nothing specifying
    `onupdate`, and `now()` is transaction-scoped, so a same-transaction
    test would have compared identical timestamps.
12. Ordering assertions on `created_at` are non-deterministic within a
    transaction. Messages and events gained a `seq` column, which W4 and
    W10 need as a cursor regardless.
13. `checkpoint` from spec section 12 was persisted nowhere, though
    ADR-0002 keeps section 12 in force for the MVP in full. Added to
    `Run`, along with `current_task_id`, which ADR-0006's `current_run`
    payload implies.
14. Three `MessageType` values contain hyphens and are not valid Python
    identifiers. Member naming is now specified so the wire form cannot
    silently diverge from the spec.
15. Section 18's minimum metrics require estimated cost and the model
    used; `IterationRecord` recorded token counts only.
16. Nothing put `alembic.ini` or `migrations/` into the container image,
    so the shipped image could not apply its own schema. New increment 3
    owns that, along with the two-stage Dockerfile install review 0003
    carried into this workstream and which no increment owned.
17. Every increment's Verify ran pytest without starting the database.
    A `test-integration` Make target now does.
18. Every test in the workstream was an integration test, so `make test`
    would have covered none of it. Each increment now carries unit tests
    for what needs no database.
19. The exit criterion "the repository layer is the only module issuing
    queries" was enforced by nothing. Increment 9 now tests it.
20. Increment 7 was six repository classes and roughly seventeen methods
    in one commit. Split into increments 7 and 8.
21. `AgentStatus` and `RunStatus` were both "the eight section 6 states",
    duplicating a type for a run that can never be `CREATED`.
22. Design 0002's workstream criterion 2 is unsatisfiable until W12; the
    exemption is now recorded in the constraints rather than discovered
    at close-out.

## Documents still needing amendment

These are design decisions rather than plan defects, and are recorded
rather than changed here. Review 0003 raised the first two.

- ADR-0001's consequences state that CI must provide a PostgreSQL service
  container. CI runs `make test`, which brings PostgreSQL up through
  Compose. This plan cites ADR-0001 as a contract, so the ADR should say
  what shipped.
- Design 0002's workstream criterion 2 requires an acceptance suite that
  does not exist until W12, and contradicts criterion 3.
- ADR-0002's durability list includes every state transition. This plan
  stores current status only, with no transition history table. W3 owns
  the state machine and may want one; decide it there deliberately rather
  than by omission.
