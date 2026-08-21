"""Agent and run repositories: the only module issuing queries for them.

Each method takes an `AsyncSession` the caller obtained from
`session_scope()` and never opens or commits one itself; the caller owns
the transaction boundary.
"""

import uuid
from typing import Any

from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from juicebox.persistence.models import Agent, AgentStatus, Run, RunStatus


class AgentRepository:
    """Create, read, list, update, and delete agents."""

    @staticmethod
    async def create(
        session: AsyncSession,
        name: str,
        definition: dict[str, Any],
        objective: dict[str, Any],
        *,
        repository_url: str | None = None,
        base_branch: str | None = None,
        work_branch: str | None = None,
    ) -> Agent:
        """Insert an agent and flush so its generated id is populated."""
        agent = Agent(
            name=name,
            definition=definition,
            objective=objective,
            repository_url=repository_url,
            base_branch=base_branch,
            work_branch=work_branch,
        )
        session.add(agent)
        await session.flush()
        return agent

    @staticmethod
    async def get(session: AsyncSession, agent_id: uuid.UUID) -> Agent | None:
        """Return the agent with `agent_id`, or `None` if it does not exist."""
        return await session.get(Agent, agent_id)

    @staticmethod
    async def list(
        session: AsyncSession, *, limit: int = 50, offset: int = 0
    ) -> list[Agent]:
        """Return agents newest-created first, paged by `limit` and `offset`.

        `id` breaks ties because `created_at` defaults to `now()`, which is
        transaction-scoped: agents created in one transaction share a
        timestamp, and without a tiebreaker their relative order is
        arbitrary, so paging over them could skip or repeat rows.
        """
        rows = await session.scalars(
            select(Agent)
            .order_by(Agent.created_at.desc(), Agent.id)
            .limit(limit)
            .offset(offset)
        )
        return list(rows)

    @staticmethod
    async def set_status(
        session: AsyncSession, agent_id: uuid.UUID, status: AgentStatus
    ) -> Agent | None:
        """Set an agent's status and, via `onupdate`, advance `updated_at`."""
        agent = await session.get(Agent, agent_id)
        if agent is None:
            return None
        agent.status = status
        await session.flush()
        return agent

    @staticmethod
    async def delete(session: AsyncSession, agent_id: uuid.UUID) -> None:
        """Delete an agent; its runs and every run-scoped row cascade."""
        await session.execute(delete(Agent).where(Agent.id == agent_id))


class RunRepository:
    """Create and read an agent's numbered run attempts, per ADR-0006."""

    @staticmethod
    async def create_attempt(session: AsyncSession, agent_id: uuid.UUID) -> Run:
        """Create the next attempt for an agent.

        Reads the current highest attempt number then writes one higher,
        which races if two starters act on the same agent concurrently.
        The MVP has a single orchestrator, and the unique constraint on
        `(agent_id, attempt)` fails loudly rather than corrupting data, so
        this is recorded rather than fixed with locking or retries.
        """
        current = await session.scalar(
            select(func.max(Run.attempt)).where(Run.agent_id == agent_id)
        )
        run = Run(agent_id=agent_id, attempt=(current or 0) + 1, status=RunStatus.STARTING)
        session.add(run)
        await session.flush()
        return run

    @staticmethod
    async def get_current(session: AsyncSession, agent_id: uuid.UUID) -> Run | None:
        """Return the highest-attempt run for an agent, or `None` if it has none."""
        return await session.scalar(
            select(Run)
            .where(Run.agent_id == agent_id)
            .order_by(Run.attempt.desc())
            .limit(1)
        )
