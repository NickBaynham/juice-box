# Declarative schemas

The YAML document formats workstream W2 delivers: the agent definition of
specification [section 8](specs/juice-box-spec.md#8-agent-definition) and
the objective of
[section 9](specs/juice-box-spec.md#9-objective-specification). A reader
should be able to write a valid document of either kind from this page
alone, without opening `agent.py` or `objective.py`.

Every model in `juicebox.schemas` sets `model_config =
ConfigDict(extra="forbid")`: an unknown key is a validation error, not a
silently dropped setting. Every enum value is lowercase, per
[ADR-0009](../.dev-commander/design/adr-0009-status-values-are-lowercase.md);
enum member names stay uppercase Python identifiers.

## Loading

`juicebox.schemas.loading` exposes two entry points:

```python
from juicebox.schemas.loading import load_agent_definition, load_objective

definition = load_agent_definition(yaml_text)   # -> AgentDefinition
objective = load_objective(yaml_text)           # -> Objective
```

Both parse with `yaml.safe_load` and validate through a Pydantic model.
Malformed YAML raises `yaml.YAMLError`; a document that parses but fails
validation raises `pydantic.ValidationError`. Neither loader catches
either exception — both propagate to the caller, which is W3, mapping
them to a `422` response.

`load_objective` validates through `ObjectiveDocument`, which unwraps the
top-level `objective:` key as a model field rather than a dict subscript.
That is what turns a document missing the key, or one that is a
top-level list or empty, into a `pydantic.ValidationError` instead of a
`KeyError` or `TypeError` — neither of which a caller could map to a 422.

### The error-location contract

A `pydantic.ValidationError` carries a `loc` tuple locating each failure.
Because `ObjectiveDocument` wraps `Objective` under an `objective` field,
every error inside a valid objective mapping carries a `loc` beginning
`("objective", ...)` — for example `("objective", "success_criteria")`.
A document that is not a mapping at all (a top-level list, a bare
string, `null`) fails before that field is even reached, and reports
`loc == ()`. A caller building a 422 body from `loc` cannot assume it is
non-empty.

### The `by_alias` rule

`AgentDefinition.api_version` carries the alias `apiVersion` and no
`populate_by_name`, deliberately. A document must be re-dumped with
`model_dump(by_alias=True)`, never a bare `model_dump()`:

```python
definition.model_dump(by_alias=True)   # {"apiVersion": "juicebox.ai/v1", ...}
definition.model_dump()                # {"api_version": ...} -- will not re-validate
```

A bare dump writes `api_version` instead of `apiVersion`, and because
`populate_by_name` is absent, that document fails validation on the next
read. This is deliberate, not an oversight: adding `populate_by_name`
would make a document written with `api_version:` validate silently,
which is the trap increment 3's review caught — silent acceptance of a
key the specification never names. W3 persists validated definitions as
`JSONB` and reads them back through the same model; it must always dump
`by_alias=True`.

## Agent definition

`load_agent_definition` validates an `AgentDefinition`.

| Field | Type | Default | Notes |
| --- | --- | --- | --- |
| `apiVersion` | `Literal["juicebox.ai/v1"]` | required | Python attribute `api_version`. See [the `by_alias` rule](#the-by_alias-rule). |
| `kind` | `Literal["Agent"]` | required | |
| `metadata.name` | `str` | required | Must match [the name grammar](#name-grammar). W6 derives a work branch and container name from it directly. |
| `agent.model.provider` | `str` | required | |
| `agent.model.model` | `str` | required | |
| `agent.system_prompt` | `str` | required | Stripped of leading/trailing whitespace; rejected if empty or all whitespace after stripping. |
| `skills` | `list[str]` | `[]` | Each entry must match the name grammar. Existence against a skill directory is W7's job, not validated here (ADR-0007). |
| `secrets` | `list[str]` | `[]` | Each entry must match the name grammar. See [Secrets and skills are names, not credentials](#secrets-and-skills-are-names-not-credentials). |
| `runtime` | `Runtime \| null` | `null` | Optional block; see below. |
| `permissions` | `Permissions` | least privilege | Always present — never `null`. See [Permission defaults](#permission-defaults). |
| `repository` | `Repository \| null` | `null` | Optional block; see below. |
| `execution` | `Execution` | `max_iterations: 100, require_approval_for: []` | Always present. |

### `runtime`

| Field | Type | Default | Notes |
| --- | --- | --- | --- |
| `cpu` | `float` | required | Must be greater than `0`. |
| `memory` | `str` | required | Must match `^(\d+)(Ki\|Mi\|Gi\|Ti)$`, e.g. `4Gi`. A bare number (`memory: 4`) is rejected — the specification never writes one, and the unit is not inferable. |
| `timeout` | `str` | required | Must match `^(\d+)(s\|m\|h)$`, e.g. `8h`. A bare number (`timeout: 28800`) is rejected for the same reason. |

`Runtime.memory_bytes` (`int`) and `Runtime.timeout_delta` (`timedelta`)
are plain `@property`, not `@computed_field`. A `@computed_field` would
appear in `model_dump()`, and under `extra="forbid"` the dumped document
would carry a key nothing accepts on the way back in, breaking the round
trip described in [the `by_alias` rule](#the-by_alias-rule). Compute
these from `memory` and `timeout` on demand instead of dumping them.

### `permissions`

| Field | Type | Default | Notes |
| --- | --- | --- | --- |
| `filesystem` | `"read-only" \| "read-write"` | `"read-only"` | |
| `network` | `bool` | `false` | |
| `shell` | `bool` | `false` | |

#### Permission defaults

All three defaults are the least-privileged option, and `permissions`
itself defaults to a full instance of those defaults rather than `null`.
This is ADR-0004's requirement made concrete: an agent definition that
omits `permissions:` entirely must never be granted more access than one
that spells every field out explicitly. If the field could default to
`null`, an omitted block would need special-casing at every enforcement
point (the container boundary, the tool set) to mean "least privilege" —
and a single site that forgets the special case grants shell, network,
and read-write filesystem access to a definition that asked for nothing.
A default *instance* makes that special-casing unnecessary: `permissions`
is never absent on a validated `AgentDefinition`.

### `repository`

| Field | Type | Default | Notes |
| --- | --- | --- | --- |
| `url` | `str` | required | Must match `^https://`. Must not embed credentials (`https://user:token@host/...` is rejected) — see specification [section 17](specs/juice-box-spec.md#17-secrets). Reference a secret by name instead. |
| `branch` | `str \| null` | `null` | |

`url` is restricted to `https://` rather than `ssh://` or `git@` because
W6 clones inside a container with no agent key; an SSH URL would only
fail later, at clone time, with a less useful error.

### `execution`

| Field | Type | Default | Notes |
| --- | --- | --- | --- |
| `max_iterations` | `int` | `100` | Must be greater than `0`. |
| `require_approval_for` | `list[ApprovalOperation]` | `[]` | A list, not a set — duplicate entries are accepted and preserved, not deduplicated. See [Approval operations](#approval-operations). |

### Name grammar

`metadata.name`, each `skills` entry, and each `secrets` entry all match
`^[a-z0-9][a-z0-9-]*$`: lowercase alphanumerics and hyphens, starting
with an alphanumeric.

### Secrets and skills are names, not credentials

The name grammar checks that a `secrets` or `skills` entry looks like an
identifier — something a later stage resolves (a secret becomes a
backend lookup; a skill becomes a directory lookup in W7). It is not a
credential scanner. A string that happens to look like a token but also
matches `^[a-z0-9][a-z0-9-]*$` (all lowercase, no symbols) passes this
check, because the check has nothing to do with what the string
contains — only that it is shaped like a name. Detecting a credential
that leaked into a document is a different problem, already solved by
the `gitleaks` step CI runs on every push.

## Objective document

`load_objective` validates an `ObjectiveDocument` and returns its
unwrapped `objective` field, an `Objective`. The document on disk carries
a top-level `objective:` key; the returned model does not repeat it.

| Field | Type | Default | Notes |
| --- | --- | --- | --- |
| `id` | `str` | required | Must match [the name grammar](#name-grammar). |
| `goal` | `str` | required | Must be non-empty (`min_length=1`). |
| `context` | `dict[str, str]` | `{}` | Values must be strings. `version: 1.2` or `retries: 3` are rejected — quote them (`version: "1.2"`) if the objective needs to carry them. |
| `tasks` | `list[str]` | `[]` | Optional: section 10 has the agent decompose its own goal when this is empty. |
| `constraints` | `list[str]` | `[]` | |
| `success_criteria` | `list[str]` | required, non-empty | W9 detects completion against this list; an objective with none can never finish. |
| `completion_action` | `CompletionAction` | all fields `false` | See below. |

### `completion_action`

| Field | Type | Default | Notes |
| --- | --- | --- | --- |
| `commit` | `bool` | `false` | |
| `push` | `bool` | `false` | Requires `commit: true`. |
| `pull_request` | `bool` | `false` | Requires `push: true` (and therefore `commit: true`). |

`push: true` with `commit: false`, or `pull_request: true` with
`push: false`, are both rejected: W10 pushes a branch it committed to,
and opens a pull request from a branch it pushed. The combination is
refused at validation time rather than discovered partway through a run.

## Approval operations

`ApprovalOperation` is the closed set of values `execution.require_approval_for`
accepts. The specification does not define one directly: section 8's
example uses two slugs (`production-deployment`, `merge`); section 16
lists six prose phrases under an "Examples:" heading (`merge pull
request`, `delete cloud resource`, `deploy production`, `modify
secrets`, `force push`, `delete repository data`). Neither list is
closed, and the two disagree in both form and content. ADR-0004 requires
that an unknown approval operation be rejected with a 422, which is
impossible without an enumeration, so this workstream defines the
canonical set as slugs derived from section 16's six phrases plus
section 8's own two overlapping slugs, for six total:

| Operation | Enforced by | Status in the MVP |
| --- | --- | --- |
| `merge` | W9, git tool | Enforced |
| `force-push` | W9, git tool | Enforced |
| `repository-data-deletion` | W9, filesystem and git tools | Enforced |
| `production-deployment` | none | Accepted, inert — section 29 makes deployment a non-goal |
| `cloud-resource-deletion` | none | Accepted, inert — W5 ships no cloud tool |
| `secret-modification` | none | Accepted, inert — W5 ships no secret-mutation tool |

The inert rows are the point of the table, not an incompleteness to
apologize for. ADR-0004 exists because a gate that looks active and is
not gives false confidence, and the specification's own example
(`examples/test-commander.agent.yaml`) declares
`require_approval_for: [production-deployment, merge]` — one of those two
can never fire in the MVP, because nothing in W5's tool layer can attempt
a production deployment. A reader of that example alone would reasonably
believe both operations are enforced; they are not. See the
[ADR-0004 amendment](../.dev-commander/design/adr-0004-approval-gates-fail-closed-in-mvp.md#amended-2026-08-21)
for the full derivation and rationale.

## A recorded conflict: section 8's skill names versus ADR-0007

Specification section 8's own example names five skills: `git`,
`playwright`, `pytest`, `api-testing`, `code-analysis`. ADR-0007 commits
the MVP to shipping three: `git`, `coding`, `testing`, and W12 adds a
fourth, `playwright-testing`. None of section 8's `playwright`, `pytest`,
`api-testing`, or `code-analysis` will exist as a skill directory.

`examples/test-commander.agent.yaml`, section 8's example copied
verbatim, therefore validates in W2 (skill existence is not checked
here — ADR-0007 gives that job to W7) but will be rejected with a `422`
once W3 enforces skill existence against the directories W7 creates.
This is recorded, not resolved, here: increment 6's review recommends
updating the specification's example to ADR-0007's skill set rather than
building four more skill bundles to match the specification, on the
grounds that the [section 25](specs/juice-box-spec.md#25-mvp-acceptance-test)
acceptance test needs none of the extra four. Amending the specification
is not a call this workstream makes; it is W7's to make when it lands.
