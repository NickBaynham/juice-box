# ADR-0004: Approval-gated operations fail closed in the MVP

## Status

Accepted — 2026-08-14. Resolves the conflict between spec section 8
(agent definitions carry `execution.require_approval_for`), section 16
(dangerous operations require explicit approval), and section 26
(approval gates deferred to Phase 2).

## Context

The MVP agent definition in section 8 includes `permissions` and
`execution.require_approval_for`. Section 16 describes approval for
dangerous operations. Section 26 defers approval gates to Phase 2. An
MVP that parses `require_approval_for` and ignores it would silently
execute the exact operations an operator marked as requiring sign-off.
That is a safety defect, not a deferred feature: the field's presence
would create a false belief that a control is active.

The full approval round trip — pause into `WAITING`, emit
`approval.requested`, expose a decision endpoint, resume on approval — is
genuinely Phase 2 work, since it depends on the message and event
machinery and on resumption semantics.

Note that the operations named in section 8 and section 16 are mostly
outside the MVP anyway: pull-request creation is Phase 2 per section 26,
and production deployment is an explicit MVP non-goal in section 29.

## Decision

The MVP validates `permissions` and `execution.require_approval_for` and
enforces them by refusing the operation.

- Both fields are part of the MVP agent schema. Unknown values are
  rejected at `POST /agents` with a 422; the field is never silently
  dropped.
- Any operation named in `require_approval_for` is denied when attempted.
  The attempting task transitions to `failed` with reason
  `approval_required`, an `approval.requested` event is recorded, and the
  run continues with the remaining tasks. The operation is never
  performed.
- The `permissions` block is enforced at the container and tool boundary:
  `network: false` runs the container without network access,
  `shell: false` withholds the shell tool from the agent's tool set, and
  `filesystem: read-only` mounts the workspace read-only.

There is no approve or deny endpoint in the MVP. Granting approval means
editing the agent definition and starting a new run.

Phase 2 replaces refusal with suspension: the run enters `WAITING`,
`POST /agents/{id}/approvals/{approval_id}` accepts a decision, and the
run continues.

## Consequences

- The MVP fails closed. An operator who marks an operation as
  approval-gated gets a guarantee it will not run unattended.
- Cost is low, because the gated operations are largely unimplemented in
  the MVP.
- An agent whose objective genuinely requires a gated operation cannot
  complete it in the MVP. This is intended and visible in the failure
  reason rather than silent.
- The event name `approval.requested` from section 19 is emitted in the
  MVP, so Phase 2 adds a responder to an existing signal.

## Amended 2026-08-21

This decision requires `execution.require_approval_for` to reject an
unknown value with a 422 rather than silently drop it. Rejection needs an
enumeration, and the specification gives none. Workstream W2 defines one;
this amendment records it here rather than leaving it to live only in
plan `0003-declarative-schemas.md`, where the next workstream would not
find it.

### Deriving the six operations

The specification names approval-worthy operations in two places that
disagree with each other in both form and content, and neither is a
closed set on its own:

- Section 8's example uses two slugs directly in
  `execution.require_approval_for`: `production-deployment`, `merge`.
- Section 16 lists six prose phrases under an "Examples:" heading of
  operations that "can require explicit approval": `merge pull request`,
  `delete cloud resource`, `deploy production`, `modify secrets`,
  `force push`, `delete repository data`.

W2 defines `ApprovalOperation`, a closed `StrEnum`, as slugs derived from
section 16's six phrases, reconciled with section 8's two slugs where
they name the same operation (`deploy production` becomes
`production-deployment`, matching section 8's own spelling; `merge pull
request` becomes `merge`, likewise):

- `merge`
- `force-push`
- `repository-data-deletion` (from "delete repository data")
- `production-deployment` (from "deploy production")
- `cloud-resource-deletion` (from "delete cloud resource")
- `secret-modification` (from "modify secrets")

### Enforcement table

Three of the six operations have an MVP enforcement point; three do not,
because the tool layer that could attempt them does not exist in the
MVP.

| Operation | Enforced by | Status in the MVP |
| --- | --- | --- |
| `merge` | W9, git tool | Enforced |
| `force-push` | W9, git tool | Enforced |
| `repository-data-deletion` | W9, filesystem and git tools | Enforced |
| `production-deployment` | none | Accepted, inert — section 29 makes deployment a non-goal |
| `cloud-resource-deletion` | none | Accepted, inert — W5 ships no cloud tool |
| `secret-modification` | none | Accepted, inert — W5 ships no secret-mutation tool |

The inert rows are the point of this table, not a gap to excuse. This
ADR exists because a gate that looks active and is not gives false
confidence, and the specification's own example
(`examples/test-commander.agent.yaml`, copied verbatim from section 8)
declares `require_approval_for: [production-deployment, merge]`. Read
that example alone, and both operations look equally live. They are not:
`merge` is enforced by W9's git tool; `production-deployment` is accepted
by validation and then enforces nothing, because no tool in W5 can
attempt a production deployment and section 29 makes deployment an
explicit MVP non-goal. `cloud-resource-deletion` and
`secret-modification` are inert for the same reason — W5 ships shell,
filesystem, and git tools only.

Accepting the three inert operations rather than rejecting them is
still the right call: rejecting `production-deployment` would break
section 8's own example, and the schema's job is to validate the
document's shape, not to second-guess which operations happen to have a
tool behind them yet. The false-confidence risk this ADR names is
addressed by documentation, not by narrowing the enum — see
`docs/schemas.md#approval-operations`, which carries this same table and
is the page a reader consults before writing `require_approval_for:`.

### Consequences of this amendment

- W6 and W9, when they enforce, must name operations from exactly this
  six-value set, or a gate silently never fires.
- An operator who writes `production-deployment`,
  `cloud-resource-deletion`, or `secret-modification` into
  `require_approval_for` gets a document that validates and a gate that
  does nothing. This is now documented in two places
  (`docs/schemas.md` and here) rather than discoverable only by reading
  W9's source once it lands.
- This amendment does not change the Decision or Consequences sections
  above; it only closes the gap between "unknown values are rejected"
  and "here is the enumeration that makes rejection possible."
