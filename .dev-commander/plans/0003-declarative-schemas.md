# Plan 0003: W2 Declarative schemas

## Goal

Load and validate the agent definition of specification section 8 and the
objective of section 9 from YAML, so W3 can accept a document at
`POST /agents` and reject a malformed one with field-level errors rather
than a stack trace.

## Architecture

Pydantic v2 models in `src/juicebox/schemas/`, one module per document:
`agent.py` for the definition, `objective.py` for the objective, and
`loading.py` for the YAML entry points. Every model forbids unknown fields,
so a typo is an error rather than a silently dropped setting. The loaders
return validated models and let `pydantic.ValidationError` and
`yaml.YAMLError` propagate; W3 owns mapping them to 422. No model reaches
the database, the filesystem, or the network — this workstream is pure
parsing and validation.

## Tech Stack

Plan 0001's stack plus Pydantic 2.x and PyYAML.

## Global Constraints

- Definition of done: design 0002, with the same acceptance-suite
  exemption plan 0002 records: `pdm run pytest tests/acceptance` exits 4
  because that directory does not exist until W12. Close-out verifies
  `make lint test && make test-integration` instead. The same exemption
  covers criterion 3: it requires the acceptance scenarios traced to this
  workstream to pass, and those scenarios are pytest tests in the same
  absent directory. MVP-02 and MVP-03 both span W2 and W3 and close with
  the later one.
- Consumes ADR-0004 (approval gates fail closed) and ADR-0007 (skills are
  filesystem instruction bundles).
- Every model sets `model_config = ConfigDict(extra="forbid")`. ADR-0004
  requires that a field is never silently dropped, and a permissions or
  approval key lost to a typo is the failure that decision exists to
  prevent.
- Enum values are lowercase, per ADR-0009. Member names stay uppercase
  Python identifiers. The section 8 example already writes them lowercase.
- These are validation models, not persistence models. They import nothing
  from `juicebox.persistence` and nothing under `persistence/` imports
  them. W3 owns the translation between a validated definition and the
  `Agent` row.
- Tests here need no database, so they are unit tests under `tests/unit/`
  and run in `make test`. The only integration test is the one that reads
  the example files from disk.
- No emojis in code, output, or documentation.
- Requires W0 complete. W1 is not a dependency: nothing here touches the
  database.
- `make lint test` must pass before any increment is committed.

## Decisions this plan makes, which the specification leaves open

Recorded here because each changes what gets built, and two of them
contradict something already written down.

1. **`require_approval_for` needs a closed set, and the specification does
   not give one.** ADR-0004 states that unknown values are rejected with a
   422 and never silently dropped. Rejection is impossible without an
   enumeration. Section 8's example uses slugs (`production-deployment`,
   `merge`); section 16 lists prose phrases under an "Examples:" heading
   (`merge pull request`, `deploy production`, `modify secrets`,
   `force push`, `delete cloud resource`, `delete repository data`). The
   two lists disagree in both form and content, and neither is closed.

   This plan defines the canonical set as slugs derived from section 16,
   plus section 8's two: `merge`, `production-deployment`,
   `secret-modification`, `force-push`, `cloud-resource-deletion`,
   `repository-data-deletion`. W6 and W9 must name operations from exactly
   this set when they enforce, or the gate silently never fires.

   Three of the six have no MVP enforcement point: W5 ships shell,
   filesystem, and git tools only, so nothing can attempt a cloud-resource
   deletion or a secret modification, and section 29 makes production
   deployment an explicit non-goal. They are still accepted, because
   section 8's own example names `production-deployment` and increment 6
   ships that example verbatim. Accepting a slug that nothing checks is the
   false-confidence failure ADR-0004's context names, so increment 7
   documents each operation against its enforcement point and workstream,
   and marks the inert ones inert. Increment 7 also writes the amendment
   into ADR-0004 itself rather than deferring it: four amendments are
   already queued from earlier reviews, and a set living only in a plan is
   a set the next workstream will not find.

2. **`runtime.memory` and `runtime.timeout` are strings with units.** The
   specification writes `4Gi` and `8h` and defines neither grammar. They
   are validated against explicit patterns and parsed into bytes and a
   `timedelta`, so W6 can size a container without re-parsing. Rejecting
   `4GB` or `8 hours` at validation time is better than discovering it when
   a container fails to start.

3. **Skill names are validated as strings only.** ADR-0007 gives W7 the
   job of rejecting an unknown skill, and W7's exit criterion is exactly
   that. Validating existence here would duplicate it against a skill
   directory that does not exist yet.

4. **Both loaders validate through an envelope model, and raise.**
   `pydantic.ValidationError` already carries the field path, message, and
   type for every failure, which is what "field-level errors" means. W3
   maps it to a 422 body. Wrapping it in a project exception would discard
   that structure and add a layer with no caller.

   The objective document's `objective:` wrapper is unwrapped by a Pydantic
   model, not by subscripting the parsed mapping. `yaml.safe_load(text)
   ["objective"]` raises `KeyError` on a document missing the key and
   `TypeError` on a list or an empty document, and W3 maps neither to 422 —
   they would surface as 500s with a stack trace, which is the outcome this
   workstream exists to prevent. Because the envelope is a model, every
   error path inside an objective reports a `loc` beginning `("objective",
   ...)`, and the tests below assert that prefix.

   The same decision has a consequence W3 must know: because
   `populate_by_name` is deliberately absent, `AgentDefinition.model_dump()`
   emits `api_version` while validation accepts only `apiVersion`, so a
   bare dump does not round-trip. `model_dump(by_alias=True)` does.
   Increment 7 documents it. The alternative — adding `populate_by_name` —
   is worse: it would make a document written with `api_version:` validate
   silently, which is the trap the scan caught in increment 1.

## Increments

### 1. YAML loading and the document envelope

- [x] Load a YAML document and reject one that is not a Juice Box agent.

Files: `src/juicebox/schemas/__init__.py`,
`src/juicebox/schemas/agent.py`, `src/juicebox/schemas/loading.py`,
`tests/unit/test_schema_loading.py`, `pyproject.toml`

Failing test first — `tests/unit/test_schema_loading.py`:

```python
import pytest
import yaml
from pydantic import ValidationError

from juicebox.schemas.loading import load_agent_definition

MINIMAL = """
apiVersion: juicebox.ai/v1
kind: Agent
metadata:
  name: test-commander
agent:
  model:
    provider: anthropic
    model: claude-sonnet
  system_prompt: Be useful.
"""


def test_loads_a_minimal_definition():
    definition = load_agent_definition(MINIMAL)
    assert definition.metadata.name == "test-commander"


def test_rejects_a_wrong_api_version():
    document = MINIMAL.replace("juicebox.ai/v1", "juicebox.ai/v2")
    with pytest.raises(ValidationError) as caught:
        load_agent_definition(document)
    assert caught.value.errors()[0]["loc"] == ("apiVersion",)


def test_rejects_an_unknown_field():
    with pytest.raises(ValidationError) as caught:
        load_agent_definition(MINIMAL + "\nunexpected: value\n")
    assert caught.value.errors()[0]["loc"] == ("unexpected",)


def test_propagates_a_yaml_syntax_error():
    with pytest.raises(yaml.YAMLError):
        load_agent_definition("apiVersion: [unclosed\n")
```

Minimal implementation: in `agent.py`, a `Metadata` model whose `name`
matches `^[a-z0-9][a-z0-9-]*$` — W6 derives a work branch and a container
name from it, and `Test Commander / v2` is legal in neither — and an
`AgentDefinition` model with
`api_version: Literal["juicebox.ai/v1"] = Field(alias="apiVersion")`,
`kind: Literal["Agent"]`, `metadata: Metadata`, and `agent: AgentSpec`.
Set `model_config = ConfigDict(extra="forbid")`. Do NOT add
`populate_by_name=True`: it would also accept `api_version:` in the
document, so a file writing the wrong key validates silently. Without it
the alias `apiVersion` is the only accepted spelling and the Python
attribute is still `api_version`. `AgentSpec` at this increment holds only `model` and
`system_prompt`; increment 2 fills it in, and a placeholder is not
acceptable — define `ModelSpec` with `provider: str` and `model: str` now.

In `loading.py`, `load_agent_definition(document: str) -> AgentDefinition`
calling `yaml.safe_load` then `AgentDefinition.model_validate`. `safe_load`,
never `load`: a definition is untrusted input.

Add both dependencies with `pdm add pydantic pyyaml` and commit the
regenerated `pdm.lock` in the same commit. Editing `pyproject.toml` by hand
leaves the lock hash stale, `pdm lock --check` warns, and CI's `make
install` re-resolves against the network instead of the committed lock.
Both packages are already present transitively — pydantic through
pydantic-settings, PyYAML through uvicorn's standard extra — but a direct
import needs a direct dependency, or a change to either of those breaks
this one.

Verify: `make lint test`

Commit: `Add YAML loading and the agent document envelope`

### 2. Model, prompt, skills, and secrets

- [x] Validate the agent's model, system prompt, skill list, and the
      secrets it references by name.

Files: `src/juicebox/schemas/agent.py`,
`tests/unit/test_schema_agent.py`

`skills` and `secrets` are TOP-LEVEL keys of the document, siblings of
`metadata:` and `agent:`. Section 8 puts them there, and section 17 shows
`secrets` at the top level too. `agent:` holds only `model` and
`system_prompt`. These tests therefore build a whole document, not an
`AgentSpec`; with `extra="forbid"` an `AgentSpec` carrying `skills` raises
`extra_forbidden` rather than accepting it.

Failing test first — `tests/unit/test_schema_agent.py`:

```python
import pytest
from pydantic import ValidationError

from juicebox.schemas.loading import load_agent_definition

MINIMAL = """
apiVersion: juicebox.ai/v1
kind: Agent
metadata:
  name: test-commander
agent:
  model:
    provider: anthropic
    model: claude-sonnet
  system_prompt: Be useful.
"""


def test_accepts_skills_and_secrets():
    definition = load_agent_definition(
        MINIMAL + "skills:\n  - git\n  - playwright\nsecrets:\n  - github-token\n"
    )
    assert definition.skills == ["git", "playwright"]
    assert definition.secrets == ["github-token"]


def test_defaults_skills_and_secrets_to_empty():
    definition = load_agent_definition(MINIMAL)
    assert definition.skills == []
    assert definition.secrets == []


def test_rejects_an_empty_system_prompt():
    document = MINIMAL.replace("system_prompt: Be useful.", 'system_prompt: "  "')
    with pytest.raises(ValidationError) as caught:
        load_agent_definition(document)
    assert caught.value.errors()[0]["loc"] == ("agent", "system_prompt")


def test_rejects_a_secret_name_that_is_not_a_slug():
    with pytest.raises(ValidationError) as caught:
        load_agent_definition(MINIMAL + "secrets:\n  - Github_Token\n")
    assert caught.value.errors()[0]["loc"] == ("secrets", 0)
```

Minimal implementation: `AgentSpec` keeps `model: ModelSpec` and
`system_prompt: str`, with a field validator that strips the prompt and
rejects it when empty. On `AgentDefinition`, add
`skills: list[str] = []` and `secrets: list[SecretName] = []`, where
`SecretName = Annotated[str, StringConstraints(pattern=r"^[a-z0-9][a-z0-9-]*$")]`.

The constrained type matters: a `@field_validator` over the whole list
reports `loc == ("secrets",)`, without the index, so the asserted `loc`
above only holds for a per-item constraint. The same is true of
`require_approval_for` in increment 4, which gets its index from
`list[ApprovalOperation]`.

The pattern is a NAME grammar, not a credential detector. It admits
`github-token` and rejects `Github_Token`; it also admits `sk-ant-api03-xy9`,
which is credential-shaped and lowercase. Section 17 requires secrets to be
referenced by name and never embedded, and a name grammar is the part of
that which a schema can check. Detecting a leaked credential is the
gitleaks step CI already runs, not this model's job — do not grow the
pattern into a heuristic.

Verify: `make lint test`

Commit: `Add model, prompt, skill, and secret validation`

### 3. Runtime and permissions

- [x] Validate the runtime envelope and the permission block ADR-0004
      enforces.

Files: `src/juicebox/schemas/agent.py`,
`tests/unit/test_schema_runtime.py`

Failing test first — `tests/unit/test_schema_runtime.py`:

```python
from datetime import timedelta

import pytest
from pydantic import ValidationError

from juicebox.schemas.agent import FilesystemAccess, Permissions, Runtime


def test_parses_memory_and_timeout():
    runtime = Runtime.model_validate({"cpu": 2, "memory": "4Gi", "timeout": "8h"})
    assert runtime.memory_bytes == 4 * 1024**3
    assert runtime.timeout_delta == timedelta(hours=8)


@pytest.mark.parametrize("memory", ["4GB", "4 Gi", "Gi", "-1Gi"])
def test_rejects_malformed_memory(memory):
    with pytest.raises(ValidationError) as caught:
        Runtime.model_validate({"cpu": 2, "memory": memory, "timeout": "8h"})
    assert caught.value.errors()[0]["loc"] == ("memory",)


@pytest.mark.parametrize("timeout", ["8 hours", "8H", "h", "-1h"])
def test_rejects_malformed_timeout(timeout):
    with pytest.raises(ValidationError) as caught:
        Runtime.model_validate({"cpu": 2, "memory": "4Gi", "timeout": timeout})
    assert caught.value.errors()[0]["loc"] == ("timeout",)


def test_rejects_zero_cpu():
    with pytest.raises(ValidationError) as caught:
        Runtime.model_validate({"cpu": 0, "memory": "4Gi", "timeout": "8h"})
    assert caught.value.errors()[0]["loc"] == ("cpu",)


def test_permissions_default_to_least_privilege():
    permissions = Permissions.model_validate({})
    assert permissions.filesystem is FilesystemAccess.READ_ONLY
    assert permissions.network is False
    assert permissions.shell is False


def test_rejects_an_unknown_filesystem_mode():
    with pytest.raises(ValidationError) as caught:
        Permissions.model_validate({"filesystem": "read-write-execute"})
    assert caught.value.errors()[0]["loc"] == ("filesystem",)


def test_a_document_without_permissions_is_least_privileged():
    """The default must survive being wired onto the document.

    An implementer who writes `permissions: Permissions | None = None`
    hands W6 a None meaning unrestricted, which is the ADR-0004 failure.
    """
    definition = load_agent_definition(MINIMAL)
    assert definition.permissions.filesystem is FilesystemAccess.READ_ONLY
    assert definition.permissions.network is False
    assert definition.runtime is None
```

`MINIMAL` is the same document literal increment 2 uses; import
`load_agent_definition` alongside the models.

Minimal implementation: `FilesystemAccess(StrEnum)` with
`READ_ONLY = "read-only"` and `READ_WRITE = "read-write"`. `Permissions`
with `filesystem: FilesystemAccess = FilesystemAccess.READ_ONLY`,
`network: bool = False`, `shell: bool = False`. The defaults are least
privilege because an omitted block must not grant more than a present one;
the project constraint that agents run under least privilege is what
decides this, not convenience.

Wire `Runtime` and `Permissions` onto `AgentDefinition` in this increment:
`runtime: Runtime | None = None` and `permissions: Permissions =
Permissions()`. Without this the section 8 example fails at increment 6
with `extra_forbidden` on both blocks, and increment 6 forbids editing the
example to make it pass — the workstream dead-ends. `permissions` gets a
default instance rather than `None` so an omitted block is least privilege
rather than absent; `runtime` may be `None` because W6 supplies its own
container defaults.

`Runtime` with `cpu: float = Field(gt=0)`, `memory: str`, `timeout: str`,
plus `memory_bytes: int` and `timeout_delta: timedelta` as plain
`@property`. Not `@computed_field`: that puts them in `model_dump()`, and
under `extra="forbid"` the dumped document no longer re-validates, breaking
the round trip W3 needs when reading a definition back from JSONB. Validate
`memory` against `^(\d+)(Ki|Mi|Gi|Ti)$` and `timeout` against
`^(\d+)(s|m|h)$`, converting with explicit multiplier tables. Do not accept
a bare number for either: `memory: 4` is ambiguous and the specification
never writes it.

Verify: `make lint test`

Commit: `Add runtime and permission validation`

### 4. Repository and execution

- [x] Validate the repository coordinates and the execution limits,
      including the approval set ADR-0004 requires be closed.

Files: `src/juicebox/schemas/agent.py`,
`tests/unit/test_schema_execution.py`

Failing test first — `tests/unit/test_schema_execution.py`:

```python
import pytest
from pydantic import ValidationError

from juicebox.schemas.agent import ApprovalOperation, Execution, Repository


def test_accepts_a_repository():
    repository = Repository.model_validate(
        {"url": "https://github.com/example/application",
         "branch": "juicebox/test-commander"}
    )
    assert repository.branch == "juicebox/test-commander"


def test_rejects_a_non_https_repository_url():
    with pytest.raises(ValidationError) as caught:
        Repository.model_validate({"url": "git@github.com:example/application.git"})
    assert caught.value.errors()[0]["loc"] == ("url",)


def test_accepts_known_approval_operations():
    execution = Execution.model_validate(
        {"max_iterations": 100, "require_approval_for": ["merge", "force-push"]}
    )
    assert ApprovalOperation.MERGE in execution.require_approval_for


def test_rejects_an_unknown_approval_operation():
    with pytest.raises(ValidationError) as caught:
        Execution.model_validate(
            {"max_iterations": 100, "require_approval_for": ["rm -rf /"]}
        )
    assert caught.value.errors()[0]["loc"] == ("require_approval_for", 0)


def test_rejects_a_non_positive_iteration_limit():
    with pytest.raises(ValidationError) as caught:
        Execution.model_validate({"max_iterations": 0})
    assert caught.value.errors()[0]["loc"] == ("max_iterations",)
```

Minimal implementation: `ApprovalOperation(StrEnum)` holding exactly the
six slugs this plan's decision 1 names: `MERGE = "merge"`,
`PRODUCTION_DEPLOYMENT = "production-deployment"`,
`SECRET_MODIFICATION = "secret-modification"`,
`FORCE_PUSH = "force-push"`,
`CLOUD_RESOURCE_DELETION = "cloud-resource-deletion"`,
`REPOSITORY_DATA_DELETION = "repository-data-deletion"`.

`Repository` with `url: str = Field(pattern=r"^https://")` — use the field
pattern or a `@field_validator`, never a `@model_validator`, which reports
`loc == ()` and would fail the test above — plus a `@field_validator` that
rejects a URL carrying credentials, since `^https://` alone admits
`https://user:token@host/repo` and section 17 requires secrets to be
referenced by name and never embedded; and
`branch: str | None = None`. SSH URLs are rejected because W6 clones inside
a container with no agent key, so an SSH URL would fail at clone time with
a less useful message. `Execution` with
`max_iterations: int = Field(default=100, gt=0)` and
`require_approval_for: list[ApprovalOperation] = []`. Wire `Repository` and `Execution` onto `AgentDefinition`:
`repository: Repository | None = None` and `execution: Execution =
Execution()`, so `max_iterations` always has a value for W9 to enforce.

Verify: `make lint test`

Commit: `Add repository and execution validation`

### 5. Objective schema

- [x] Validate the objective of specification section 9.

Files: `src/juicebox/schemas/objective.py`,
`src/juicebox/schemas/loading.py`,
`tests/unit/test_schema_objective.py`

Failing test first — `tests/unit/test_schema_objective.py`:

```python
import pytest
from pydantic import ValidationError

from juicebox.schemas.loading import load_objective

MINIMAL = """
objective:
  id: improve-api-tests
  goal: Improve automated API test coverage.
  success_criteria:
    - critical API flows are tested
"""


def test_loads_a_minimal_objective():
    objective = load_objective(MINIMAL)
    assert objective.id == "improve-api-tests"
    assert objective.completion_action.commit is False


def test_rejects_an_objective_with_no_success_criteria():
    document = MINIMAL.replace(
        "  success_criteria:\n    - critical API flows are tested\n", ""
    )
    with pytest.raises(ValidationError) as caught:
        load_objective(document)
    assert caught.value.errors()[0]["loc"] == ("objective", "success_criteria")


def test_rejects_empty_success_criteria():
    document = MINIMAL.replace(
        "  success_criteria:\n    - critical API flows are tested\n",
        "  success_criteria: []\n",
    )
    with pytest.raises(ValidationError) as caught:
        load_objective(document)
    error = caught.value.errors()[0]
    assert error["loc"] == ("objective", "success_criteria")
    assert error["type"] == "too_short"


def test_rejects_an_id_that_is_not_a_slug():
    document = MINIMAL.replace("improve-api-tests", "Improve API Tests")
    with pytest.raises(ValidationError) as caught:
        load_objective(document)
    assert caught.value.errors()[0]["loc"] == ("objective", "id")


def test_pull_request_requires_push():
    document = MINIMAL + "  completion_action:\n    push: false\n    pull_request: true\n"
    with pytest.raises(ValidationError) as caught:
        load_objective(document)
    assert caught.value.errors()[0]["loc"] == ("objective", "completion_action")


def test_rejects_a_document_with_no_objective_key():
    with pytest.raises(ValidationError) as caught:
        load_objective("goal: do the thing\n")
    assert caught.value.errors()[0]["loc"] == ("objective",)
```

The two negative success-criteria tests are deliberately different: one
removes the key, which fails as `missing`, and one writes `[]`, which fails
as `too_short`. Without the second, an implementer who omits `min_length=1`
passes every test while accepting an objective that W9 can never complete.

The second must write `success_criteria: []` explicitly. Deleting the item
line instead leaves `success_criteria:` with no value, which YAML parses as
`None`, not `[]` — that fails as `list_type` whether or not `min_length=1`
is present, so the test would catch nothing. Proven during increment 5's
review.

Minimal implementation: `CompletionAction` with `commit: bool = False`,
`push: bool = False`, `pull_request: bool = False`, and a model validator
rejecting `pull_request` without `push`, and `push` without `commit` —
W10 pushes a branch it committed to, and the impossible combination is
better refused here than discovered at the end of a run. `Objective` with
`id: str` matching `^[a-z0-9][a-z0-9-]*$`, `goal: str` non-empty,
`context: dict[str, str] = {}`, `tasks: list[str] = []`,
`constraints: list[str] = []`, `success_criteria: list[str]` with
`min_length=1`, and `completion_action: CompletionAction = CompletionAction()`.

Success criteria are required and everything else optional because W9
detects completion against them; an objective without them can never
finish. `tasks` stays optional because section 10 has the agent decompose
the goal itself. `context` values must be strings; section 9's example only
uses strings, and increment 7 documents the restriction so a reader does
not write `version: 1.2` and get a type error.

`ObjectiveDocument` with `model_config = ConfigDict(extra="forbid")` and a
single `objective: Objective` field is what unwraps the document.
`load_objective(document: str) -> Objective` returns
`ObjectiveDocument.model_validate(yaml.safe_load(document)).objective`.
Subscripting the parsed mapping instead — `yaml.safe_load(document)
["objective"]` — raises `KeyError` on a missing key and `TypeError` on a
list or an empty document, and W3 maps neither to a 422. Every `loc` above
carries the `("objective", ...)` prefix because of the envelope.

Verify: `make lint test`

Commit: `Add objective schema`

### 6. Example documents

- [x] Ship the specification's own examples and prove they validate.

Files: `examples/test-commander.agent.yaml`,
`examples/full.agent.yaml`,
`examples/improve-api-tests.objective.yaml`,
`tests/unit/test_examples_validate.py`

This is a unit test, not an integration test. It parses YAML files and
touches no database, and `pyproject.toml` defines the `integration` marker
as "requires docker services". Placing it in `tests/integration/` would
also inherit that directory's autouse fixtures, which run `alembic upgrade
head` and truncate every table — a live PostgreSQL to check that a YAML
file parses. It would also drop the test proving W2's exit criterion out of
`make test`, the loop developers actually run.

Failing test first — `tests/unit/test_examples_validate.py`:

```python
from pathlib import Path

from juicebox.schemas.loading import load_agent_definition, load_objective

EXAMPLES = Path(__file__).resolve().parents[2] / "examples"


def test_every_agent_example_validates():
    paths = sorted(EXAMPLES.glob("*.agent.yaml"))
    assert paths, "no agent examples found"
    for path in paths:
        load_agent_definition(path.read_text())


def test_every_objective_example_validates():
    paths = sorted(EXAMPLES.glob("*.objective.yaml"))
    assert paths, "no objective examples found"
    for path in paths:
        load_objective(path.read_text())


def test_every_example_file_is_covered_by_a_glob():
    """A file named neither *.agent.yaml nor *.objective.yaml is checked by
    nothing, and the exit criterion claims every example validates."""
    covered = set(EXAMPLES.glob("*.agent.yaml")) | set(EXAMPLES.glob("*.objective.yaml"))
    assert set(EXAMPLES.glob("*.yaml")) == covered
```

`EXAMPLES` is absolute, so `tests/unit/conftest.py`'s autouse
`monkeypatch.chdir(tmp_path)` does not affect it.

The `assert paths` lines are load-bearing: without them the test passes on
an empty directory, which is the failure mode this workstream's exit
criterion cares about.

Minimal implementation: copy the section 8 and section 9 examples verbatim
into `test-commander.agent.yaml` and `improve-api-tests.objective.yaml`,
then change only what validation rejects, and record every such change in
the commit message. Add `full.agent.yaml` exercising every optional block —
`runtime`, `permissions`, `repository`, `execution`, `skills`, `secrets` —
which is what increment 7's documentation check needs, and which the glob
above then guards permanently.

Record in the commit message, and do not fix here: section 8's example
names skills `git, playwright, pytest, api-testing, code-analysis`, while
ADR-0007 ships exactly `git`, `coding`, and `testing`, and W12 adds
`playwright-testing`. Once W7 lands, this example validates in W2 and is
rejected with a 422 in W3. Either W7 renames its skills to match the
specification's example or W12 updates the example; W7 decides, knowing
this now rather than discovering it. If the specification's own example
does not validate, that is a finding about the schema or the specification,
not licence to edit the example until it passes — stop and report it.

Verify: `make lint test && make test-integration`

Commit: `Add example agent and objective documents`

### 7. Workstream close-out

- [x] Document the schemas, amend ADR-0004, and close out W2.

Files: `docs/schemas.md`, `.dev-commander/design/adr-0004-approval-gates-fail-closed-in-mvp.md`,
`README.md`, `CHANGELOG.md`, `FEATURES.md`, `TODO.md`

Failing test first: none applies. The executable check is that a reader can
write a valid agent definition from `docs/schemas.md` alone, without
opening `agent.py`. `examples/full.agent.yaml` from increment 6 is that
check, permanently: write it from the documentation, and increment 6's
glob keeps validating it on every run. A proof written and then deleted
guards nothing.

Minimal implementation: `docs/schemas.md` covering both documents field by
field with types, defaults, and closed value sets; that a definition must
be dumped with `model_dump(by_alias=True)` and never a bare `model_dump()`,
because `api_version` carries the alias `apiVersion` and deliberately has
no `populate_by_name`, so a bare dump produces a document that will not
re-validate — proven during increment 3's review, and a live trap for W3,
which persists these documents as JSONB and reads them back; the memory and timeout
grammars; the least-privilege permission defaults with the reason; that
`context` values must be strings; that `require_approval_for` is a list
that tolerates duplicates rather than a set; and that `secrets` entries are
names, checked as a name grammar and not as credential detection.

Include a table naming, for each approval operation, the workstream and
enforcement point that acts on it:

| Operation | Enforced by | Status in the MVP |
|---|---|---|
| `merge` | W9, git tool | Enforced |
| `force-push` | W9, git tool | Enforced |
| `repository-data-deletion` | W9, filesystem and git tools | Enforced |
| `production-deployment` | none | Accepted, inert — section 29 makes deployment a non-goal |
| `cloud-resource-deletion` | none | Accepted, inert — W5 ships no cloud tool |
| `secret-modification` | none | Accepted, inert — W5 ships no secret-mutation tool |

The inert rows are the point of the table. ADR-0004 exists because a gate
that looks active and is not gives false confidence, and three of the six
operations the schema accepts have nothing to enforce them in the MVP.
Anyone reading only `examples/test-commander.agent.yaml`, whose
`require_approval_for` is `[production-deployment, merge]`, would otherwise
believe both are live.

Amend ADR-0004 in this increment rather than recording that someone should:
append an "Amended 2026-08-21" section carrying the six operations, the
derivation from sections 8 and 16, and the enforcement table above. Four
document amendments are already queued unserviced from earlier reviews, and
this plan's own argument is that a set living only in a plan is one the
next workstream will not find.

Link `docs/schemas.md` from README. Update CHANGELOG, FEATURES, and TODO.
The controller runs `/dc:review` and `/dc:journal`; they are not available
to an implementer.

Verify: `make lint test && make test-integration`

Commit: `Document the declarative schemas and close out W2`

## Exit Criteria

Design 0002's workstream criteria, less the acceptance-test criterion
exempted above, plus design 0001's W2 exit: every file under `examples/`
validates, and a malformed document is rejected with an error naming the
field that failed.

## Corrections to this plan

Recorded after a pre-flight scan and before implementation, in the same
form plan 0002 used. The scan built a throwaway project, wrote the models
to this plan's own prose, and ran its test bodies verbatim: four blockers,
of which the first three would have been found only during implementation
and the fourth only in W3.

1. Increment 2 tested `skills` and `secrets` on `AgentSpec` while its own
   note said they belong on `AgentDefinition`, and told the implementer to
   settle it. Section 8 puts both at the top level. Three of the four tests
   failed as written. The note is deleted and the tests target the document.
2. The secrets test asserted `loc == ("secrets", 0)`, which a
   `@field_validator` over the list cannot produce — it reports
   `("secrets",)`. Only a per-item constrained type gives the index.
3. No increment wired `runtime` or `permissions` onto `AgentDefinition`,
   so section 8's example was rejected with `extra_forbidden` on both, and
   increment 6 forbids editing the example to make it pass. The workstream
   would have dead-ended at its own exit criterion.
4. `load_objective` unwrapped the document by subscripting the parsed
   mapping, which raises `KeyError` or `TypeError` on three ordinary
   malformed inputs. W3 maps neither to 422, so the plan's stated goal —
   field-level errors rather than a stack trace — failed for exactly the
   documents it was written to catch. An envelope model fixes it and
   changes every asserted `loc` in increment 5.
5. `populate_by_name=True` would have accepted `api_version:` as well as
   the specification's `apiVersion:`, so a document with the wrong key
   validated silently.
6. `memory_bytes` and `timeout_delta` as `@computed_field` would appear in
   `model_dump()` and, under `extra="forbid"`, make the dumped document
   fail to re-validate — breaking W3's read path out of JSONB.
7. The examples test was marked `integration`, which the project defines as
   "requires docker services". It would have inherited the migration and
   truncation fixtures, needing a live database to parse a YAML file, and
   dropped the only proof of W2's exit criterion out of `make test`.
8. `test_rejects_a_secret_that_looks_like_a_value` passed only because its
   fixture had an uppercase letter; the pattern admits lowercase
   credential-shaped strings. Renamed to what it actually checks, and the
   rationale corrected.
9. `min_length=1` on `success_criteria` was enforced by no test: the only
   negative case removed the key, failing as `missing`. An empty-list test
   was added.
10. The `url` check said "validated to start with `https://`" without
    naming a mechanism; a `@model_validator` reports `loc == ()` and would
    have failed the test.
11. Increment 1 edited `pyproject.toml` by hand, leaving `pdm.lock` stale
    so CI re-resolves against the network instead of the lock.
12. Increment 7's documentation check wrote a definition and deleted it.
    A deleted proof guards nothing; it is now `examples/full.agent.yaml`,
    covered by increment 6's glob.
13. The ADR-0004 amendment was deferred to the controller. Four such
    amendments are already queued unserviced, so increment 7 writes it.
14. Three of the six approval operations have no MVP enforcement point,
    and one of them appears in the example this plan ships. Increment 7 now
    documents each against its enforcement point and marks the inert ones.
15. `metadata.name` had only `min_length=1` while `objective.id` had a slug
    pattern, though W6 derives a branch and container name from it.
16. Smaller gaps closed: no malformed-`timeout` cases to match the
    malformed-`memory` ones; no test that an omitted `permissions` block
    still yields least privilege once wired; no assertion that every
    `.yaml` under `examples/` is covered by a glob; `context` string-only
    values undocumented; duplicate approval operations undocumented; the
    W0-only dependency unstated.
