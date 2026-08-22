# Changelog

All notable changes to this project are recorded here. The format follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/) and this project
adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Fixed

- Settings ignores unrelated keys in `.env` instead of refusing to start, so
  a shared `.env` can hold configuration for other tools.
- Unit tests are isolated from `JUICEBOX_` variables and from a developer's
  `.env` file, so the tests asserting defaults no longer depend on the
  environment they run in.

### Changed

- `AgentStatus` and `RunStatus` values are now lowercase (`"created"`,
  `"running"`, ...), matching `TaskStatus` and `TaskPriority`, so every
  entity stores status and type values the same way. Enum member names
  stay uppercase Python identifiers. Specification section 11 shows task
  status in a literal JSON payload example; section 6 renders the agent
  lifecycle only as an uppercase ASCII diagram that never appears in an
  API payload, so the lowercase reading is better evidenced. A hand-written
  migration (`a017971fe447`) drops and recreates the `ck_agent_status` and
  `ck_run_status` CHECK constraints and lowercases existing `agent` and
  `run` rows' `status` values; `downgrade()` reverses both steps.

### Added

- `juicebox.schemas` package: Pydantic models for the agent definition
  envelope of specification section 8, loaded from YAML.
  `load_agent_definition(document)` parses with `yaml.safe_load` and
  validates through `AgentDefinition`, whose `apiVersion`, `kind`,
  `metadata`, and `agent` fields all forbid unknown keys, so a typo such
  as `api_version:` is rejected rather than silently accepted.
  `Metadata.name` is constrained to `^[a-z0-9][a-z0-9-]*$`, the pattern W6
  will need to derive a work branch and container name from it. Opens
  workstream W2: declarative schemas.
- `AgentDefinition` gains top-level `skills` and `secrets` fields, siblings
  of `metadata:` and `agent:` per specification section 8 and section 17,
  each defaulting to an empty list. `AgentSpec.system_prompt` is stripped
  and rejected when empty or all whitespace. Each `secrets` entry is a
  `SecretName`, a name constrained to `^[a-z0-9][a-z0-9-]*$` reused from
  `Metadata.name`'s pattern; the constraint lives on the item type rather
  than a list-level validator so a rejected entry's error `loc` carries
  its index. The pattern checks that a secret is referenced by name, not
  that a name is credential-free — detecting leaked credentials is the
  gitleaks step CI already runs.
- `Runtime` and `Permissions`, the `runtime:` and `permissions:` blocks of
  specification section 8, wired onto `AgentDefinition` as `runtime:
  Runtime | None = None` and `permissions: Permissions = Permissions()`.
  `runtime.memory` and `runtime.timeout` are strings validated against
  `^(\d+)(Ki|Mi|Gi|Ti)$` and `^(\d+)(s|m|h)$`, converted to `memory_bytes`
  and `timeout_delta` through plain `@property`, not `@computed_field`, so
  neither appears in `model_dump()` and a dumped `Runtime` still
  re-validates under `extra="forbid"` — the round trip W3 needs when
  reading a definition back out of JSONB. `Permissions` defaults to least
  privilege (`filesystem: read-only`, `network: false`, `shell: false`) as
  a default *instance* rather than `None`, per ADR-0004: an omitted block
  must not grant more access than a present one, so `permissions` is never
  absent on a validated `AgentDefinition`. `FilesystemAccess` is a
  `StrEnum` with lowercase values (`read-only`, `read-write`) per
  ADR-0009.
- `Repository` and `Execution`, the `repository:` and `execution:` blocks
  of specification section 8, wired onto `AgentDefinition` as `repository:
  Repository | None = None` and `execution: Execution = Execution()` so
  `max_iterations` always has a value for W9 to enforce. `Repository.url`
  is constrained to `^https://` on the field itself, since W6 clones
  inside a container with no agent key and an SSH URL would only fail
  later, at clone time, with a less useful message.
  `ApprovalOperation` is a closed `StrEnum` of the six approval slugs
  `execution.require_approval_for` may name — `merge`,
  `production-deployment`, `secret-modification`, `force-push`,
  `cloud-resource-deletion`, `repository-data-deletion` — derived from
  section 16's prose examples plus section 8's own two, since ADR-0004
  requires an unknown operation be rejected and neither section on its own
  gives a closed set. Three members have no MVP enforcement point yet;
  increment 7 documents each against its enforcement point and
  workstream. With this block wired on, specification section 8's example
  now validates end to end.
- `juicebox.schemas.loading.load_objective(document)`, parsing a YAML
  string and validating it against `ObjectiveDocument`, the objective
  document envelope of specification section 9. Like `AgentDefinition`,
  the envelope is a Pydantic model rather than a subscript into the
  parsed mapping, so a document missing the `objective:` key, or one that
  is a top-level list or empty, raises `pydantic.ValidationError` with a
  `("objective", ...)` `loc` prefix instead of `KeyError` or `TypeError`.
  `Objective.id` reuses `agent.NAME_PATTERN`; `success_criteria` is
  required and non-empty, since W9 detects completion against it and an
  objective without any can never finish, while `tasks` stays optional
  because section 10 has the agent decompose the goal itself.
  `CompletionAction` rejects `pull_request` without `push`, and `push`
  without `commit`, since W10 pushes a branch it committed to. Section
  9's example now validates end to end.
- Persistence layer documentation (`docs/persistence.md`): the seven
  tables and their columns, the status and type enums and their lowercase
  legal values, every repository method's signature, how to create a
  migration, and why a later `relationship()` needs `passive_deletes=True`.
  Records two performance items found in increment 8, neither fixed here:
  `task` has no index on `run_id`, and `repositories.py` holds all six
  repository classes in one module. Closes out workstream W1: persistence.
- `tests/integration/test_migration_data_correctness.py`, proving the
  lowercase-status migration (`a017971fe447`) is data-correct and not
  merely schema-correct: it seeds uppercase `agent` and `run` rows through
  raw SQL at the prior revision, since the current models reject
  uppercase values, upgrades through the migration, and asserts the
  seeded rows were actually rewritten to lowercase. Every table is empty
  during a normal run, so the migration's `UPDATE` statements were
  otherwise exercised by nothing.
- `tests/unit/test_query_locality.py`, the executable form of the
  workstream's exit criterion that the repository layer is the only
  module issuing queries: an `ast`-based scan, not a text scan, asserting
  no module under `src/juicebox` outside `persistence/` calls `select(`
  or a `session.execute(...)`-shaped method.
- `AgentRepository` and `RunRepository` (`juicebox.persistence.repositories`),
  the first repositories in the persistence layer: `AgentRepository.create`,
  `get`, `list` (newest-created first, with `limit` and `offset`),
  `set_status`, and `delete` (cascading to the agent's runs and every
  run-scoped row); `RunRepository.create_attempt`, which numbers an agent's
  run attempts per ADR-0006, and `get_current`, which returns the latest
  attempt. Both are classes of static methods taking an `AsyncSession` the
  caller obtained from `session_scope()`; neither opens or commits its own
  session, keeping the repository layer the only module issuing queries.
- `TaskRepository`, `MessageRepository`, `EventRepository`, and
  `IterationRepository` (`juicebox.persistence.repositories`), completing
  the persistence layer: `TaskRepository.create`, `get`, and `list_for_run`
  (oldest-created first, `id` breaking ties); `MessageRepository.list_unconsumed`,
  agent-scoped and oldest-first by `seq`, and `mark_consumed`, which stamps
  `consumed_at` and returns the message, or `None` for an unknown id;
  `EventRepository.append` and `list_for_agent` (oldest-first by `seq`);
  `IterationRepository.append` and `list_for_run` (ordered by `iteration`).
  Same static-method, session-taking shape as `AgentRepository` and
  `RunRepository`; none of the four opens or commits its own session.
  `IterationRepository.list_for_run` filters on `run_id`, which the
  `(run_id, iteration)` unique index covers, so its own ORDER BY cannot be
  proven necessary by that filter alone; its test adds an agent-scoped
  assertion over the same rows, which has no covering index, to prove the
  ordering is genuinely enforced rather than incidental.
  `create_attempt` reads the current highest attempt then writes one
  higher, which races under concurrent starters for the same agent; the
  MVP has a single orchestrator and the unique `(agent_id, attempt)`
  constraint fails loudly rather than corrupting data, so this is recorded
  in the docstring rather than fixed with locking or retries.
- `artifact` and `iteration_record` tables (`juicebox.persistence.models`),
  the last of the W1 schema: `artifact` records one output an agent
  produces (`kind`, `name`, `path`, `content_type`, `size_bytes`) and
  `iteration_record` records one execution-loop iteration (`action`,
  `command`, `result`, `next_action`, an optional `task_id` set to `NULL`
  rather than cascaded if its task is deleted, and the `model`,
  `input_tokens`, `output_tokens`, and `cost_usd` section 18's minimum
  metrics require). `cost_usd` is `Numeric(12, 6)`, not a float, so
  sub-cent per-call costs are exact. `iteration_record` is unique on
  `(run_id, iteration)`. Both tables are append-only, like `event`, so
  neither has `updated_at`, and both cascade when their agent or run is
  deleted. `message` also gains an index on `(agent_id, seq)`, matching
  `event`'s, ahead of W1 increment 8's `list_unconsumed` query.
- Async SQLAlchemy engine and session factory (`juicebox.persistence`),
  built from `Settings().database_url` with a `NullPool` engine so pooled
  connections cannot outlive a test's event loop.
- `session_scope()` context manager that commits on a clean exit and rolls
  back and re-raises on error.
- Alembic migrations (`alembic.ini`, `migrations/`) configured for the
  async engine, taking the database URL from `Settings().database_url` so
  no connection string is committed. `pdm run alembic upgrade head`
  creates the schema.
- `message` and `event` tables storing messages sent to a running agent
  and events it emits. Both carry a monotonic `seq` identity column,
  which orders them deterministically even when several rows share a
  transaction-scoped `created_at`, and is the cursor W4 and W10 will page
  on. `event` additionally has an index on `(agent_id, seq)`. Both cascade
  when their agent or run is deleted.
- `MessageType` enum holding specification section 7's seven wire-form
  message types, enforced in the database by a CHECK constraint.
- Container image ships its own `alembic.ini` and `migrations/`
  alongside `src/`, and the `Dockerfile` installs dependencies
  (`pdm install --prod --no-self`) before copying source and migrations
  and installing the project (`pdm install --prod --no-editable`), so
  editing source no longer invalidates the dependency layer.
- `make migrate` Make target applying pending Alembic migrations to the
  Compose database by running `pdm run alembic upgrade head` inside a
  one-off `api` container.
- `agent` and `run` tables (`juicebox.persistence.models`): an agent
  carries its definition, objective, repository details, lifecycle status,
  and timestamps; a run is one numbered attempt at that objective, unique
  per `(agent_id, attempt)`, cascading on agent delete, and carrying the
  checkpoint specification section 12 requires.
- `AgentStatus` and `RunStatus` enums supplying the specification's
  lifecycle states, enforced in the database by CHECK constraints rather
  than native PostgreSQL enum types.
- `task` table (`juicebox.persistence.models`): one node in the task
  graph an agent decomposes its objective into, carrying its title,
  status, priority, dependency ids as `JSONB`, attempt count, result,
  error, and timestamps, cascading on both agent and run delete.
  `TaskStatus` and `TaskPriority` enums, also CHECK-constrained rather
  than native enums, following specification section 11's lowercase
  rendering of task states.
- Integration test harness (`tests/integration/conftest.py`) that brings
  the database to the latest migration and truncates every table before
  each test.
- `make test-integration` Make target that starts the database via Compose
  and runs the `integration`-marked test suite.
- pdm project skeleton with the `juicebox` package and a version smoke test.
- Make targets for `help`, `install`, `lint`, `test`, `build`, and `run`.
- Documentation set: README, changelog, feature list, and to do list.
- Settings module reading configuration from `JUICEBOX_`-prefixed
  environment variables or a `.env` file.
- FastAPI application factory serving `GET /health`.
- Uvicorn entrypoint: `python -m juicebox` and `make run` serve the API on
  the configured host and port.
- Container image built from `python:3.12-slim` that installs the project
  with pdm and serves `GET /health` on port 8000.
- Docker Compose services for PostgreSQL 17 and the API, with `make test`
  starting the database and `make run` starting the full stack.
- CI workflow running install, lint, unit tests, integration tests, build,
  a dependency scan, and a secret scan on every push and pull request.
- Development guide (`docs/development.md`) covering prerequisites, Make
  targets, running the API locally and under Compose, unit versus
  integration tests, and the settings reference. Closes out workstream
  W0: project foundation.
