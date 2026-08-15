# ADR-0002: Durable state in the MVP, checkpoint resume in Phase 2

## Status

Accepted — 2026-08-14. Resolves the conflict between spec section 12
(state must survive restarts and resume from the latest safe checkpoint)
and section 26 (restart/resume checkpoints listed as Phase 2).

## Context

Section 12 states that agent state must survive process or container
restarts and that a restarted Juice Box should resume from the latest
safe checkpoint. Section 26 defers "restart/resume checkpoints" to
Phase 2. Section 24 asks only that the MVP "maintain task/execution
state" and "stop/restart an agent."

These are two different capabilities being described by one word.
Durability — state is written to a store and readable after a crash — is
cheap and is a precondition for observability, the API, and the final
execution report. Resumption — a new container picks up an interrupted
run mid-iteration and continues without repeating or corrupting work — is
expensive, because it requires the execution loop to be re-entrant, tool
side effects to be idempotent or replayable, and the workspace filesystem
to be reconstructable.

Conflating them would either inflate the MVP or leave the MVP with no
durable record, which breaks the report in section 24.

## Decision

The MVP delivers durability, not resumption.

Durability in the MVP:

- Every state transition, task transition, iteration record, message,
  tool invocation, and emitted event is written to PostgreSQL as it
  happens, before the next action is taken.
- All of it remains readable through the API after the API process, the
  orchestrator, or the agent container dies.
- The final execution report is generated from these persisted records,
  not from in-process memory.

On restart of the API or orchestrator, any run left in `RUNNING` whose
container is gone is transitioned to `FAILED` with reason
`interrupted`, and the transition is recorded. Section 6's lifecycle is
unchanged; no new state is added.

`POST /agents/{id}/restart` in the MVP starts a fresh run against the
same agent and objective. It reuses the persisted agent definition and
objective, and it does not continue the interrupted run's iteration
sequence.

Resumption is Phase 2 and is scoped there as: workspace reconstruction,
a re-entrant execution loop, an explicit safe-checkpoint boundary at
task completion, and `POST /agents/{id}/resume-run`.

Section 12 is amended to read as a Phase 2 requirement for the resume
sentence; the persistence list in section 12 applies to the MVP in full.

## Consequences

- The MVP can lose in-flight work on a crash: the run restarts from the
  beginning. This is acceptable because MVP runs are bounded by
  `max_iterations` and a timeout.
- The execution history of a failed run is preserved and inspectable,
  which is what debugging the MVP acceptance test needs.
- The execution loop does not need to be re-entrant in the MVP, removing
  the largest source of MVP complexity.
- Phase 2 resumption is additive: it reads records the MVP already
  writes, so no data model rewrite is expected.
