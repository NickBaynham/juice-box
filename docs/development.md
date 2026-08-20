# Development guide

How to set up, run, and test Juice Box locally. This is the canonical
reference; `README.md` links here instead of repeating it.

## Prerequisites

- Python 3.12 or newer
- [pdm](https://pdm-project.org/)
- Docker and Docker Compose (Docker must be running before `make test`
  or `make run`)

## Clone and install

```
git clone git@github.com:NickBaynham/juice-box.git
cd juice-box
make install
```

`make install` runs `pdm install`, which creates a `.venv` and installs
the project plus its dev dependency group (ruff, pytest, pytest-asyncio,
httpx, asyncpg).

## Make targets

| Target | Runs | Purpose |
| --- | --- | --- |
| `help` | — | List available targets |
| `install` | `pdm install` | Install dependencies |
| `lint` | `pdm run ruff check .` | Run the linter |
| `test` | `docker compose up -d --wait db`, then `pdm run pytest -m "not integration"` | Start the database and run unit tests |
| `test-integration` | `docker compose up -d --wait db`, then `pdm run pytest -m integration` | Start the database and run integration tests |
| `build` | `pdm build` | Build the distribution |
| `run` | `docker compose up -d --build` | Build and start the full stack (API and database) |

## Running the API

### Locally, without Docker

The health endpoint has no database dependency, so it can be served
without Compose:

```
pdm run python -m juicebox
```

This reads `Settings()` and calls `uvicorn.run` on the configured host
and port (`0.0.0.0:8000` by default). Confirm it is serving:

```
curl -s localhost:8000/health
```

Expect `{"status":"ok","version":"0.1.0"}`.

### Under Docker Compose

```
make run
```

This builds the image from the `Dockerfile` and starts both Compose
services: `db` (PostgreSQL 17, publishing 5432) and `api` (the FastAPI
app, publishing 8000, waiting for `db`'s healthcheck before starting).
Confirm with the same `curl` command above. Stop the stack with
`docker compose down`.

## Running tests

Tests are split by the `integration` pytest marker (declared in
`pyproject.toml`). Integration tests need Docker; unit tests do not.

- Unit tests only: `make test`. This starts the `db` Compose service
  first, per ADR-0001 (PostgreSQL is the persistence store from the
  first increment that needs it, so the test target always brings the
  database up), then runs `pdm run pytest -m "not integration"`. None of
  the current unit tests touch the database directly.
- Integration tests only: `make test-integration`. This also starts the
  `db` Compose service, then runs `pdm run pytest -m integration`, which
  builds the container image, runs it publishing host port 8001 and polls
  `http://localhost:8001/health`, and separately opens sessions against
  the `db` Compose service through `juicebox.persistence.session_scope`
  as well as a direct `asyncpg` connection.
- Both: `make test && make test-integration`.

`tests/integration/conftest.py` provides two autouse fixtures shared by
every integration test that needs the schema: a session-scoped fixture
that brings the database to the latest Alembic migration, and a
function-scoped fixture that truncates every table in `Base.metadata`
before each test so leftover rows on the persistent `db-data` volume
cannot leak between test runs. Both are no-ops until a later increment
adds `alembic.ini` and `juicebox.persistence.models`.

## Settings

`Settings` (`src/juicebox/config/settings.py`) is a
`pydantic_settings.BaseSettings` subclass. Every field can be overridden
by an environment variable with the `JUICEBOX_` prefix, or by a `.env`
file in the working directory if one is present.

| Field | Env var | Default |
| --- | --- | --- |
| `api_host` | `JUICEBOX_API_HOST` | `0.0.0.0` |
| `api_port` | `JUICEBOX_API_PORT` | `8000` |
| `log_level` | `JUICEBOX_LOG_LEVEL` | `INFO` |
| `database_url` | `JUICEBOX_DATABASE_URL` | `postgresql+asyncpg://juicebox:juicebox@localhost:5432/juicebox` |

The Compose `api` service overrides `JUICEBOX_DATABASE_URL` to
`postgresql+asyncpg://juicebox:juicebox@db:5432/juicebox` so it reaches
the `db` service by its Compose service name rather than `localhost`.

## Known deviations from the plan

- The `Dockerfile` copies `src/` before running `pdm install`, not
  after. The project builds as a real package (`[tool.pdm] distribution
  = true`), so `pdm install` needs the source present to install it.
- The CI workflow (`.github/workflows/ci.yml`) was generated from the
  dev-commander plugin's local template cache rather than from a
  `templates/ci/github/python/ci.yml.tmpl` path inside this repository;
  no such path exists in this repository.
