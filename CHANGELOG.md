# Changelog

All notable changes to this project are recorded here. The format follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/) and this project
adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

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
