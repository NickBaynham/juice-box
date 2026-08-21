# Persistence layer

The schema, session handling, and repository API workstream W1 delivers.
A consumer should be able to read this document and use the layer without
opening `models.py` or `repositories.py`.

## Sessions

`juicebox.persistence.database` exposes `session_scope()`, an
async context manager yielding an `AsyncSession` that commits on a clean
exit and rolls back and re-raises on error:

```python
from juicebox.persistence.database import session_scope
from juicebox.persistence.repositories import AgentRepository

async with session_scope() as session:
    agent = await AgentRepository.create(session, "my-agent", definition, objective)
```

The engine uses `NullPool`: a pooled connection cached on one asyncio
event loop breaks on another, which matters under `pytest-asyncio`'s
per-test loop and is worth keeping in mind before pooling is revisited
for production traffic.

## Entities

Every table carries `id` (`uuid4`, primary key) and `created_at`. Every
table but `agent` and `run` also carries `agent_id` and `run_id` (both
foreign keys, `ondelete="CASCADE"` unless noted), per ADR-0006. `run`
carries `agent_id` but not `run_id` — it is the run. `agent` is the root
the rest hang off and carries neither. Mutable tables also carry
`updated_at`. Timestamps are `DateTime(timezone=True)`;
`created_at`/`updated_at` default to `now()` at the database, and
`updated_at` advances on every update.

| Table | Columns beyond the common set | Notes |
| --- | --- | --- |
| `agent` | `name`, `definition` (`JSONB`), `objective` (`JSONB`), `repository_url`, `base_branch`, `work_branch`, `status`, `failure_reason`, `started_at`, `finished_at` | Root entity; no `agent_id`/`run_id`. `status` defaults to `created`. |
| `run` | `agent_id`, `attempt`, `status`, `iteration_count` (default `0`), `current_task_id`, `checkpoint` (`JSONB`, nullable), `failure_reason`, `started_at`, `finished_at` | One numbered attempt at an agent's objective. Unique on `(agent_id, attempt)`. Never `created` — a run is created by starting. |
| `task` | `agent_id`, `run_id`, `title`, `status`, `priority`, `dependencies` (`JSONB` list of task ids), `attempts` (default `0`), `result` (`JSONB`, nullable), `error`, `started_at`, `finished_at` | One node in the task graph. |
| `message` | `seq` (`BIGSERIAL`-equivalent identity), `agent_id`, `run_id`, `type`, `body` (`JSONB`), `consumed_at` | Sent to a running agent. Index on `(agent_id, seq)`. Ordered by `seq`, not `created_at`, which is transaction-scoped and ties within a transaction. |
| `event` | `seq`, `agent_id`, `run_id`, `name`, `payload` (`JSONB`) | Append-only; no `updated_at`. Index on `(agent_id, seq)`. |
| `artifact` | `agent_id`, `run_id`, `kind`, `name`, `path`, `content_type`, `size_bytes` | Append-only; no `updated_at`. `kind` is a free-form string, not CHECK-constrained — section 4 lists it as illustrative, not a closed set. |
| `iteration_record` | `agent_id`, `run_id`, `iteration`, `task_id` (nullable, `ondelete="SET NULL"`), `action`, `command`, `result`, `next_action`, `model`, `input_tokens`, `output_tokens`, `cost_usd` (`Numeric(12, 6)`) | Append-only; no `updated_at`. Unique on `(run_id, iteration)`. `task_id` is `SET NULL` rather than cascaded: history should outlive the task it was once linked to. |

## Status and type enums

Every status and type column is a plain `String` with a `CHECK`
constraint built by `status_check()`, not a native PostgreSQL enum type —
a native enum survives `DROP TABLE`, which fails a
`downgrade base` + `upgrade head` cycle with `DuplicateObjectError`. All
values are lowercase, per
[ADR-0009](../.dev-commander/design/adr-0009-status-values-are-lowercase.md);
enum member names stay uppercase Python identifiers, so
`AgentStatus.RUNNING.value == "running"`.

| Enum | Column(s) | Legal values |
| --- | --- | --- |
| `AgentStatus` | `agent.status` | `created`, `starting`, `running`, `paused`, `waiting`, `completed`, `failed`, `stopped` |
| `RunStatus` | `run.status` | `starting`, `running`, `paused`, `waiting`, `completed`, `failed`, `stopped` (never `created`) |
| `TaskStatus` | `task.status` | `pending`, `ready`, `running`, `blocked`, `waiting`, `completed`, `failed`, `cancelled` |
| `TaskPriority` | `task.priority` | `low`, `medium`, `high` |
| `MessageType` | `message.type` | `instruction`, `question`, `context`, `priority-change`, `cancel-task`, `new-task`, `approval` |

`MessageType` values are the wire form the API accepts; three contain
hyphens, so the corresponding members are named `PRIORITY_CHANGE`,
`CANCEL_TASK`, and `NEW_TASK`.

## Repository API

Every repository is a class of `@staticmethod`s taking an `AsyncSession`
as its first argument. None opens, commits, or rolls back a session — the
caller owns the transaction boundary via `session_scope()`. This is
enforced by `tests/unit/test_query_locality.py`: no module under
`src/juicebox` outside `persistence/` may call `select(` or
`session.execute`.

### `AgentRepository`

```python
async def create(session, name: str, definition: dict, objective: dict, *,
                  repository_url: str | None = None,
                  base_branch: str | None = None,
                  work_branch: str | None = None) -> Agent
async def get(session, agent_id: UUID) -> Agent | None
async def list(session, *, limit: int = 50, offset: int = 0) -> list[Agent]
async def set_status(session, agent_id: UUID, status: AgentStatus) -> Agent | None
async def delete(session, agent_id: UUID) -> None
```

`list` orders newest-created first, `id` breaking ties. `set_status`
persists the new status and advances `updated_at` via `onupdate`.
`delete` cascades to the agent's runs and every run-scoped row.

### `RunRepository`

```python
async def create_attempt(session, agent_id: UUID) -> Run
async def get_current(session, agent_id: UUID) -> Run | None
```

`create_attempt` reads the current highest attempt then writes one
higher; this races under concurrent starters for the same agent. The MVP
has a single orchestrator, and the unique `(agent_id, attempt)`
constraint fails loudly rather than corrupting data, so this is recorded
rather than fixed with locking or retries.

### `TaskRepository`

```python
async def create(session, agent_id: UUID, run_id: UUID, title: str,
                  priority: TaskPriority, *,
                  dependencies: list[str] | None = None) -> Task
async def get(session, task_id: UUID) -> Task | None
async def list_for_run(session, run_id: UUID) -> list[Task]
```

`list_for_run` orders oldest-created first, `id` breaking ties.

### `MessageRepository`

```python
async def list_unconsumed(session, agent_id: UUID) -> list[Message]
async def mark_consumed(session, message_id: UUID) -> Message | None
```

`list_unconsumed` is agent-scoped, not run-scoped — a message is
addressed to an agent per ADR-0006 — and returns oldest-first by `seq`.
`mark_consumed` stamps `consumed_at` unconditionally; the caller drains
ids returned by `list_unconsumed`, which already excludes consumed rows.

### `EventRepository`

```python
async def append(session, agent_id: UUID, run_id: UUID, name: str,
                  payload: dict) -> Event
async def list_for_agent(session, agent_id: UUID) -> list[Event]
```

`list_for_agent` returns events oldest-first by `seq`.

### `IterationRepository`

```python
async def append(session, agent_id: UUID, run_id: UUID, iteration: int,
                  action: str, *, task_id: UUID | None = None,
                  command: str | None = None, result: str | None = None,
                  next_action: str | None = None, model: str | None = None,
                  input_tokens: int | None = None,
                  output_tokens: int | None = None,
                  cost_usd: Decimal | None = None) -> IterationRecord
async def list_for_run(session, run_id: UUID) -> list[IterationRecord]
```

`list_for_run` orders by `iteration`. Its `run_id` filter is covered by
the `(run_id, iteration)` unique index, so Postgres can satisfy it with
an index scan and no sort step even without the `ORDER BY` — its test
proves the clause is load-bearing with an agent-scoped assertion over the
same rows instead, which has no covering index.

## Creating a migration

1. Change `src/juicebox/persistence/models.py`.
2. Generate a revision:

   ```
   pdm run alembic revision --autogenerate -m "add thing"
   ```

3. Read the generated file under `migrations/versions/` before
   committing it. Autogenerate is a starting point, not a final answer —
   it cannot detect a data migration (see below) or judge whether a
   `CHECK` constraint should be hand-written.
4. Check it rolls back and re-applies cleanly:

   ```
   pdm run alembic downgrade base && pdm run alembic upgrade head
   ```

   A native PostgreSQL enum type fails this cycle with
   `DuplicateObjectError`, which is why status columns are `String` plus
   `CHECK`, never `sa.Enum`.
5. If the migration changes existing values rather than only the schema
   (as `a017971fe447` does — see `AGENT_STATUSES_LOWER` and
   `RUN_STATUSES_LOWER` in that revision), write the `UPDATE` by hand and
   prove it with a test that seeds rows through raw SQL at the prior
   revision before upgrading. An empty table exercises no `UPDATE`
   statement, so the normal suite cannot catch one going missing;
   `tests/integration/test_migration_data_correctness.py` is the
   pattern to follow.

Full details on `alembic.ini`, `env.py`, and running migrations against
Compose or the container image are in
[the development guide](development.md#database-schema-and-migrations).

## Adding a relationship later

No model declares a SQLAlchemy `relationship()` yet; every cascade here
is `ondelete="CASCADE"` (or `"SET NULL"` for `iteration_record.task_id`)
enforced by the database, and repositories navigate by explicit foreign
key queries. If a later workstream adds a `relationship()` for
convenience, it must pass `passive_deletes=True`. Without it, SQLAlchemy
tries to load and individually delete or null out every child row in
Python before issuing the parent delete, which both defeats the
database-level cascade these tests assert and silently changes the
behavior `AgentRepository.delete`'s cascade test and
`RunRepository`/`TaskRepository`'s equivalents rely on.

## Known performance items

Recorded rather than fixed in this workstream, per the increment 9 note:

- `task` has no index on `run_id`, so `TaskRepository.list_for_run`
  sequential-scans. Worth an index if task lists grow large enough to
  matter; not needed at MVP scale.
- `repositories.py` holds all six repository classes in one module. Worth
  splitting one file per aggregate (agent/run, task, messaging,
  execution) if W3 adds enough to it to make the single file hard to
  navigate.
