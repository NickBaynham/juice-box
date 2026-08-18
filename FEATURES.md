# Features

What works today. Planned work is tracked in [TODO.md](TODO.md).

## Build and test

- pdm project exposing the `juicebox` package with a declared version.
- Make targets for setup, lint, test, and build.
- Pytest suite with an `integration` marker that separates tests requiring
  Docker services from the default unit run.
- Ruff linting across the repository.
- `make run` serves the API locally through uvicorn.

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
