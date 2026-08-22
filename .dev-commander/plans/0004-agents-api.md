# Plan 0004: W3 Agents API and lifecycle

## Goal

Expose the specification section 21 agent and lifecycle routes over HTTP,
persist a validated definition and objective as an agent, and enforce the
section 6 state machine so an illegal transition is refused rather than
performed.

## Architecture

Routers under `src/juicebox/api/`, one module per resource, mounted by the
existing `create_app()` factory. A pure state machine in
`src/juicebox/lifecycle/` owns the legal transitions and knows nothing
about HTTP or the database. Routes translate: they parse a body with
`yaml.safe_load_all` and validate the parsed mappings with
`AgentDefinition.model_validate` and `ObjectiveDocument.model_validate`,
ask the state machine whether a transition is legal, and call W1's
repositories through a session dependency. W2's `load_agent_definition` and
`load_objective` take a string and are not usable on this path, which holds
already-parsed documents. No route issues a query
itself, which `tests/unit/test_query_locality.py` already enforces.

## Tech Stack

Plan 0001's stack. No new dependencies: FastAPI, Pydantic, SQLAlchemy,
and PyYAML are already present.

## Global Constraints

- Definition of done: design 0002. Increment 7 amends its workstream
  criteria 2 and 3 to be conditional on `tests/acceptance/` existing, which
  it does not until W12. This is the third plan that would otherwise repeat
  that exemption, and review 0005 said to fix the document rather than
  repeat it again. Close-out verifies
  `make lint test && make test-integration`.
- Consumes ADR-0002 (an interrupted run is `FAILED`; restart starts a fresh
  attempt), ADR-0003 (the CLI is a thin client with no logic of its own),
  ADR-0004 (approval gates fail closed, so the MVP never suspends),
  ADR-0006 (the agent id is the caller's handle; runs are numbered
  attempts), ADR-0009 (status values are lowercase).
- Status values are lowercase everywhere, including in JSON responses.
  `AgentStatus.RUNNING` serialises as `"running"`.
- A definition is persisted with `model_dump(by_alias=True)`, never a bare
  `model_dump()`. `api_version` carries the alias `apiVersion` and
  deliberately has no `populate_by_name`, so a bare dump produces a
  document that cannot be loaded back. `docs/schemas.md` records this and
  W2's review proved it.
- A `pydantic.ValidationError` becomes a 422 whose body carries the field
  path, message, and type of every error. A `yaml.YAMLError` becomes a 422
  as well. Neither becomes a 500.
- A caller building that 422 body must not assume a non-empty `loc`: a
  document that is not a mapping reports `loc == ()`. W2's review proved
  this too.
- Routes take an `AsyncSession` from a FastAPI dependency and never open
  their own. The repository layer remains the only module issuing queries.
- Tests that need a database are integration tests; everything else is a
  unit test. The state machine is pure and its tests are unit tests.
- No emojis in code, output, or documentation.
- `make lint test` must pass before any increment is committed.
- The path parameter is spelled `{agent_id}` in every route decorator.
  Sections 21 and 6 write `{id}` as prose; FastAPI derives the OpenAPI path
  literally from the decorator, so the spelling is normative here and
  increment 7's OpenAPI assertion depends on it.
- Integration tests drive the app through `httpx.ASGITransport`, never
  `starlette.testclient.TestClient`. TestClient runs the app on its own
  event loop in a portal thread, while this project's engine is
  deliberately `NullPool`'d because of per-test loops.
  `tests/unit/test_health.py` is the existing precedent.
- Requires W1 and W2 complete.

## Decisions this plan makes, which the specification leaves open

Recorded because each changes what gets built, and four of them resolve a
contradiction rather than filling a gap.

1. **`GET /agents/{id}/status` is not in section 21's endpoint list.**
   Section 6 lists it among the lifecycle operations and ADR-0006 requires
   it to return a `current_run` object, but section 21 — the API list W3's
   exit criterion names — omits it entirely. It is built, because two
   sources require it and only an omission argues against it, and increment
   7 adds it to section 21 rather than leaving the list wrong.

2. **"The six lifecycle endpoints" is a miscount.** Design 0001's W3 entry
   says six; section 21's Lifecycle block lists five: `start`, `stop`,
   `restart`, `pause`, `resume`. Section 6 lists those five plus
   `POST /agents`, which is six but includes creation, and separately lists
   `GET /agents/{id}` and `GET /agents/{id}/status`. This plan builds the
   five transitions, creation, retrieval, listing, deletion, and status —
   nine routes — and increment 7 corrects design 0001's count.

3. **`POST /agents` takes both documents as one multi-document YAML body.**
   An agent is bound to one objective per ADR-0006, so both are required at
   creation. The body is a YAML stream of exactly two documents separated
   by `---`: the section 8 definition, then the section 9 objective. This
   is what `cat agent.yaml objective.yaml` produces and `yaml.safe_load_all`
   parses it. Each document may individually be written in JSON syntax,
   since JSON is a subset of YAML, but a single JSON body cannot express two
   documents: the `---` separator is not JSON. Exactly two documents are
   required; one or three is a 422.

   A raw-text body carries no `requestBody` schema in OpenAPI. W3's exit
   criterion is that OpenAPI covers the section 21 routes, and W11's CLI has
   nothing to generate against, so increment 7 documents the body in prose
   with a worked example of the exact bytes.

4. **The definition is not resolved by name server-side.** Section 30's CLI
   is `juicebox run --agent test-commander --repo <url> --spec
   objective.yaml`, which passes a name rather than a document, implying a
   server-side registry of definitions. No such registry exists in any
   workstream, and ADR-0003 forbids the CLI from having logic of its own.
   This plan keeps the API the source of truth: the caller sends the
   documents. `--agent test-commander` is not the hard half — reading a
   local file of that name and posting its bytes is transport, not logic,
   and stays inside ADR-0003.

   `--repo <url>` is the hard half, because honouring it means mutating a
   validated document before sending it, which is the logic ADR-0003
   forbids. Three exits exist: drop `--repo`, since `repository.url` already
   lives in the definition and `examples/test-commander.agent.yaml` carries
   one; add a `repository_url` override parameter to `POST /agents`; or have
   the CLI rewrite the document. Increment 7 records the first as the
   default and the second as the fallback, and rejects the third. W11
   decides, with the options already weighed.

5. **`start` transitions state and creates a run attempt; it executes
   nothing.** The execution loop is W9 and the container runtime is W6.
   After `POST /agents/{id}/start` an agent is `starting` with a run at
   attempt 1, and nothing advances it further until W9 exists. This is
   honest rather than a stub: the state and the run record are exactly what
   the endpoint owns. Increment 7 says so in `docs/api.md`, so a reader
   does not conclude the loop is broken.

   This decision is why `starting` needs an exit. Nothing advances an agent
   out of `starting` until W9, so without a `STARTING -> STOPPED` edge every
   started agent would be unstoppable for six workstreams, removable only by
   `DELETE`. Increment 3 adds that edge and increment 7 records it in
   section 31.

6. **The state machine covers caller-initiated transitions only.** Section 6
   also requires `STARTING -> RUNNING`, `RUNNING -> COMPLETED`, and
   `RUNNING -> FAILED`, and ADR-0002 requires `RUNNING -> FAILED` with
   reason `interrupted` when the orchestrator restarts. None of these has a
   caller action, so W9 performs them. `next_status(current, action)` is
   keyed on `LifecycleAction` and cannot express them; increment 3 therefore
   also exposes `is_legal(current, target)` over the full section 6 edge
   set, so W9 has one place to ask rather than calling `set_status`
   directly and bypassing the machine that design 0001 makes W3's to own.

7. **Recording each state transition is deferred to W4, and ADR-0002 is
   amended to say so.** ADR-0002 requires every transition written to
   PostgreSQL as it happens; the schema stores current status only. Reviews
   0004 and 0005 both assigned this question to W3. The answer is that W4's
   event bus is the transition record — section 19 already defines
   `agent.started`, `agent.paused`, `agent.resumed`, `agent.completed`, and
   `agent.failed`, and `event` rows are append-only and carry both
   `agent_id` and `run_id`. Adding a second history table here would
   duplicate it. Increment 7 amends ADR-0002 rather than leaving the
   requirement unmet and unmentioned for a third workstream.

## Increments

### 1. Router package, agent creation, and the validation error contract

- [x] Create an agent from a definition and objective, and reject a
      malformed document with field-level errors.

Files: `src/juicebox/api/agents.py`, `src/juicebox/api/dependencies.py`,
`src/juicebox/api/errors.py`, `src/juicebox/api/__init__.py`,
`src/juicebox/app.py`, `tests/integration/conftest.py`,
`tests/unit/test_api_errors.py`,
`tests/integration/test_api_agents_create.py`

`src/juicebox/api/` already exists and holds `health.py`; its `__init__.py`
re-exports `health_router` and must re-export the new router the same way.
`tests/integration/conftest.py` also already exists, with the schema and
truncation fixtures; add an async `client` fixture to it built on
`httpx.ASGITransport(app=create_app())` and `httpx.AsyncClient`, which
every integration test below uses.

Failing test first — the unit test, which needs no database:

```python
import pytest
import yaml
from pydantic import ValidationError

from juicebox.api.errors import validation_error_detail
from juicebox.schemas.loading import load_agent_definition


def test_detail_carries_the_field_path():
    with pytest.raises(ValidationError) as caught:
        load_agent_definition("apiVersion: juicebox.ai/v2\nkind: Agent\n")
    detail = validation_error_detail(caught.value)
    assert detail[0]["loc"] == ["apiVersion"]
    assert "type" in detail[0] and "msg" in detail[0]


def test_detail_survives_an_empty_loc():
    """A document that is not a mapping reports loc == (); the body must
    still be JSON-serialisable and must not assume a field name."""
    with pytest.raises(ValidationError) as caught:
        load_agent_definition("- a\n- b\n")
    detail = validation_error_detail(caught.value)
    assert detail[0]["loc"] == []


def test_yaml_error_detail_is_a_single_entry():
    with pytest.raises(yaml.YAMLError) as caught:
        load_agent_definition("apiVersion: [unclosed\n")
    detail = validation_error_detail(caught.value)
    assert len(detail) == 1
    assert detail[0]["loc"] == []
```

Then the integration test — `tests/integration/test_api_agents_create.py`,
marked `@pytest.mark.integration`: post a two-document body built from
`examples/test-commander.agent.yaml` and
`examples/improve-api-tests.objective.yaml`, assert 201, assert the
response carries an `id` and `"status": "created"`, and assert the row is
readable through `AgentRepository.get`. Then post a body whose definition
has `apiVersion: juicebox.ai/v2` and assert 422 with `loc` naming
`apiVersion`. Then post a body with one document and assert 422.

Minimal implementation: `errors.py` defines
`validation_error_detail(error) -> list[dict]` returning, for a
`ValidationError`, one entry per `error.errors()` with `loc` as a list,
`msg`, and `type`; and for a `yaml.YAMLError`, a single entry with
`loc == []`, the exception's message, and `type == "yaml_error"`. `loc`
becomes a list because a tuple is not JSON, and the empty case must stay
an empty list rather than being dropped.

Every 422 this endpoint returns carries that same list-of-entries body,
including the wrong-document-count case, whose entry has `loc == []` and
`type == "document_count"`. A bare-string `detail` on one path would make a
client indexing `detail[0]["msg"]` receive a character rather than raise, so
the inconsistency corrupts silently instead of failing. An integration test
posts all three malformed shapes and asserts one body shape across them.

`dependencies.py` defines an async generator yielding an `AsyncSession`
from `session_scope()`, for `Depends`.

`agents.py` defines an `APIRouter` with `POST /agents` taking the raw
request body as text, splitting it with `yaml.safe_load_all`, requiring
exactly two documents, validating the first as `AgentDefinition` and the
second through `load_objective`'s envelope, and calling
`AgentRepository.create` with `definition.model_dump(by_alias=True)` and
the objective's dump.

`AgentRepository.create(session, name, definition, objective, *,
repository_url, base_branch, work_branch)` is the real signature. `name`
comes from `definition.metadata.name`; `repository_url` from
`definition.repository.url` and `base_branch` from
`definition.repository.branch`, both `None` when the block is absent.
`branch` is the base branch to check out, per specification section 13
step 3 — not the work branch, despite `examples/test-commander.agent.yaml`
naming it `juicebox/test-commander`, which reads like one. W6 creates the
work branch. Without this mapping, section 12's repository-information
requirement is unmet and increment 2's response model returns nulls.

The objective is stored as `Objective.model_dump()`, without the
`{objective: ...}` envelope, so reading it back uses
`Objective.model_validate`, not `load_objective`. Increment 7 records which
shape is stored, since `docs/schemas.md` documents the envelope.

Register an exception handler mapping
`ValidationError` and `yaml.YAMLError` to a 422 whose body is
`{"detail": validation_error_detail(exc)}`. Mount the router in
`create_app()`.

Verify: `make lint test && make test-integration`

Commit: `Add agent creation and the validation error contract`

### 2. Reading and deleting agents

- [x] List agents newest first, fetch one by id, and delete one.

Files: `src/juicebox/api/agents.py`,
`tests/integration/test_api_agents_read.py`

Failing test first — `tests/integration/test_api_agents_read.py`, marked
`@pytest.mark.integration`: create three agents through the API; assert
`GET /agents` returns them newest first; assert `?limit=1&offset=1`
returns exactly the middle one; assert `GET /agents/{id}` returns one
agent with a lowercase `"status"`; assert `GET /agents/{id}` for a
syntactically valid but absent UUID returns 404 with a JSON body, not a
stack trace; assert `GET /agents/{id}` for a malformed id returns 422;
assert `DELETE /agents/{id}` returns 204 and a subsequent `GET` returns
404.

Minimal implementation: `GET /agents` with `limit: int = 50` and
`offset: int = 0` calling `AgentRepository.list`; `GET /agents/{id}` and
`DELETE /agents/{id}` calling `get` and `delete`, with `get` returning
`None` mapped to a 404. A response model that serialises the agent's id,
name, status, timestamps, and repository fields — not the whole definition
blob, which a list endpoint should not return by the page.

`limit` and `offset` are bounded — `Query(ge=1, le=200)` and
`Query(ge=0)` — because an unbounded negative `limit` reaches PostgreSQL
and raises `InvalidRowCountInLimitClauseError`, which surfaces as a 500.
That is validation, not defensive programming.

`AgentRepository.delete` issues an unconditional `DELETE`, so deleting an
absent agent is a no-op. Assert 204 for that case as well: idempotent
deletion is what falls out and is worth pinning rather than leaving
undecided.

The `?limit=1&offset=1` assertion discriminates newest-first ordering, and
that is all it does. It does NOT exercise the `id` tiebreaker `list` uses
for rows sharing a `created_at`, because these three agents are created
through three separate requests and so have distinct timestamps. The
tiebreaker's guard already exists in
`tests/integration/test_repositories_agent.py`, which creates three agents
in one transaction. Do not claim this test covers it.

Verify: `make lint test && make test-integration`

Commit: `Add agent listing, retrieval, and deletion`

### 3. The state machine

- [x] Decide whether a lifecycle transition is legal, with no HTTP and no
      database involved.

Files: `src/juicebox/lifecycle/__init__.py`,
`src/juicebox/lifecycle/transitions.py`,
`tests/unit/test_lifecycle_transitions.py`

Failing test first — `tests/unit/test_lifecycle_transitions.py`:

```python
import pytest

from juicebox.lifecycle.transitions import (
    IllegalTransition,
    LifecycleAction,
    next_status,
)
from juicebox.persistence.models import AgentStatus


@pytest.mark.parametrize(
    ("current", "action", "expected"),
    [
        (AgentStatus.CREATED, LifecycleAction.START, AgentStatus.STARTING),
        (AgentStatus.RUNNING, LifecycleAction.PAUSE, AgentStatus.PAUSED),
        (AgentStatus.PAUSED, LifecycleAction.RESUME, AgentStatus.RUNNING),
        (AgentStatus.RUNNING, LifecycleAction.STOP, AgentStatus.STOPPED),
        (AgentStatus.STARTING, LifecycleAction.STOP, AgentStatus.STOPPED),
        (AgentStatus.FAILED, LifecycleAction.RESTART, AgentStatus.STARTING),
        (AgentStatus.STOPPED, LifecycleAction.RESTART, AgentStatus.STARTING),
    ],
)
def test_legal_transitions(current, action, expected):
    assert next_status(current, action) is expected


@pytest.mark.parametrize(
    ("current", "action"),
    [
        (AgentStatus.CREATED, LifecycleAction.PAUSE),
        (AgentStatus.COMPLETED, LifecycleAction.RESTART),
        (AgentStatus.COMPLETED, LifecycleAction.START),
        (AgentStatus.RUNNING, LifecycleAction.START),
        (AgentStatus.PAUSED, LifecycleAction.PAUSE),
    ],
)
def test_illegal_transitions_raise(current, action):
    with pytest.raises(IllegalTransition) as caught:
        next_status(current, action)
    assert current.value in str(caught.value)
    assert action.value in str(caught.value)


def test_completed_is_terminal_for_every_action():
    for action in LifecycleAction:
        with pytest.raises(IllegalTransition):
            next_status(AgentStatus.COMPLETED, action)


def test_no_action_reaches_waiting():
    """No caller action reaches WAITING. ADR-0004 has approval-gated
    operations fail closed rather than suspend, so nothing in the MVP
    enters it; the state exists because section 6 defines it and Phase 2
    will use it. This proves the transition table has no edge into WAITING,
    not that the column can never hold it — W9 could still set it directly,
    which is why decision 6 gives W9 `is_legal` to ask instead."""
    reachable = set()
    for current in AgentStatus:
        for action in LifecycleAction:
            try:
                reachable.add(next_status(current, action))
            except IllegalTransition:
                pass
    assert reachable, "no transition is legal; the table is empty"
    assert AgentStatus.WAITING not in reachable
```

Minimal implementation: write the transition table explicitly rather than
leaving it implied by the parametrised test above. It has seven edges:

| From | Action | To |
|---|---|---|
| `created` | `start` | `starting` |
| `starting` | `stop` | `stopped` |
| `running` | `pause` | `paused` |
| `running` | `stop` | `stopped` |
| `paused` | `resume` | `running` |
| `failed` | `restart` | `starting` |
| `stopped` | `restart` | `starting` |

`starting -> stopped` is the edge specification section 6 does not draw and
decision 5 makes necessary: nothing advances an agent out of `starting`
until W9 exists, so without it every started agent is unstoppable until
then. Increment 7 records it in section 31 alongside row 8, which recorded
the two restart edges for the same reason.

`LifecycleAction(StrEnum)` with `START`, `STOP`,
`RESTART`, `PAUSE`, `RESUME`, lowercase values per ADR-0009.
`IllegalTransition(Exception)` carrying the current status and the action
in its message, so the 409 body can quote both. `TRANSITIONS` as a mapping
of `(AgentStatus, LifecycleAction)` to `AgentStatus`, and
`next_status(current, action)` raising `IllegalTransition` on a missing
key.

`FAILED -> STARTING` and `STOPPED -> STARTING` are restart edges, and only
those. Section 6 draws all three of `FAILED`, `COMPLETED`, and `STOPPED` as
terminal with no arrow back, but ADR-0002 requires `restart` to start a
fresh attempt, so the state machine would otherwise refuse the call that
ADR mandates. `COMPLETED` stays terminal. Specification section 31 row 8
records this; increment 7 verifies the row still matches what shipped.

The last test is the one that keeps `WAITING` honest. It is unreachable by
construction rather than by convention, and if a later workstream adds an
edge into it the test fails and forces the question.

Also expose `is_legal(current, target) -> bool` over the full section 6
edge set, including the system transitions no caller action names —
`starting -> running`, `running -> completed`, `running -> failed`. W9
performs those and needs one place to ask; without it W9 calls
`set_status` directly and bypasses the machine design 0001 makes W3's to
own. Test it for one legal system edge and one illegal one.

Verify: `make lint test`

Commit: `Add the lifecycle state machine`

### 4. Start and stop

- [x] Start an agent, creating its first run attempt, and stop it.

Files: `src/juicebox/api/agents.py`,
`tests/integration/test_api_lifecycle.py`

Failing test first — `tests/integration/test_api_lifecycle.py`, marked
`@pytest.mark.integration`: create an agent; assert `POST
/agents/{id}/start` returns 200 with `"status": "starting"`; assert
`RunRepository.get_current` now returns a run with `attempt == 1`; assert
a second `POST .../start` returns 409 with a body naming both the current
status and the action; assert `POST /agents/{id}/stop` returns 200 with
`"status": "stopped"`; assert `POST` to either route for an absent agent
returns 404.

Minimal implementation: a shared handler taking the agent id and a
`LifecycleAction`, loading the agent, calling `next_status`, mapping
`IllegalTransition` to a 409 whose body carries the message, calling
`AgentRepository.set_status`, and for `START` also calling
`RunRepository.create_attempt`. `start` and `stop` are two routes over
that one handler; increment 5 adds three more to it rather than repeating
the logic.

`start` creates the run attempt and sets the status. It does not start a
container and does not run an execution loop — W6 and W9 own those. The
agent stays `starting` until W9 exists. Do not add a stub that pretends
otherwise.

Verify: `make lint test && make test-integration`

Commit: `Add start and stop`

### 5. Pause, resume, and restart

- [ ] Pause a running agent, resume it, and restart a failed or stopped
      one into a fresh attempt.

Files: `src/juicebox/api/agents.py`,
`tests/integration/test_api_lifecycle.py`

Failing test first, added to the same file: drive an agent to `running`
through the repository layer directly, since W9 does not exist to do it;
assert `pause` returns 200 and `"paused"`; assert `resume` returns 200 and
`"running"`; assert `pause` on a `created` agent returns 409. Then take a
second agent, `POST .../start` it through the API so it has attempt 1,
drive it to `failed` with `AgentRepository.set_status`, assert `restart`
returns 200 and `"starting"`, and
assert `RunRepository.get_current` returns `attempt == 2` — a restart
starts a fresh attempt and does not renumber or overwrite the first, which
ADR-0006 requires so a restarted agent still shows its earlier failures.
Then drive an agent to `completed` and assert `restart` returns 409.

Minimal implementation: three more routes over increment 4's handler.
`RESTART` also calls `RunRepository.create_attempt`, like `START`.

The `attempt == 2` assertion is the one that matters. A restart that
reused attempt 1 would pass a status-only test and destroy the history
ADR-0006 exists to preserve.

The agent must be started before being failed, or the assertion is wrong
rather than load-bearing: `create_attempt` computes `max(attempt) + 1`
over existing runs, so restarting an agent that was never started yields
attempt 1, not 2.

Verify: `make lint test && make test-integration`

Commit: `Add pause, resume, and restart`

### 6. Agent status

- [ ] Report an agent's status with its current run.

Files: `src/juicebox/api/agents.py`,
`tests/integration/test_api_status.py`

Failing test first — `tests/integration/test_api_status.py`, marked
`@pytest.mark.integration`: create an agent and assert `GET
/agents/{id}/status` returns 200 with `"status": "created"` and
`"current_run": null`; start it and assert `current_run` carries
`attempt == 1`, a lowercase status, and `iteration_count == 0`; then fail
that same started agent and restart it, asserting
`current_run.attempt == 2` — the agent must have been started first, for
the reason increment 5 gives; assert the
route returns 404 for an absent agent.

Minimal implementation: a response model with the agent's id, name,
status, timestamps, and a nullable `current_run` object carrying the run's
id, attempt, status, iteration count, and timestamps. ADR-0006 requires
this shape: the agent id is the only handle a caller holds, so run
information reaches them through the agent.

Verify: `make lint test && make test-integration`

Commit: `Add the agent status endpoint`

### 7. OpenAPI, documentation, and close-out

- [ ] Document the API, correct three records that no longer match what
      shipped, and close out W3.

Files: `docs/api.md`, `docs/specs/juice-box-spec.md`,
`.dev-commander/design/0001-mvp-decomposition.md`,
`.dev-commander/design/0002-definition-of-done.md`,
`.dev-commander/design/adr-0002-durable-state-in-mvp-resume-in-phase-2.md`,
`README.md`,
`CHANGELOG.md`, `FEATURES.md`, `TODO.md`,
`tests/unit/test_openapi.py`

Failing test first — `tests/unit/test_openapi.py`, which needs no
database:

```python
from juicebox.app import create_app

EXPECTED_AGENT_ROUTES = {
    ("/agents", "post"),
    ("/agents", "get"),
    ("/agents/{agent_id}", "get"),
    ("/agents/{agent_id}", "delete"),
    ("/agents/{agent_id}/start", "post"),
    ("/agents/{agent_id}/stop", "post"),
    ("/agents/{agent_id}/restart", "post"),
    ("/agents/{agent_id}/pause", "post"),
    ("/agents/{agent_id}/resume", "post"),
    ("/agents/{agent_id}/status", "get"),
}


def test_openapi_covers_every_agent_route():
    paths = create_app().openapi()["paths"]
    actual = {
        (path, method)
        for path, methods in paths.items()
        for method in methods
        if path == "/agents" or path.startswith("/agents/")
    }
    assert actual == EXPECTED_AGENT_ROUTES
```

The assertion is equality, not containment, so a route added without a plan
entry fails as loudly as a missing one. It is scoped to `/agents` routes
rather than the whole app: `/health` is W0's, and W4, W9, and W10 each add
routes under `/agents/{agent_id}` that would otherwise break this test
without warning. `docs/api.md` must state the contract — any workstream
adding an `/agents` route extends `EXPECTED_AGENT_ROUTES` in the same
commit — or the tripwire becomes a nuisance the next workstream deletes.

Minimal implementation: `docs/api.md` covering every route with its
request shape, response shape, and status codes; the state machine as a
transition table including the two restart edges; that `WAITING` is
defined and unreachable in the MVP, per ADR-0004, so a reader does not
report it as a gap; that `start` transitions state and creates a run but
executes nothing until W9; and the 422 body's shape including that `loc`
may be empty.

Then correct the records rather than leaving them wrong:
- Specification section 21 gains `GET /agents/{id}/status`, which section 6
  and ADR-0006 both require and section 21 omits.
- Specification section 31 gains a row recording the `starting -> stopped`
  edge, a sibling of row 8, which recorded the restart edges for the same
  reason: an edge section 6 does not draw that a decision here requires.
  The status endpoint needs no new row — row 6 already records ADR-0006's
  `current_run`; extend it to note the section 21 addition.
- Design 0001's W3 entry says "the six lifecycle endpoints"; there are five
  transitions. Correct the count.
- Design 0001 assigns no owner to section 21's `POST/GET
  /agents/{id}/messages` or `GET /agents/{id}/tasks`, while its W11 entry
  says the CLI's `message` command depends on W3. They are not W3's:
  `MessageRepository` has no `create`, and review 0004 recorded that W9 and
  W10 own the writers. Assign both blocks explicitly and correct W11's
  dependency line.
- `.dev-commander/design/0002-definition-of-done.md` workstream criteria 2
  and 3 become conditional on `tests/acceptance/` existing. Three plans have
  now exempted them individually.
- ADR-0002 is amended per decision 7: W4's event bus is the state-transition
  record, so no separate history table is built.

`docs/api.md` also documents the state machine as an interface, not only as
a transition table: the signatures of `next_status`, `is_legal`,
`LifecycleAction`, and `IllegalTransition`, with one usage example. W9
consumes them, and design 0002's workstream criterion 5 requires each owned
interface documented with names, types, and an example.

Record, do not act on:
- Section 30's `juicebox run --agent test-commander --repo <url>` passes a
  name where the API takes documents. Decision 4 weighs the three exits and
  names dropping `--repo` as the default and an API override parameter as
  the fallback. W11 decides.
- `POST /agents` is the enforcement point for ADR-0007's unknown-skill 422,
  and the check lands in W7, when skill directories first exist. W7 will
  modify `src/juicebox/api/agents.py` and increment 1's fixture, which posts
  `examples/test-commander.agent.yaml` — an example naming skills ADR-0007
  does not ship. `docs/schemas.md` already records that conflict.
- `run.current_task_id` carries no foreign key. Review 0004 named W3 or W9
  as its owner; W9 writes that column, so W9 decides.

Update README, CHANGELOG, FEATURES, and TODO. The controller runs
`/dc:review` and `/dc:journal`; they are not available to an implementer.

Verify: `make lint test && make test-integration`

Commit: `Document the agents API and close out W3`

## Exit Criteria

Design 0002's workstream criteria, less the two exempted above, plus
design 0001's W3 exit: an illegal transition is refused, and OpenAPI
covers the section 21 agent and lifecycle routes plus the status endpoint
section 21 omitted.

## Corrections to this plan

Recorded after a pre-flight scan and before implementation, in the form
plans 0002 and 0003 used. The scan built a scratch FastAPI app against the
real installed packages and ran it against the live database: five
blockers, four of which would have been found only during implementation
and one only in W9.

1. `starting` had no exit. Decision 5 stops anything advancing an agent out
   of `starting` until W9, and the transition table had no edge from it, so
   every started agent would have been unstoppable for six workstreams —
   removable only by `DELETE`. Proven against a scratch app: `stop` from
   `starting` returned 409 where increment 4 asserted 200. Added
   `starting -> stopped`, and increment 7 records it in section 31.
2. Increment 5's and increment 6's `attempt == 2` assertions would have
   failed. `create_attempt` computes `max(attempt) + 1`, so restarting an
   agent that was never started yields 1. The fixtures now start the agent
   first. The plan had called this assertion the one that matters, so it
   would have been written exactly as specified and failed.
3. Increment 2 claimed its paging assertion guarded the `id` tiebreaker. It
   does not: the three agents are created through three requests and so
   have distinct timestamps. Proven — the assertion passes with the
   tiebreaker removed. The real guard is in W1's repository tests. The
   claim is deleted rather than the test.
4. The OpenAPI test asserted `/agents/{agent_id}` while every prose
   reference wrote `{id}`. FastAPI derives the path from the decorator, so
   an implementer following the prose would have failed the assertion in
   the last increment, after five increments were committed. The spelling
   is now normative in the global constraints.
5. ADR-0002 requires every state transition written to PostgreSQL, and
   reviews 0004 and 0005 both assigned that question to W3. The plan was
   silent. Decision 7 now answers it: W4's event bus is the record.
6. The OpenAPI assertion compared the whole application's path set, which
   would have broken in W4, W9, and W10 with nothing telling those
   workstreams why. Now scoped to `/agents` routes, with the maintenance
   contract documented.
7. No increment said how tests reach the app. `tests/integration/conftest.py`
   was in no file list, and `TestClient` would have run the app on its own
   event loop against a deliberately `NullPool`'d engine. Increment 1 now
   adds an `ASGITransport` client fixture.
8. Increment 1 never mapped `name`, `repository_url`, or `base_branch` out
   of the definition, while increment 2's response model claimed to
   serialise repository fields — so those fields would have been null and
   section 12's repository requirement unmet. Also settled that
   `repository.branch` is the base branch, not the work branch.
9. Decision 3 claimed a JSON client works without a second code path.
   Proven false: a single JSON body cannot express two documents. Narrowed
   to the true claim, and the missing OpenAPI `requestBody` consequence
   recorded.
10. Decision 4 treated `--agent` as the hard half of section 30's CLI. It
    is not; `--repo` is, because honouring it means mutating a validated
    document, which ADR-0003 forbids. Three exits are now named and ranked.
11. The state machine could not express the system transitions section 6
    and ADR-0002 require, so W9 would have bypassed it. Decision 6 adds
    `is_legal`.
12. `test_no_action_reaches_waiting` passed on an empty transition table.
    Added a tripwire, and corrected a docstring that claimed more than the
    test proves.
13. Section 21's messaging and tasks routes have no owner in design 0001,
    while W11's entry depends on W3 for `message`. Increment 7 assigns them.
14. Smaller gaps closed: `src/juicebox/api/` and
    `tests/integration/conftest.py` already exist and were in no file list;
    `limit` and `offset` were unbounded, so a negative `limit` reached
    PostgreSQL as a 500; `DELETE` of an absent agent is a no-op 204 and now
    says so; the architecture section told the implementer to use W2's
    string loaders on a path that holds parsed documents; the objective is
    stored unwrapped and reading it back needs `Objective.model_validate`;
    design 0002's exemption is amended rather than repeated a third time.
