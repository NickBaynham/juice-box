# Juice Box

Containerized orchestration platform that launches, controls, observes, and
coordinates autonomous AI agents working against persistent objectives in
isolated containers.

## Status

Early development. Workstream W0 (project foundation) is complete. See
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
make test-integration
make build
make run
```

`make run` serves `GET /health` on `localhost:8000`. See
[docs/development.md](docs/development.md) for prerequisites, every Make
target, running the API with and without Docker, unit versus integration
tests, and the full settings reference.

## Layout

| Path | Contents |
| --- | --- |
| `src/juicebox/` | Application package |
| `migrations/` | Alembic environment and revisions |
| `tests/unit/` | Unit tests |
| `docs/specs/` | Specification |
| `.dev-commander/` | Designs, ADRs, plans, and reviews |
| `.test-commander/` | Test strategy, requirements, and traceability |

## Documentation

- [Development guide](docs/development.md)
- [Specification](docs/specs/juice-box-spec.md)
- [Feature list](FEATURES.md)
- [To do](TODO.md)
- [Changelog](CHANGELOG.md)
- [MVP decomposition](.dev-commander/design/0001-mvp-decomposition.md)
- [Definition of done](.dev-commander/design/0002-definition-of-done.md)
