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

### Added

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
