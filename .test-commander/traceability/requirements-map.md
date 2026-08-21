# Requirements Traceability Map

Requirement -> workstream -> plan -> acceptance scenario. Derived
2026-08-14 from `requirements/requirements-inventory.md` and
`.dev-commander/design/0001-mvp-decomposition.md`.

Per ADR-0008, acceptance scenarios are pytest tests under
`tests/acceptance/` that drive the HTTP API. They run at workstream
boundaries, not per increment. The `Scenario` column names the Gherkin
scenario under `.test-commander/bdd/features/` that the test references;
scenarios are written by `/tc:generate-bdd` as each workstream is
planned.

| Workstream | Plan | Requirements | Acceptance scenario file |
|-----------|------|--------------|--------------------------|
| W0 Foundation | 0001 | none — infrastructure only | none |
| W1 Persistence | 0002 | MVP-10, AMD-01 | `state-durability.feature` (authored in W9) |
| W2 Schemas | 0003 | MVP-02, MVP-03 | `agent-definition.feature` |
| W3 Agents API | 0004 | MVP-01, MVP-02, MVP-03, MVP-11, MVP-12, MVP-13, AMD-06, AMD-07 | `agent-lifecycle.feature` |
| W4 Events and logging | 0005 | MVP-11 | `observability.feature` |
| W5 Tools | 0006 | MVP-06, MVP-07, MVP-08 | `tool-execution.feature` |
| W6 Workspace and runtime | 0007 | MVP-04, MVP-05, AMD-04 | `workspace-isolation.feature` |
| W7 Skills | 0008 | AMD-04, AMD-05 | `skill-loading.feature` |
| W8 Providers | 0009 | MVP-09 | `provider-contract.feature` |
| W9 Execution loop | 0010 | MVP-04, MVP-10, MVP-12, MVP-14, AMD-01, AMD-03 | `execution-loop.feature` |
| W10 Completion and reporting | 0011 | MVP-15, MVP-16 | `completion-and-report.feature` |
| W11 CLI | 0012 | AMD-02 | `cli-client.feature` |
| W12 Acceptance | 0013 | ACC-01 through ACC-12 | `end-to-end.feature` |

## Coverage check

Every requirement in the inventory is traced to at least one workstream.
No workstream other than W0 is without a requirement; W0 is
infrastructure and is verified by its own plan's exit criteria rather
than by an acceptance scenario.

Requirements traced to more than one workstream — MVP-02, MVP-03, MVP-04,
MVP-10, MVP-11, MVP-12, AMD-01, AMD-04 — are covered when the last of
their workstreams completes. The earlier workstream's acceptance scenario
asserts only its own part.

## Gaps

None open. Two items are deliberately untraced and recorded in the
inventory's open questions: ACC-05's dependence on a real model, and
secret handling beyond environment variables in specification section 17.

## W1 completion note

W1 completed on 2026-08-20. MVP-10 and AMD-01 both span W1 and W9, so
neither closes here: W1 delivers durable state — the seven entities,
their migrations, and the repository layer — and W9 delivers the
interrupted-run behaviour and authors `state-durability.feature` that
exercises both halves. Their inventory status stays `planned` until then.
