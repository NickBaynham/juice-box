# Review 0005: W2 declarative schemas implementation

Scope: commits `9d308be..2eb9f91`, thirteen commits, the whole of
workstream W2 as delivered by plan 0003.

Verdict: approve. Seven increments, each reviewed against its own brief as
it landed, then the workstream reviewed as a whole. Every finding was
repaired before this record was written; the repairs are named per finding.
The remaining items are minors carried into W3.

## Method

Plan 0003 was scanned before implementation rather than after, which is the
change of practice this workstream tested. The scan built a throwaway
project, wrote the models from the plan's own prose, and ran its test
bodies verbatim: four blockers and sixteen corrections, recorded in the
plan rather than applied silently. Reviews then ran per increment, and
verified by execution — loading the specification's examples, diffing test
bodies byte-for-byte, reproducing each claimed failure, and in two cases
proving a shipped test could not fail.

The result is visible in where defects were found. Increment 1 came back
with no findings at any severity, the first in this project. Every finding
after it was in the plan text rather than the implementation.

## Correctness

No blocker or major findings outstanding.

**Repaired, was a major.** The `success_criteria` emptiness test could not
fail. It emptied the list by deleting the item line, which YAML parses as
`None`, so the check failed as `list_type` whether or not `min_length=1`
was present. The review proved that asserting `list_type` would pass
against an implementation with no `min_length` at all — the test would have
caught nothing it was written to catch. Repaired in `e319aac`: it now
writes `success_criteria: []` explicitly, and was verified to fail when
`min_length=1` is removed.

**Repaired, was a major.** `load_objective`'s docstring, and its CHANGELOG
and FEATURES entries, claimed all three malformed document shapes report an
`("objective", ...)` `loc` prefix. Only the missing-key case does; a
top-level list and an empty document report `loc == ()`. W3 builds 422
bodies from `errors()` and would have been told it could assume a non-empty
`loc`. Repaired in `e319aac`.

**Repaired, was a major.** `skills` was `list[str]` while every other
identifier in the same module carried the name grammar. ADR-0007 makes a
skill name a filesystem directory lookup at agent creation, so `../../etc`
validated and W7 would have inherited the path-safety problem. Repaired in
`f4765df` after reproducing it.

**Repaired, was a major.** `Repository.url` accepted
`https://user:token@host/repo`. Specification section 17 requires secrets to
be referenced by name and never embedded, and a credential there would
reach the persisted definition, the clone command, and any log touching
either. Repaired in `1c24c7f` after reproducing it.

**Repaired, was a minor.** The memory and timeout grammars anchored with
`$`, which matches before a trailing newline, so a YAML block scalar
produced `4Gi\n` and validated. `goal` accepted a whitespace-only string
while its counterpart `system_prompt` stripped and rejected one. Both
repaired in `2eb9f91`.

Specification section 8's example validates end to end with zero rejected
keys, and section 9's likewise. Both example files are byte-identical to
the specification, verified by independent extraction and checksum — no
edit was needed to make either validate, which is the strongest form this
workstream's exit criterion could take.

## Simplicity

No findings. Ten models and two enums across two modules, each a plain
Pydantic class. One before-validator was added during increment 5 to
satisfy the broken test above and deleted with it; it had made
`success_criteria` the only one of nine collection fields across both
modules to treat a null as anything other than a type error.

## DRY

No findings. `NAME_PATTERN` and `SlugName` are defined once and reused for
`metadata.name`, `skills`, `secrets`, and `objective.id`.

## Size

No findings. `agent.py` is 190 lines, `objective.py` 77, `loading.py` 32.
Increment 4's reviewer judged a split unnecessary on the grounds that
increment 4 was the last to add classes, which held.

## Clarity

No findings. No emojis. Docstrings carry the reasoning that would otherwise
be lost — why `memory_bytes` is a property rather than a computed field,
why the envelope is a model rather than a subscript, why three approval
operations are inert.

## Tests

No findings outstanding. Every test body in the plan was used verbatim, and
each increment's reviewer diffed them byte-for-byte rather than reading
them. Two tests were proven unable to fail and repaired; the discipline
that caught them is the one carried from W1, where six such tests shipped.

`tests/unit/test_examples_validate.py` carries three tripwires, all proven
to fire: the two `assert paths` lines fail on an empty `examples/`
directory rather than passing vacuously, and the glob-coverage test fails
when a `stray.yaml` is added. Proven in a detached worktree.

## Minor findings carried into W3

1. `docs/schemas.md` documents the `by_alias` rule, and W3 must follow it:
   a bare `model_dump()` emits `api_version` while validation accepts only
   `apiVersion`, so a bare dump produces a document that cannot be loaded
   back. W3 persists these as JSONB and reads them back.
2. A document that is not a mapping reports `loc == ()`. W3's 422 body
   builder cannot assume a non-empty `loc`.
3. Specification section 8's example names skills `git, playwright,
   pytest, api-testing, code-analysis`; ADR-0007 ships `git`, `coding`,
   `testing`, and W12 adds `playwright-testing`. Once W7 lands, that
   example validates in W2 and is refused with a 422 in W3. Increment 6's
   reviewer recommends retiring the specification's list in favour of
   ADR-0007's, on the grounds that section 25's acceptance test needs none
   of the extras. W7 decides.
4. Three of the six approval operations are accepted and inert. ADR-0004's
   amendment and `docs/schemas.md` both carry the enforcement table naming
   them. W6 and W9 must name operations from `ApprovalOperation` when they
   enforce, or a configured gate never fires.

## Documents needing amendment

Carried from reviews 0003 and 0004, still outstanding. None block W2.
ADR-0004's amendment was written in increment 7 rather than added to this
queue, which is the practice the rest of these should follow.

- ADR-0001 states CI must provide a PostgreSQL service container. CI runs
  `make test`, which brings it up through Compose.
- Design 0002 workstream criterion 2 requires an acceptance suite that does
  not exist until W12. Criterion 3 requires the acceptance scenarios traced
  to a workstream to pass, and those scenarios are pytest tests in the same
  absent directory — so criterion 3 is unsatisfiable before W12 for the
  same reason. Two plans now exempt criterion 2 individually and this
  workstream had to exempt criterion 3 as well. The exemption belongs in
  design 0002.
- Design 0002 increment criterion 7 requires one commit per increment. It
  has been contradicted by a self-review correction four times now.
- ADR-0002's durability list includes every state transition. The schema
  stores current status only. W3 owns the state machine and should decide
  deliberately.
