# ADR-0006: The agent id is the handle callers use; runs are attempts

## Status

Accepted — 2026-08-14. Resolves the mismatch between spec section 21,
which keys every endpoint on `/agents/{id}`, and section 30, which has
callers pass a `<run-id>`.

## Context

Section 4 defines a Run as one execution of an agent against an
objective, and section 12 requires runs to be persisted. Section 21
exposes no run-scoped endpoint: everything hangs off `/agents/{id}`.
Section 30 then has the developer call `juicebox status <run-id>`. There
is no documented way to obtain a run id, and no endpoint accepts one.

This surfaced while specifying W3 and W10 and needs settling before
either is built, because it determines the primary key every client
holds.

## Decision

The agent id is the handle. A caller creates an agent with an objective,
receives one id, and uses that id for every subsequent call.

- `POST /agents` creates an agent bound to one objective and returns its
  id. An agent is not a reusable template in the MVP; a second objective
  means a second agent.
- A Run row records one attempt at that objective. `POST
  /agents/{id}/start` creates run attempt 1. Per ADR-0002,
  `POST /agents/{id}/restart` creates attempt 2, and so on.
- Runs have ids and are persisted, but no MVP endpoint is keyed on them.
  `GET /agents/{id}/status` includes a `current_run` object carrying the
  run id, attempt number, and iteration count. Tasks, messages, events,
  artifacts, and iteration records all carry both `agent_id` and
  `run_id`, so run-scoped endpoints can be added later without a
  migration.
- The CLI takes an agent id. Section 30's `<run-id>` is amended to
  `<agent-id>`, and `juicebox run` prints that id.

## Consequences

- Clients hold one identifier, and every section 21 route works as
  written.
- Run history is queryable through the agent, so a restarted agent shows
  its earlier failed attempts.
- Run-scoped endpoints remain available as a Phase 2 addition with no
  data model change.
- The word "run" stays meaningful in the domain model rather than being
  an alias for the agent id.
