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
