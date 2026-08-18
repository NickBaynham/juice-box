# Juice Box

Containerized orchestration platform that launches, controls, observes, and
coordinates autonomous AI agents working against persistent objectives in
isolated containers.

## Status

Early development. Workstream W0 (project foundation) is in progress. See
[FEATURES.md](FEATURES.md) for what works today and [TODO.md](TODO.md) for
what is planned.

## Requirements

- Python 3.12 or newer
- [pdm](https://pdm-project.org/)
- Docker and Docker Compose

## Getting started

```
make install
make lint
make test
make build
```

## Make targets

| Target | Purpose |
| --- | --- |
| `help` | List available targets |
| `install` | Install dependencies with pdm |
| `lint` | Run ruff |
| `test` | Start the database via Compose, then run unit tests (integration tests are excluded) |
| `build` | Build the distribution |
| `run` | Build and start the full stack (API and database) via Docker Compose |

Tests marked `integration` require Docker services and are excluded from
`make test`. Run them with `pdm run pytest -m integration`.

## Layout

| Path | Contents |
| --- | --- |
| `src/juicebox/` | Application package |
| `tests/unit/` | Unit tests |
| `docs/specs/` | Specification |
| `.dev-commander/` | Designs, ADRs, plans, and reviews |
| `.test-commander/` | Test strategy, requirements, and traceability |

## Documentation

- [Specification](docs/specs/juice-box-spec.md)
- [Feature list](FEATURES.md)
- [To do](TODO.md)
- [Changelog](CHANGELOG.md)
- [MVP decomposition](.dev-commander/design/0001-mvp-decomposition.md)
- [Definition of done](.dev-commander/design/0002-definition-of-done.md)
