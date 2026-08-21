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
