# ADR-0003: The CLI is a thin client over the HTTP API

## Status

Accepted — 2026-08-14. Resolves the gap between spec section 30
(definition of done requires `juicebox run` and `juicebox status`) and
sections 21 and 23, which define no CLI surface or module.

## Context

Section 30 defines v0.1 as complete when a developer can run
`juicebox run --agent ... --repo ... --spec objective.yaml` followed by
`juicebox status <run-id>`. Neither the MVP API in section 21 nor the
repository structure in section 23 contains a CLI. The definition of
done is therefore unreachable as written.

Two readings are available. The first treats section 30 as conceptual,
meaning any equivalent HTTP call satisfies it. The second treats the CLI
as a real deliverable. The second is preferable: the CLI is the surface a
developer actually touches, it is what makes the acceptance test in
section 25 reproducible by hand, and it is small.

The risk in adding a CLI is that logic migrates into it — YAML parsing,
validation, and lifecycle rules living in the CLI rather than the
service. That would violate the API-first principle in section 3, because
CLI-only behavior would not be reachable through the API.

## Decision

A CLI ships in the MVP as `src/juicebox/cli/`, built with Typer, exposed
through the `juicebox` console script in `pyproject.toml`.

The CLI is a thin client. It may read local files, format output, and set
exit codes. It performs no validation, no lifecycle decisions, and no
state management of its own. Every command maps to HTTP calls against the
API defined in section 21:

- `juicebox run --agent <name> --repo <url> --spec <path>` reads the
  agent and objective YAML from disk, posts them verbatim to
  `POST /agents`, calls `POST /agents/{id}/start`, and prints the run id.
- `juicebox status <run-id>` calls `GET /agents/{id}/status`.
- `juicebox logs <run-id>` calls `GET /agents/{id}/logs`.
- `juicebox message <run-id> <text>` calls `POST /agents/{id}/messages`.
- `juicebox stop <run-id>` calls `POST /agents/{id}/stop`.

Schema validation of the agent and objective documents happens in the
API, not the CLI. A malformed spec produces an API 422 that the CLI
renders.

Section 23 is amended to add `cli/` alongside `api/` under
`src/juicebox/`. The API base URL comes from `JUICEBOX_API_URL`,
defaulting to `http://localhost:8000`.

## Consequences

- Any behavior added to the CLI must exist in the API first, which keeps
  the API-first principle enforceable by review.
- The CLI is testable without a container runtime by pointing it at a
  stubbed HTTP server.
- A remote Juice Box is usable from the CLI with no code change, only an
  environment variable.
- Offline use is not supported; the CLI requires a reachable API.
