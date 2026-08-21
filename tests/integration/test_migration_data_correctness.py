"""Integration test proving the lowercase-status migration is data-correct,
not merely schema-correct.

Every table is empty during a normal test run, so a migration's `UPDATE`
statements are exercised by nothing: deleting both `UPDATE` lines from
`a017971fe447` was proven during review to leave the whole suite green.
This test seeds rows through raw SQL at the prior revision -- the current
models reject uppercase status values, so the ORM cannot be used -- then
upgrades and asserts the seeded rows actually changed.
"""

import asyncio
import uuid

import pytest
from alembic import command
from sqlalchemy import Uuid, bindparam, text

from juicebox.persistence.database import session_scope

PRIOR_REVISION = "d87365651814"  # add task; immediately before the lowercase migration
LOWERCASE_REVISION = "a017971fe447"  # lowercase agent and run status values

INSERT_AGENT = text(
    "INSERT INTO agent (id, name, definition, objective, status) "
    "VALUES (:id, 'seed-agent', '{}'::jsonb, '{}'::jsonb, 'RUNNING')"
).bindparams(bindparam("id", type_=Uuid()))

INSERT_RUN = text(
    "INSERT INTO run (id, agent_id, attempt, status, iteration_count) "
    "VALUES (:id, :agent_id, 1, 'RUNNING', 0)"
).bindparams(bindparam("id", type_=Uuid()), bindparam("agent_id", type_=Uuid()))

SELECT_AGENT_STATUS = text("SELECT status FROM agent WHERE id = :id").bindparams(
    bindparam("id", type_=Uuid())
)
SELECT_RUN_STATUS = text("SELECT status FROM run WHERE id = :id").bindparams(
    bindparam("id", type_=Uuid())
)


def _write(statement, **params) -> None:
    """Run a write statement on its own fresh event loop.

    `command.upgrade`/`command.downgrade` each drive `migrations/env.py`
    through their own `asyncio.run` call, so this test must stay a plain
    `def`, not `async def` -- pytest-asyncio's "auto" mode would already
    have a loop running, and nesting `asyncio.run` inside it raises. The
    `run_query` fixture in `conftest.py` uses the same one-loop-per-call
    shape for reads; this mirrors it for writes.
    """

    async def _run() -> None:
        async with session_scope() as session:
            await session.execute(statement, params)

    asyncio.run(_run())


def _read_one(statement, **params) -> str:
    async def _run() -> str:
        async with session_scope() as session:
            return (await session.scalars(statement, params)).one()

    return asyncio.run(_run())


@pytest.mark.integration
def test_lowercase_status_migration_lowercases_seeded_rows(alembic_config):
    """Seed uppercase agent and run rows at the revision before the
    lowercase migration, upgrade through it, and assert the seeded rows
    were actually rewritten -- not merely that the schema still applies.
    """
    agent_id = uuid.uuid4()
    run_id = uuid.uuid4()

    command.downgrade(alembic_config, PRIOR_REVISION)
    try:
        _write(INSERT_AGENT, id=agent_id)
        _write(INSERT_RUN, id=run_id, agent_id=agent_id)

        command.upgrade(alembic_config, LOWERCASE_REVISION)

        assert _read_one(SELECT_AGENT_STATUS, id=agent_id) == "running"
        assert _read_one(SELECT_RUN_STATUS, id=run_id) == "running"
    finally:
        # Every later test file's fixtures assume head; restore it even if
        # an assertion above failed.
        command.upgrade(alembic_config, "head")
