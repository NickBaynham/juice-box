# To do

Workstreams from the [MVP decomposition](.dev-commander/design/0001-mvp-decomposition.md).
A workstream is complete when its exit criteria pass and every increment of
its plan is committed.

Phase 0 (W0, project foundation) and W1 (persistence) are complete; see
[FEATURES.md](FEATURES.md).

## Phase 1: MVP

- [x] W1. Persistence. Async SQLAlchemy models, Alembic migrations, session
      management, repository layer.
- [ ] W2. Declarative schemas. Pydantic agent definition and objective
      models, YAML loading, validation.
- [ ] W3. Agents API and lifecycle. Agent routes, lifecycle endpoints, state
      machine enforcement.
- [ ] W4. Events and structured logging. Event bus, event persistence,
      structured JSON logs, logs endpoint.
- [ ] W5. Tool layer. Tool protocol with shell, filesystem, and git tools.
- [ ] W6. Workspace and container runtime. Docker SDK integration, workspace
      layout, repository clone, permission enforcement, teardown.
- [ ] W7. Skills. Filesystem skill loader, tool granting, instruction
      injection, requirement verification, built-in skills.
- [ ] W8. Provider layer. Provider protocol, fake provider, Anthropic
      provider.
- [ ] W9. Execution loop. Runner, iteration records, task decomposition,
      message injection, completion detection, limits.
- [ ] W10. Completion and reporting. Final commit, branch push, execution
      report, artifacts endpoints.
- [ ] W11. CLI. Typer console script with run, status, logs, message, stop.
- [ ] W12. Acceptance. End-to-end scenario automated against the fake
      provider.

## Phase 2 and beyond

Spec sections 26 through 28, amended by the ADRs. The OpenAI provider is the
first Phase 2 item.
