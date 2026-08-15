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
