# Plan 0001: W0 Project foundation

## Goal

Stand up a running, linted, tested, containerized FastAPI service with a
health endpoint and a dockerized PostgreSQL, so every later workstream
has a working build and test loop to extend.

## Architecture

A single `juicebox` package under `src/` exposes a FastAPI application
built by an application factory. Configuration is read once into a
settings object from the environment. PostgreSQL runs as a Compose
service and is required by the test target, per ADR-0001; no code in this
workstream talks to it beyond proving reachability.

## Tech Stack

Python 3.12+, pdm, FastAPI, Uvicorn, Pydantic and pydantic-settings,
Ruff, Pytest with pytest-asyncio, httpx, asyncpg, Docker and Docker
Compose, PostgreSQL 17.

## Global Constraints

- Definition of done: design 0002. Every increment inherits its seven
  increment criteria, and this workstream inherits its workstream
  criteria. They are not restated per increment.
- Every increment is test-first and ends in a commit.
- Version pins are lower bounds; pdm resolves the current release at
  install time.
- No emojis in code, output, or documentation.
- `make lint test` must pass before any increment is committed.
- Docker must be running; `make test` starts the database itself.
- Consumes ADR-0001 (PostgreSQL from the first increment) and design
  0001 workstream W0.

## Increments

### 1. pdm project, package skeleton, and Make targets

- [x] Create the pdm project so `import juicebox` works and the standard
      Make targets run.

Files:
`pyproject.toml`, `Makefile`, `.gitignore`, `README.md`, `CHANGELOG.md`,
`FEATURES.md`, `TODO.md`, `src/juicebox/__init__.py`,
`tests/unit/test_smoke.py`. No `tests/__init__.py` is created; pytest
uses rootdir discovery.

Failing test first — `tests/unit/test_smoke.py`:

```python
import juicebox


def test_package_exposes_version():
    assert juicebox.__version__ == "0.1.0"
```

Minimal implementation:

- `src/juicebox/__init__.py` containing `__version__ = "0.1.0"`.
- `pyproject.toml` with `name = "juice-box"`, `version = "0.1.0"`,
  `requires-python = ">=3.12"`, the pdm-backend build system,
  `[tool.pdm] distribution = true`, `[tool.pdm.build] package-dir = "src"`,
  a dev dependency group of `ruff>=0.6`, `pytest>=8.0`,
  `pytest-asyncio>=0.24`, `httpx>=0.27`, and
  `[tool.pytest.ini_options]` setting `testpaths = ["tests"]`,
  `asyncio_mode = "auto"`, and
  `markers = ["integration: requires docker services"]`.
- `Makefile` with `help`, `install` (`pdm install`), `lint`
  (`pdm run ruff check .`), `test` (`pdm run pytest -m "not integration"`),
  `build` (`pdm build`), and a `run` target printing that it is defined in
  increment 4.
- `README.md` under 400 lines linking to `CHANGELOG.md`, `FEATURES.md`,
  `TODO.md`, and `docs/specs/juice-box-spec.md`.
- `FEATURES.md` listing only what works today, and `TODO.md` seeded from
  the workstream list in design 0001.
- `.gitignore` covering `__pycache__/`, `.pdm-python`, `.venv/`, `dist/`,
  `.pytest_cache/`, `.ruff_cache/`, `*.egg-info/`.

Verify: `make install && make lint && make test && make build`

Commit: `Add pdm project skeleton and Make targets`

### 2. Settings module

- [x] Read configuration from the environment into a typed settings
      object with usable defaults.

Files: `src/juicebox/config/__init__.py`,
`src/juicebox/config/settings.py`, `tests/unit/test_settings.py`

Failing test first — `tests/unit/test_settings.py`:

```python
from juicebox.config.settings import Settings


def test_defaults():
    settings = Settings()
    assert settings.api_host == "0.0.0.0"
    assert settings.api_port == 8000
    assert settings.log_level == "INFO"
    assert settings.database_url.startswith("postgresql+asyncpg://")


def test_environment_overrides(monkeypatch):
    monkeypatch.setenv("JUICEBOX_API_PORT", "9000")
    assert Settings().api_port == 9000
```

Minimal implementation: `Settings(BaseSettings)` with
`model_config = SettingsConfigDict(env_prefix="JUICEBOX_", env_file=".env")`,
fields `api_host: str = "0.0.0.0"`, `api_port: int = 8000`,
`log_level: str = "INFO"`, and
`database_url: str = "postgresql+asyncpg://juicebox:juicebox@localhost:5432/juicebox"`.
Add `pydantic-settings>=2.6` to project dependencies.

Verify: `make lint && make test`

Commit: `Add settings module reading configuration from the environment`

### 3. Application factory and health endpoint

- [ ] Serve `GET /health` from a FastAPI application built by a factory.

Files: `src/juicebox/api/__init__.py`, `src/juicebox/api/health.py`,
`src/juicebox/app.py`, `tests/unit/test_health.py`

Failing test first — `tests/unit/test_health.py`:

```python
import httpx

from juicebox.app import create_app


async def test_health_returns_ok():
    transport = httpx.ASGITransport(app=create_app())
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok", "version": "0.1.0"}
```

Minimal implementation: `health.py` defines an `APIRouter` with a
`GET /health` route returning `{"status": "ok", "version": __version__}`.
`app.py` defines `create_app() -> FastAPI` that constructs the app with
`title="Juice Box"` and `version=__version__` and includes the health
router. Add `fastapi>=0.115` to project dependencies.

Verify: `make lint && make test`

Commit: `Add application factory and health endpoint`

### 4. Uvicorn entrypoint and make run

- [ ] Start the API with `make run` using the settings from increment 2.

Files: `src/juicebox/__main__.py`, `tests/unit/test_entrypoint.py`,
`Makefile`

Failing test first — `tests/unit/test_entrypoint.py`:

```python
from juicebox import __main__


def test_main_starts_uvicorn_with_settings(monkeypatch):
    captured = {}

    def fake_run(app, **kwargs):
        captured["app"] = app
        captured["kwargs"] = kwargs

    monkeypatch.setattr(__main__.uvicorn, "run", fake_run)
    __main__.main()

    assert captured["app"] == "juicebox.app:create_app"
    assert captured["kwargs"]["port"] == 8000
    assert captured["kwargs"]["factory"] is True
```

Minimal implementation: `__main__.py` defines `main()` calling
`uvicorn.run("juicebox.app:create_app", host=settings.api_host,
port=settings.api_port, factory=True)` and an
`if __name__ == "__main__": main()` guard. Change the Makefile `run`
target to `pdm run python -m juicebox`. Add `uvicorn[standard]>=0.32` to
project dependencies.

Verify: `make lint && make test`, then `make run` and confirm
`curl -s localhost:8000/health` returns the health payload.

Commit: `Add uvicorn entrypoint and wire make run`

### 5. API container image

- [ ] Build a container image that serves the health endpoint.

Files: `Dockerfile`, `.dockerignore`,
`tests/integration/test_container_image.py`

Failing test first — `tests/integration/test_container_image.py`, marked
`@pytest.mark.integration`: build the image with
`docker build -t juice-box:test .`, run it detached publishing 8001 to
8000, poll `http://localhost:8001/health` until it returns 200 or 30
seconds elapse, assert the payload, and remove the container in a
`finally` block.

Minimal implementation: a Dockerfile based on `python:3.12-slim` that
installs pdm, copies `pyproject.toml` and `pdm.lock`, runs
`pdm install --prod --no-editable`, copies the source, exposes 8000, and
sets `CMD ["pdm", "run", "python", "-m", "juicebox"]`. `.dockerignore`
excludes `.git`, `.venv`, `__pycache__`, `.pytest_cache`, `.ruff_cache`,
`dist`, and `.dev-commander`.

Verify: `pdm run pytest -m integration tests/integration/test_container_image.py`

Commit: `Add API container image`

### 6. Compose services and database reachability

- [ ] Run PostgreSQL and the API under Compose, make `make test` start
      the database, and prove the test session can reach it.

Files: `docker-compose.yml`, `Makefile`,
`tests/integration/test_database_connection.py`

Failing test first — `tests/integration/test_database_connection.py`,
marked `@pytest.mark.integration`: read `Settings().database_url`, strip
the `+asyncpg` dialect suffix, connect with `asyncpg.connect`, assert
`await connection.fetchval("SELECT 1") == 1`, and close the connection.
Add `asyncpg>=0.30` to the dev dependency group so the test can run. If
the settings default and the Compose service disagree, correct the
default in `settings.py` rather than the test.

Minimal implementation: `docker-compose.yml` with a `db` service on
`postgres:17`, user, password, and database all `juicebox`, port 5432
published, a named `db-data` volume, and a healthcheck running
`pg_isready -U juicebox` with a 5 second interval and 10 retries; and an
`api` service built from the Dockerfile, publishing 8000, depending on
`db` with `condition: service_healthy`, and setting
`JUICEBOX_DATABASE_URL` to reach `db` by service name. Change the
Makefile `test` target to run `docker compose up -d --wait db` before
pytest, and the `run` target to `docker compose up -d --build`.

Verify: `make test && pdm run pytest -m integration tests/integration/test_database_connection.py`

Commit: `Add compose services for PostgreSQL and prove reachability`

### 7. CI workflow

- [ ] Run install, lint, test, build, and the security scans on every
      push and pull request.

Files: `.github/workflows/ci.yml`

Failing test first: none applies; the executable check is the first CI
run reporting success on the branch.

Minimal implementation: generate the workflow from the dev-commander
Python CI template at
`templates/ci/github/python/ci.yml.tmpl`, substituting the project name.
The template's ubuntu-latest runner already provides Docker, so the
`make test` step starts the database through Compose and no service
container block is needed. Add a step running
`pdm run pytest -m integration` after `make test`.

Verify: push the branch and confirm the workflow completes green.

Commit: `Add CI workflow`

### 8. Workstream close-out

- [ ] Document what W0 produced, review it, and record the result.

Files: `docs/development.md`, `README.md`, `CHANGELOG.md`,
`FEATURES.md`, `TODO.md`

Failing test first: none applies; this increment produces documentation
and review records, and its executable check is that a reader who has
never seen the repository can go from clone to a served health endpoint
using only `docs/development.md`.

Minimal implementation:

- `docs/development.md` covering prerequisites, the Make targets, how to
  run the API locally and in Compose, how to run unit versus integration
  tests, and the settings keys with their defaults and env var names.
- `README.md` links to it.
- `CHANGELOG.md` Unreleased section records the foundation.
- `FEATURES.md` lists the health endpoint, settings, container image, and
  Compose environment as working today.
- `TODO.md` lists W1 through W11 as not yet built.
- Run `/dc:review` over the workstream diff and address every finding.
- Run `/dc:journal` recording what was built and anything that deviated
  from this plan.

Verify: from a clean clone, follow `docs/development.md` verbatim and
reach a 200 from `GET /health`; then `make lint test && pdm run pytest -m integration`.

Commit: `Document the development workflow and close out W0`

## Exit Criteria

Design 0002's workstream criteria apply in full. In addition:

- `make install lint test build` passes from a clean checkout.
- `make run` serves `GET /health` returning 200.
- `docker compose up -d --wait db` reports the database healthy and the
  integration suite connects to it.
- CI is green on the branch.
- The workstream W0 entry in design 0001 can be checked off, and W1, W2,
  W5, and W7 are unblocked.
