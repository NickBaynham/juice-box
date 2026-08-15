# Requirements Inventory

Source: `docs/specs/juice-box-spec.md`, sections 24, 25, and 30, as
amended by section 31. Derived 2026-08-14.

Status values: `open` (no implementation started), `planned` (a plan
exists), `covered` (implemented and acceptance-tested).

## MVP capabilities — specification section 24

| ID | Requirement | Workstream | Status |
|----|-------------|-----------|--------|
| MVP-01 | Create an agent through the API | W3 | planned |
| MVP-02 | Pass an objective and specification | W2, W3 | planned |
| MVP-03 | Pass a Git repository URL | W2, W3 | planned |
| MVP-04 | Start an isolated agent runtime | W6, W9 | open |
| MVP-05 | Clone the repository into its workspace | W6 | open |
| MVP-06 | Agent can inspect and modify files | W5 | open |
| MVP-07 | Agent can execute shell commands | W5 | open |
| MVP-08 | Agent can perform Git operations | W5 | open |
| MVP-09 | Support at least one LLM provider | W8 | open |
| MVP-10 | Maintain task and execution state | W1, W9 | planned |
| MVP-11 | Expose status and logs | W3, W4 | open |
| MVP-12 | Accept messages while the agent is running | W3, W9 | open |
| MVP-13 | Stop and restart an agent | W3 | open |
| MVP-14 | Detect completion or failure | W9 | open |
| MVP-15 | Commit successful work to the repository | W10 | open |
| MVP-16 | Produce a final execution report | W10 | open |

## Derived from the amendments — specification section 31

| ID | Requirement | Workstream | Status |
|----|-------------|-----------|--------|
| AMD-01 | State survives process death; an interrupted run becomes FAILED with reason `interrupted` (ADR-0002) | W1, W9 | planned |
| AMD-02 | `juicebox run` and `juicebox status` work as a thin client over the API (ADR-0003) | W11 | open |
| AMD-03 | An approval-gated operation is refused, its task fails with `approval_required`, and `approval.requested` is emitted (ADR-0004) | W9 | open |
| AMD-04 | A `permissions` block is enforced at the container and tool boundary (ADR-0004) | W6, W7 | open |
| AMD-05 | An unknown skill name is rejected with 422; a missing required command fails the run before the first model call (ADR-0007) | W7 | open |
| AMD-06 | `GET /agents/{id}/status` returns a `current_run` object (ADR-0006) | W3 | open |
| AMD-07 | `FAILED -> STARTING` and `STOPPED -> STARTING` are legal; `COMPLETED` is terminal (review 0002) | W3 | open |

## Acceptance scenario — specification section 25

Each step is a numbered assertion in the end-to-end scenario. All are
owned by W12 and depend on every preceding workstream.

| ID | Step | Status |
|----|------|--------|
| ACC-01 | Juice Box starts | open |
| ACC-02 | Test Commander agent initializes | open |
| ACC-03 | Repository is cloned | open |
| ACC-04 | Existing tests are inspected | open |
| ACC-05 | Coverage gap is identified | open |
| ACC-06 | New Playwright test is generated | open |
| ACC-07 | Test suite executes | open |
| ACC-08 | Failures are diagnosed if necessary | open |
| ACC-09 | Test passes | open |
| ACC-10 | Changes are committed | open |
| ACC-11 | Execution report is produced | open |
| ACC-12 | Agent enters COMPLETED state | open |

## Open questions

- ACC-05 cannot be asserted against the fake provider, which replays a
  script rather than reasoning. The automated run proves the gap flows
  through the system; only the manual Anthropic run in W12 evidences that
  a gap is genuinely identified. Recorded in review 0002 as accepted.
- Specification section 17 leaves secret handling beyond environment
  variables unresolved for the MVP. No requirement is inventoried for it
  until an ADR settles the scope.
