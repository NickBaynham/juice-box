# Review 0002: Consistency and feasibility of the plan set

Reviewed 2026-08-14. Scope: `docs/specs/juice-box-spec.md` sections 1-31,
designs 0001 and 0002, ADR-0001 through ADR-0006, plans 0001 and 0002.

Question asked: is the approach internally consistent, and is it
feasible as written.

## Verdict

Consistent after four repairs, three of which are recorded below as
required and one as accepted. Feasible, with two feasibility risks that
are real but bounded. One finding is significant enough to change the
workstream breakdown.

## Required repairs

### 1. The MVP accepts a `skills` field that nothing consumes — significant

Spec section 8 puts `skills` in the agent definition and section 14
describes a skills system, but design 0001's workstreams W0 through W11
contain no owner for it. Section 24's MVP list does not mention skills,
and section 26 defers a skill registry to Phase 2, so the omission looked
defensible. It is not.

Two things break. First, an agent definition would declare
`skills: [git, playwright, pytest]` and the MVP would silently ignore
it — the exact failure mode ADR-0004 was written to prevent. Second, the
section 25 acceptance test requires the agent to write and run Playwright
tests, and nothing would carry the instructions telling it how.

Repair: ADR-0007 defines skills for the MVP as filesystem-backed
instruction bundles loaded from the `skills/` directory that spec section
23 already reserves. A skill grants tools, injects instructions into the
system prompt, and declares required commands verified at container
start. An unknown skill name is a 422. Registry, versioning, and dynamic
loading stay in Phase 2.

Consequence: a new workstream. Design 0001 gains W7 Skills between W6
and the provider layer, and everything after it shifts by one. The set is
now thirteen workstreams, W0 through W12, and plans 0001 through 0013.

### 2. `restart` has no legal transition — required

ADR-0002 states that an interrupted run becomes `FAILED` and that
`POST /agents/{id}/restart` starts a fresh attempt. Spec section 6 draws
`FAILED`, `COMPLETED`, and `STOPPED` as terminal, with no arrow back.
W3's state machine would therefore refuse the very call ADR-0002
requires.

Repair: the W3 state machine permits `FAILED -> STARTING` and
`STOPPED -> STARTING`, and only those, as restart edges. `COMPLETED` stays
terminal. This is recorded in the W3 plan and added to the section 31
table rather than left for the implementer to discover.

### 3. `WAITING` is unreachable in the MVP — required, documentation only

ADR-0004 has approval-gated operations fail closed, so the MVP never
suspends into `WAITING`. Section 6 lists it as a state and section 7
lists an `approval` message type. Both are Phase 2 surfaces.

Repair: W3's state machine defines `WAITING` but the MVP has no
transition into it, and this is stated in `docs/api.md` rather than left
as an apparent gap. No code change.

## Accepted without repair

### 4. The end-to-end test proves plumbing, not agent quality

W12's automated acceptance test runs against the fake provider, which
replays a script. It cannot discover a coverage gap; it can only prove
that a discovered gap flows correctly through tasks, tools, commits, and
reporting.

Accepted. This is already named as a risk in design 0001, and the
mitigation — a manual Anthropic run in W12 — is the only real check.
Recorded here so no one later mistakes a green CI run for evidence that
the agent works.

## Feasibility

### Container-in-container is the binding constraint

The API runs in a container under Compose, and W8 has it launch sibling
agent containers. That requires mounting `/var/run/docker.sock` into the
`api` service, which plan 0001 increment 6 does not do. It is also the
decision most likely to force rework, because the same code must later
run on ECS/Fargate where no Docker socket exists.

Assessment: feasible for the MVP. Mounting the socket is two lines of
Compose. The rework risk is real but deferred by design — spec section 29
lists Kubernetes as a non-goal and section 26 puts Fargate in Phase 2.
The mitigation is that W8 must put container creation behind a runtime
interface with one Docker implementation, so a Fargate implementation is
additive.

Action: the W8 plan adds the socket mount to `docker-compose.yml` and
defines the runtime interface. Noted here because it changes a file plan
0001 already wrote.

### Test feedback loop will be slow

Plan 0001 increment 5 builds a container image inside an integration
test, W7 verifies skill command requirements inside a container, and
W12's agent image needs Python, Node, and Playwright browsers. That image
will be large and slow to build.

Assessment: feasible but needs discipline. `make test` stays unit-only,
integration tests stay behind the marker, and the agent image must be
built once and cached rather than rebuilt per test. If the W12 loop
exceeds a few minutes, cache the browser layer separately.

### Everything else checks out

- The dependency order in design 0001 has no cycles. Each workstream's
  inputs are produced by an earlier one.
- The interface list in design 0001 assigns every shared type exactly one
  owner. No workstream reaches into another's internals.
- ADR-0001's requirement that CI provide PostgreSQL is satisfied by plan
  0001 increment 7, because the ubuntu-latest runner supplies Docker and
  `make test` starts the service itself. No service container block is
  needed.
- ADR-0003's thin-CLI rule is enforceable: the W11 plan's tests point the
  CLI at a stubbed HTTP server, so any validation that leaked into the
  CLI would have to be tested there and would be visible in review.
- ADR-0005's fake provider makes W9 and W12 runnable offline, which is
  what keeps the acceptance loop fast enough to use.
- Plan 0002's model set covers every item spec section 12 requires to be
  persisted. Checked field by field.

## Actions taken

1. ADR-0007 written; design 0001 renumbered to thirteen workstreams with
   W7 Skills inserted; spec section 31 updated.
2. Restart transitions and the unreachable `WAITING` state recorded as
   section 31 entries and carried into the W3 plan.
3. The Docker socket mount and the runtime interface carried into the W8
   plan.
