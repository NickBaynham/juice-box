# Features

What works today. Planned work is tracked in [TODO.md](TODO.md).

## Build and test

- pdm project exposing the `juicebox` package with a declared version.
- Make targets for setup, lint, test, and build.
- Pytest suite with an `integration` marker that separates tests requiring
  Docker services from the default unit run.
- Ruff linting across the repository.
- `make run` builds and starts the API and database via Docker Compose;
  `pdm run python -m juicebox` serves the API directly through uvicorn
  without Docker.
- Development guide (`docs/development.md`) covering setup, every Make
  target, running the API, and the settings reference.

## Persistence

- Async SQLAlchemy engine and session factory built from `Settings().database_url`.
- `session_scope()` context manager committing on success and rolling back
  and re-raising on error.
- Integration test harness that brings the database to the latest Alembic
  migration once per session and truncates every table before each test.
- Alembic migrations under `migrations/`, configured for the async engine
  and reading the database URL from `Settings().database_url`.
- `agent` table storing an agent's definition, objective, repository URL,
  base and work branches, lifecycle status, failure reason, and creation,
  update, start, and finish timestamps.
- `run` table storing one numbered attempt at an agent's objective, with
  its status, iteration count, current task, resume checkpoint, failure
  reason, and timestamps. Attempts are unique per agent and cascade when
  the agent is deleted.
- `AgentStatus` and `RunStatus` enums holding the specification's
  lifecycle states, enforced in the database by CHECK constraints.
- `task` table storing one node of the task graph an agent decomposes its
  objective into: title, status, priority, dependency ids, attempt count,
  result, error, and timestamps. Cascades when its agent or run is
  deleted.
- `TaskStatus` and `TaskPriority` enums, enforced in the database by
  CHECK constraints. `TaskStatus` holds specification section 11's eight
  task states in their lowercase form.
- `message` table storing one message sent to a running agent: type, body,
  and creation, update, and consumption timestamps. Cascades when its
  agent or run is deleted.
- `event` table storing one append-only event an agent emits while
  running: name, payload, and creation timestamp. Cascades when its agent
  or run is deleted, and carries an index on `(agent_id, seq)` for paged
  reads.
- `MessageType` enum holding specification section 7's seven wire-form
  message types, enforced in the database by a CHECK constraint.
- `seq`, a monotonic `BIGSERIAL`-equivalent identity column on `message`
  and `event`, giving deterministic ordering independent of `created_at`
  and serving as the cursor for future paged reads. `message` also
  carries an index on `(agent_id, seq)`, matching `event`'s.
- `artifact` table storing one output an agent produces: kind, name,
  path, content type, size in bytes, and creation timestamp. Cascades
  when its agent or run is deleted.
- `AgentRepository` and `RunRepository` (`juicebox.persistence.repositories`),
  classes of static methods each taking an `AsyncSession` from
  `session_scope()`. `AgentRepository` provides `create`, `get` (`None`
  for an unknown id), `list` (newest-created first, paged by `limit` and
  `offset`), `set_status` (advances `updated_at`), and `delete`
  (cascading to the agent's runs and every run-scoped row).
  `RunRepository` provides `create_attempt`, which numbers an agent's run
  attempts per ADR-0006, and `get_current`, which returns the latest
  attempt.
- `TaskRepository`, `MessageRepository`, `EventRepository`, and
  `IterationRepository` (`juicebox.persistence.repositories`), completing
  the repository layer in the same static-method, session-taking shape.
  `TaskRepository` provides `create`, `get`, and `list_for_run`
  (oldest-created first). `MessageRepository` provides `list_unconsumed`,
  agent-scoped and oldest-first by `seq`, and `mark_consumed`, which
  stamps `consumed_at`. `EventRepository` provides `append` and
  `list_for_agent` (oldest-first by `seq`). `IterationRepository` provides
  `append` and `list_for_run` (ordered by `iteration`).
- `iteration_record` table storing one execution-loop iteration: action,
  command, result, next action, an optional link to the task it worked
  on (set to `NULL` rather than deleted if that task goes away), the
  model used and its input/output token counts, an exact `Numeric(12,
  6)` cost in USD, and a creation timestamp. Unique on
  `(run_id, iteration)`; cascades when its agent or run is deleted.
- `docs/persistence.md`, documenting the entity list, status and type
  enums, repository API signatures, and how to add a migration, so the
  layer can be used without opening `models.py`.
- `tests/integration/test_migration_data_correctness.py`, proving a data
  migration's `UPDATE` statements actually rewrite seeded rows, not only
  that the schema applies.
- `tests/unit/test_query_locality.py`, an `ast`-based check that no
  module outside `persistence/` issues a query directly.

## Declarative schemas

- `juicebox.schemas.loading.load_agent_definition(document)`, parsing a
  YAML string with `yaml.safe_load` and validating it against
  `AgentDefinition`, the agent document envelope of specification
  section 8: `apiVersion` (must be `juicebox.ai/v1`), `kind` (must be
  `Agent`), `metadata.name` (must match `^[a-z0-9][a-z0-9-]*$`), and
  `agent` (a `model` provider/model pair plus a `system_prompt`). Every
  model forbids unknown fields, so a mistyped key such as `api_version:`
  is rejected with a field-level `ValidationError` instead of being
  silently dropped. Malformed YAML raises `yaml.YAMLError` unchanged.
  Schemas live independently of `juicebox.persistence`: neither package
  imports the other.
- `AgentDefinition` also carries top-level `skills` and `secrets` lists,
  siblings of `metadata:` and `agent:` per section 8 and section 17, each
  defaulting to empty. `agent.system_prompt` is stripped and rejected when
  empty. Each `secrets` entry must match `Metadata.name`'s
  `^[a-z0-9][a-z0-9-]*$` slug pattern, checking that a secret is
  referenced by name rather than embedded — not that the name is free of
  credential-shaped text, which gitleaks already checks in CI.
- `AgentDefinition.runtime` (optional `Runtime`) and `.permissions`
  (`Permissions`, always present) validate the `runtime:` and
  `permissions:` blocks of section 8. `Runtime.memory` and `.timeout` are
  unit strings (`4Gi`, `8h`) validated against `^(\d+)(Ki|Mi|Gi|Ti)$` and
  `^(\d+)(s|m|h)$`; `.memory_bytes` and `.timeout_delta` convert them to an
  `int` and a `timedelta` through a plain `@property`, so they never
  appear in `model_dump()` and a dumped `Runtime` still re-validates.
  `Permissions` defaults to least privilege — `filesystem: read-only`,
  `network: false`, `shell: false` — as a default instance, so an agent
  definition that omits `permissions:` is never treated as unrestricted,
  per ADR-0004. `FilesystemAccess` is a `StrEnum` (`read-only`,
  `read-write`) per ADR-0009.
- `AgentDefinition.repository` (optional `Repository`) and `.execution`
  (`Execution`, always present) validate the `repository:` and
  `execution:` blocks of section 8. `Repository.url` must match
  `^https://`, since W6 clones inside a container with no agent key and an
  SSH URL would otherwise fail later, at clone time, with a less useful
  message. `Execution.max_iterations` defaults to `100` and must be
  positive, so it always has a value for W9 to enforce.
  `Execution.require_approval_for` is a list of `ApprovalOperation`, a
  closed `StrEnum` of six slugs — `merge`, `production-deployment`,
  `secret-modification`, `force-push`, `cloud-resource-deletion`,
  `repository-data-deletion` — so ADR-0004's requirement that an unknown
  approval operation be rejected, not silently dropped, is enforceable.
  Specification section 8's full example now validates end to end.

## Configuration

- Typed settings for API host, API port, log level, and database URL, read
  from `JUICEBOX_`-prefixed environment variables or a `.env` file, each with
  a working local default.

## API

- FastAPI application built by a factory, titled Juice Box and versioned from
  the package.
- `GET /health` returning the service status and running version.

## Container image

- A `python:3.12-slim` based image installs the project with pdm and serves
  the API through `python -m juicebox`, exposing port 8000.
- The image carries its own `alembic.ini` and `migrations/`, so it can
  apply its own schema without a host pdm environment. Dependencies are
  installed in a separate layer (`pdm install --prod --no-self`) before
  source and migrations are copied in and the project itself is installed
  (`pdm install --prod --no-editable`), so a source edit no longer
  invalidates the dependency layer.
- `make migrate` applies pending Alembic migrations to the Compose
  database by running `pdm run alembic upgrade head` inside a one-off
  `api` container.

## Compose services

- `docker-compose.yml` runs PostgreSQL 17 as a `db` service with a health
  check and a named data volume, and the API as an `api` service built from
  the Dockerfile, configured to reach `db` by service name.
- `make test` starts the database via Compose before running the test
  suite; `make run` builds and starts the full stack via Compose.

## Continuous integration

- GitHub Actions workflow (`.github/workflows/ci.yml`) runs on every push
  and pull request: install, lint, unit tests, integration tests, build, a
  `pip-audit` dependency scan, and a `gitleaks` secret scan.
