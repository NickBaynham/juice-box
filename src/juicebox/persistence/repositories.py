"""Repositories: the only module issuing queries for the persistence layer.

Each method takes an `AsyncSession` the caller obtained from
`session_scope()` and never opens or commits one itself; the caller owns
the transaction boundary.
"""

import uuid
from datetime import UTC, datetime
from decimal import Decimal
from typing import Any

from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from juicebox.persistence.models import (
    Agent,
    AgentStatus,
    Event,
    IterationRecord,
    Message,
    Run,
    RunStatus,
    Task,
    TaskPriority,
)


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
        """Set an agent's status and, via `onupdate`, advance `updated_at`.

        Refreshes after flush: `onupdate` is server-computed, so without a
        refresh `updated_at` is left expired and a caller serialising the
        agent triggers an unawaited lazy load.
        """
        agent = await session.get(Agent, agent_id)
        if agent is None:
            return None
        agent.status = status
        await session.flush()
        await session.refresh(agent)
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


class TaskRepository:
    """Create, read, and list a run's task graph nodes."""

    @staticmethod
    async def create(
        session: AsyncSession,
        agent_id: uuid.UUID,
        run_id: uuid.UUID,
        title: str,
        priority: TaskPriority,
        *,
        dependencies: list[str] | None = None,
    ) -> Task:
        """Insert a task and flush so its generated id is populated."""
        task = Task(
            agent_id=agent_id,
            run_id=run_id,
            title=title,
            priority=priority,
            dependencies=dependencies or [],
        )
        session.add(task)
        await session.flush()
        return task

    @staticmethod
    async def get(session: AsyncSession, task_id: uuid.UUID) -> Task | None:
        """Return the task with `task_id`, or `None` if it does not exist."""
        return await session.get(Task, task_id)

    @staticmethod
    async def list_for_run(session: AsyncSession, run_id: uuid.UUID) -> list[Task]:
        """Return a run's tasks oldest-created first, `id` breaking ties.

        `id` breaks ties for the same reason as `AgentRepository.list`:
        `created_at` is transaction-scoped, so tasks created together
        would otherwise sort arbitrarily.
        """
        rows = await session.scalars(
            select(Task).where(Task.run_id == run_id).order_by(Task.created_at, Task.id)
        )
        return list(rows)


class MessageRepository:
    """List and consume messages sent to a running agent, per section 7."""

    @staticmethod
    async def list_unconsumed(session: AsyncSession, agent_id: uuid.UUID) -> list[Message]:
        """Return an agent's unconsumed messages oldest-first by `seq`.

        Agent-scoped rather than run-scoped: per ADR-0006 a message is
        addressed to an agent, and W9's execution loop drains everything
        outstanding for the agent it is running as part of each iteration.
        """
        rows = await session.scalars(
            select(Message)
            .where(Message.agent_id == agent_id, Message.consumed_at.is_(None))
            .order_by(Message.seq)
        )
        return list(rows)

    @staticmethod
    async def mark_consumed(
        session: AsyncSession, message_id: uuid.UUID
    ) -> Message | None:
        """Stamp a message's `consumed_at` and return it, `None` if missing.

        Overwrites `consumed_at` unconditionally rather than checking
        whether it is already set: the caller drains ids returned by
        `list_unconsumed`, which excludes already-consumed messages, so
        re-consuming one does not occur in ordinary operation.
        """
        message = await session.get(Message, message_id)
        if message is None:
            return None
        message.consumed_at = datetime.now(UTC)
        await session.flush()
        return message


class EventRepository:
    """Append and read the append-only events an agent emits while running."""

    @staticmethod
    async def append(
        session: AsyncSession,
        agent_id: uuid.UUID,
        run_id: uuid.UUID,
        name: str,
        payload: dict[str, Any],
    ) -> Event:
        """Insert an event and flush so its generated id and `seq` populate."""
        event = Event(agent_id=agent_id, run_id=run_id, name=name, payload=payload)
        session.add(event)
        await session.flush()
        return event

    @staticmethod
    async def list_for_agent(session: AsyncSession, agent_id: uuid.UUID) -> list[Event]:
        """Return an agent's events oldest-first by `seq`."""
        rows = await session.scalars(
            select(Event).where(Event.agent_id == agent_id).order_by(Event.seq)
        )
        return list(rows)


class IterationRepository:
    """Append and read the append-only per-iteration execution history."""

    @staticmethod
    async def append(
        session: AsyncSession,
        agent_id: uuid.UUID,
        run_id: uuid.UUID,
        iteration: int,
        action: str,
        *,
        task_id: uuid.UUID | None = None,
        command: str | None = None,
        result: str | None = None,
        next_action: str | None = None,
        model: str | None = None,
        input_tokens: int | None = None,
        output_tokens: int | None = None,
        cost_usd: Decimal | None = None,
    ) -> IterationRecord:
        """Insert an iteration record and flush so its generated id populates."""
        record = IterationRecord(
            agent_id=agent_id,
            run_id=run_id,
            iteration=iteration,
            task_id=task_id,
            action=action,
            command=command,
            result=result,
            next_action=next_action,
            model=model,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            cost_usd=cost_usd,
        )
        session.add(record)
        await session.flush()
        return record

    @staticmethod
    async def list_for_run(
        session: AsyncSession, run_id: uuid.UUID
    ) -> list[IterationRecord]:
        """Return a run's iteration records ordered by `iteration`.

        The `(run_id, iteration)` unique index covers this filter, so
        Postgres can return iteration-sorted rows even with `ORDER BY`
        removed -- increment 6 hit exactly this. The test for this method
        adds an agent-scoped assertion over the same rows, which has no
        covering index, to prove this clause is load-bearing.
        """
        rows = await session.scalars(
            select(IterationRecord)
            .where(IterationRecord.run_id == run_id)
            .order_by(IterationRecord.iteration)
        )
        return list(rows)
