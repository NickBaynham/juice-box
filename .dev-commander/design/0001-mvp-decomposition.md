# Design 0001: MVP decomposition and phase roadmap

## Goal

Break the Juice Box MVP defined in spec section 24 into ordered
workstreams small enough that each becomes one dc-plan file.

## Context

Spec section 24 describes the MVP as a single scope, but it spans an HTTP
API, a container runtime, a workspace manager, an execution loop, a tool
layer, a provider layer, Git integration, task state, messaging, and
reporting. That is roughly ten independent subsystems. Planned as one
unit it would produce a plan too large to execute or review, and its
early increments would depend on interfaces that do not exist yet.

ADR-0001 through ADR-0005 resolve the specification conflicts that
affected scope. This document consumes those decisions and orders the
remaining work.

## Approach

Work is organized as one plan per workstream. A workstream is complete
when its exit criteria pass and its plan's increments are all committed.
Plans are written just ahead of implementation, not all at once, because
each plan must name exact file paths and exact test names, and later
workstreams depend on interfaces the earlier ones define.

Phase 0 is foundation. Phase 1 is the MVP and ends at the section 25
acceptance test. Phases 2 through 4 follow spec sections 26 through 28,
amended by the ADRs.

Two rules hold across every workstream. Every increment is test-first and
ends in a commit. Nothing merges to `main` without `make lint test`
passing against a dockerized PostgreSQL.

### Phase 0 — Foundation

**W0. Project foundation.** pdm project, Make targets, Docker Compose
with PostgreSQL, Dockerfile, FastAPI application, `GET /health`,
settings module, docs set. Depends on nothing.
Exit: `make install lint test build` green; `GET /health` returns 200.

### Phase 1 — MVP

**W1. Persistence.** SQLAlchemy 2.x async models for agent, run, task,
message, event, artifact, and iteration record; Alembic migrations;
session management; repository layer. Depends on W0. Per ADR-0001.
Exit: migrations apply to an empty database; every model round-trips.

**W2. Declarative schemas.** Pydantic models for the agent definition
(spec section 8) and objective (section 9), YAML loading, and validation
including `permissions` and `execution.require_approval_for`. Depends on
W0. Per ADR-0004.
Exit: `examples/*.yaml` validate; malformed documents are rejected with
field-level errors.

**W3. Agents API and lifecycle.** `POST/GET/DELETE /agents`, the six
lifecycle endpoints, `GET /agents/{id}/status`, and enforcement of the
section 6 state machine. Depends on W1, W2.
Exit: illegal transitions are refused; OpenAPI covers the section 21
agent and lifecycle routes.

**W4. Events and structured logging.** In-process event bus, the section
19 event names, event persistence, structured JSON logs, and
`GET /agents/{id}/logs`. Depends on W1.
Exit: emitted events are queryable through the API in order.

**W5. Tool layer.** `Tool` protocol from section 15 plus shell,
filesystem, and git tools with a uniform result contract. Depends on W0.
Exit: each tool's success, failure, and timeout paths are tested.

**W6. Workspace and container runtime.** Docker SDK integration, the
`/workspace` layout from section 4, repository clone, base checkout, work
branch creation, permission enforcement, and teardown. Depends on W5.
Per ADR-0004 for permission enforcement.
Exit: a container starts, clones a fixture repository, creates the work
branch, and is torn down cleanly.

**W7. Provider layer.** Provider protocol, the fake provider, and the
Anthropic provider. Depends on W0. Per ADR-0005.
Exit: both implementations satisfy the same protocol test suite; the fake
runs offline and deterministically.

**W8. Execution loop.** Runner implementing section 10, iteration
records, task decomposition and the section 11 task states, injection of
messages received while running, completion and failure detection, and
`max_iterations` and timeout enforcement. Depends on W2, W4, W5, W6, W7.
Per ADR-0002: state is written durably each iteration, and the loop need
not be re-entrant.
Exit: a scripted objective runs to `COMPLETED` against the fake provider.

**W9. Completion and reporting.** Final commit, branch push, execution
report generation from persisted records, and the artifacts endpoints.
Depends on W8.
Exit: a completed run pushes its branch and exposes a retrievable report.

**W10. CLI.** Typer console script with `run`, `status`, `logs`,
`message`, and `stop`. Depends on W3. Per ADR-0003.
Exit: the section 30 command sequence works against a running API.

**W11. Acceptance.** The section 25 end-to-end scenario as an automated
test, run against the fake provider in CI and against Anthropic manually.
Depends on W9, W10.
Exit: all twelve steps of section 25 pass.

### Phase 2 and beyond

Phase 2 is spec section 26 with three amendments: PostgreSQL persistence
is removed because it lands in W1; checkpoint resume is scoped by
ADR-0002; approval gates become suspension rather than refusal per
ADR-0004. The OpenAI provider is the first Phase 2 item, per ADR-0005,
because adding it without touching the execution loop tests whether the
provider abstraction held. Phases 3 and 4 follow spec sections 27 and 28
unchanged.

## Alternatives considered

**One plan for the whole MVP.** Rejected: it would exceed the dc-plan
increment rubric, and its later increments would be speculative.

**Vertical slice first — one thin path through every subsystem.**
Rejected: the thinnest useful path still requires the container runtime,
the provider layer, and Git integration, so the slice is most of the MVP.

**Execution loop before the API.** Rejected: it violates the API-first
principle in spec section 3 and would leave the loop's state transitions
untestable through the interface that ultimately owns them.

## Interfaces

The interfaces other workstreams consume, defined in the workstream that
owns them:

- W1 owns the ORM models and the repository layer's async accessors.
- W2 owns `AgentDefinition` and `Objective` as Pydantic models.
- W4 owns `EventBus.emit(event_name, payload)` and the event name set.
- W5 owns `Tool.execute(request: ToolRequest) -> ToolResult`.
- W6 owns `Workspace` and the container lifecycle handle.
- W7 owns the provider protocol in `providers/base.py`.
- W8 owns `Runner`, which consumes all of the above.

No workstream may reach past these boundaries into another's internals.

## Risks

- **Container-in-container.** Running agent containers from a
  containerized API needs a mounted Docker socket or a host-side runner.
  W6 must settle this early; it is the most likely source of rework.
- **Loop quality is not architectural.** W8 can pass its exit criteria
  against the fake provider while producing a poor agent against a real
  model. W11's manual Anthropic run is the only real check.
- **Agent container image size.** A container carrying Node, Playwright,
  and Python for the acceptance test will be large; image build time may
  dominate the W11 feedback loop.
- **Secret handling.** Spec section 17 is unresolved for the MVP beyond
  environment variables. W6 should not invent a secrets abstraction; an
  ADR is needed if requirements grow past environment injection.
