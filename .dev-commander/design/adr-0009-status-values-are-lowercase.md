# ADR-0009: Status and type values are stored lowercase across every entity

## Status

Accepted — 2026-08-20. Settles a casing split that W1 introduced across
increments 2 and 4, before W3's state machine and W4's API serialization
are built on top of it.

## Context

The specification is not internally consistent about how it renders
status values, and the two W1 increments that added status columns each
followed the section governing their own entity.

Section 6 renders the agent lifecycle as an ASCII state diagram in
uppercase: `CREATED`, `STARTING`, `RUNNING`, and so on. It contains no
JSON example, so it never shows an agent status as a wire value.
Increment 2 read this literally and stored `AgentStatus` and `RunStatus`
values in uppercase.

Section 11 renders the eight task states in lowercase, in both a prose
list and a literal JSON payload example that shows `"status": "running"`
and `"priority": "high"`. Increment 4 read that literally and stored
`TaskStatus` and `TaskPriority` values in lowercase.

Both readings were defensible in isolation. Together they left sibling
tables in one schema holding `'RUNNING'` for an agent and `'running'` for
a task. A review of increment 4 established that the evidence is not
symmetric: the lowercase choice is grounded in an actual wire-format
example, while the uppercase choice is extrapolated from a diagram that
never appears in an API payload context.

The sharp risk is silent rather than loud. An operator who learns the
agent convention and writes `WHERE status = 'RUNNING'` against `task`
gets zero rows and no error. A generic state-machine helper in W3 cannot
compare raw values uniformly across entities. W4 would expose both
casings on one API surface.

## Decision

Status and type column values are lowercase for every entity. Enum member
names remain uppercase Python identifiers, so `AgentStatus.RUNNING` has
the value `"running"`, matching the style `TaskStatus` already used.

`AgentStatus` and `RunStatus` were retrofitted rather than left alone,
because the alternative was to preserve the weaker reading of the spec
permanently in the schema. The retrofit shipped as a hand-written data
migration that lowercases existing rows and swaps the CHECK constraints,
so it is correct on a database holding data and not only on the empty one
it was developed against.

## Consequences

- One convention holds across the schema, so a hand-written query and a
  generic helper behave the same for every entity.
- The stored value is also the wire value. W4 can serialize a status
  directly without a casing translation layer, and an API consumer sees
  one convention across all resources.
- W3's state machine can compare values uniformly, and may share
  transition-validation logic across entities if it chooses to.
- The spec's section 6 diagram now differs in case from what the system
  stores. The diagram describes states, not payloads, so this is a
  rendering difference rather than a contradiction, but a reader
  comparing the two should know it is deliberate.
- Two shipped migrations were superseded rather than rewritten. The
  history reflects what happened, which is why the retrofit is a forward
  migration and not an edit to increments 2 and 4.
