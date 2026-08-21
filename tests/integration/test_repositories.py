"""Integration tests for the Task, Message, Event, and Iteration repositories."""

import uuid
from datetime import UTC, datetime

import pytest
from sqlalchemy import select

from juicebox.persistence.database import session_scope
from juicebox.persistence.models import (
    Agent,
    Event,
    IterationRecord,
    Message,
    MessageType,
    Run,
    TaskPriority,
)
from juicebox.persistence.repositories import (
    AgentRepository,
    EventRepository,
    IterationRepository,
    MessageRepository,
    RunRepository,
    TaskRepository,
)

DEFINITION = {"skills": ["playwright"], "permissions": {"network": False}}
OBJECTIVE = {"goal": "raise coverage", "completion_criteria": ["suite passes"]}


async def _agent_and_run() -> tuple[Agent, Run]:
    async with session_scope() as session:
        agent = await AgentRepository.create(
            session, "test-commander", DEFINITION, OBJECTIVE
        )
    async with session_scope() as session:
        run = await RunRepository.create_attempt(session, agent.id)
    return agent, run


# ---- TaskRepository ----


@pytest.mark.integration
async def test_task_round_trips():
    agent, run = await _agent_and_run()

    async with session_scope() as session:
        created = await TaskRepository.create(
            session, agent.id, run.id, "write tests", TaskPriority.HIGH
        )
    task_id = created.id

    async with session_scope() as session:
        stored = await TaskRepository.get(session, task_id)

    assert stored.id == task_id
    assert stored.title == "write tests"
    assert stored.priority == TaskPriority.HIGH
    assert stored.dependencies == []


@pytest.mark.integration
async def test_task_get_returns_none_for_an_unknown_id():
    async with session_scope() as session:
        missing = await TaskRepository.get(session, uuid.uuid4())

    assert missing is None


@pytest.mark.integration
async def test_list_for_run_returns_only_that_runs_tasks_oldest_first():
    agent, run = await _agent_and_run()
    async with session_scope() as session:
        other_run = await RunRepository.create_attempt(session, agent.id)

    # Each task is created in its own session_scope so each gets its own
    # transaction and its own created_at, making insertion order the same
    # as created_at order.
    async with session_scope() as session:
        first = await TaskRepository.create(
            session, agent.id, run.id, "first", TaskPriority.LOW
        )
    async with session_scope() as session:
        second = await TaskRepository.create(
            session, agent.id, run.id, "second", TaskPriority.LOW
        )
    async with session_scope() as session:
        await TaskRepository.create(
            session, agent.id, other_run.id, "other run's task", TaskPriority.LOW
        )

    async with session_scope() as session:
        tasks = await TaskRepository.list_for_run(session, run.id)

    assert [task.id for task in tasks] == [first.id, second.id]


# ---- MessageRepository ----


@pytest.mark.integration
async def test_list_unconsumed_returns_oldest_first_by_seq_and_excludes_consumed():
    agent, run = await _agent_and_run()
    other_agent, other_run = await _agent_and_run()

    # All rows share one transaction so created_at ties. seq is assigned
    # in the reverse of insertion order, so only a query that truly
    # orders by seq can produce the asserted result.
    async with session_scope() as session:
        second_by_seq = Message(
            agent_id=agent.id,
            run_id=run.id,
            type=MessageType.INSTRUCTION,
            body={"m": "b"},
        )
        first_by_seq = Message(
            agent_id=agent.id,
            run_id=run.id,
            type=MessageType.INSTRUCTION,
            body={"m": "a"},
        )
        already_consumed = Message(
            agent_id=agent.id,
            run_id=run.id,
            type=MessageType.INSTRUCTION,
            body={"m": "c"},
            consumed_at=datetime.now(UTC),
        )
        other_agents_message = Message(
            agent_id=other_agent.id,
            run_id=other_run.id,
            type=MessageType.INSTRUCTION,
            body={"m": "d"},
        )
        second_by_seq.seq = 300
        first_by_seq.seq = 100
        already_consumed.seq = 200
        other_agents_message.seq = 50
        session.add_all(
            [second_by_seq, first_by_seq, already_consumed, other_agents_message]
        )

    async with session_scope() as session:
        unconsumed = await MessageRepository.list_unconsumed(session, agent.id)

    assert [m.body["m"] for m in unconsumed] == ["a", "b"]


@pytest.mark.integration
async def test_mark_consumed_sets_consumed_at_and_returns_the_message():
    agent, run = await _agent_and_run()
    async with session_scope() as session:
        message = Message(
            agent_id=agent.id, run_id=run.id, type=MessageType.QUESTION, body={"q": "?"}
        )
        session.add(message)
    message_id = message.id

    async with session_scope() as session:
        consumed = await MessageRepository.mark_consumed(session, message_id)

    assert consumed.id == message_id
    assert consumed.consumed_at is not None

    async with session_scope() as session:
        stored = await session.get(Message, message_id)

    assert stored.consumed_at is not None


@pytest.mark.integration
async def test_mark_consumed_returns_none_for_an_unknown_message():
    async with session_scope() as session:
        result = await MessageRepository.mark_consumed(session, uuid.uuid4())

    assert result is None


# ---- EventRepository ----


@pytest.mark.integration
async def test_append_returns_an_event_with_seq_populated():
    agent, run = await _agent_and_run()

    async with session_scope() as session:
        event = await EventRepository.append(
            session, agent.id, run.id, "started", {"k": "v"}
        )

    assert event.id is not None
    assert event.seq is not None


@pytest.mark.integration
async def test_list_for_agent_returns_events_oldest_first_by_seq():
    agent, run = await _agent_and_run()
    other_agent, other_run = await _agent_and_run()

    # All rows share one transaction so created_at ties. seq is assigned
    # in the reverse of insertion order, so only a query that truly
    # orders by seq can produce the asserted result.
    async with session_scope() as session:
        events = [
            Event(agent_id=agent.id, run_id=run.id, name=f"step-{i}", payload={"i": i})
            for i in range(3)
        ]
        for event, seq in zip(events, [300, 100, 200], strict=True):
            event.seq = seq
        other_agents_event = Event(
            agent_id=other_agent.id, run_id=other_run.id, name="other", payload={}
        )
        other_agents_event.seq = 50
        session.add_all([*events, other_agents_event])

    async with session_scope() as session:
        ordered = await EventRepository.list_for_agent(session, agent.id)

    assert [e.name for e in ordered] == ["step-1", "step-2", "step-0"]


# ---- IterationRepository ----


@pytest.mark.integration
async def test_append_returns_an_iteration_record():
    agent, run = await _agent_and_run()

    async with session_scope() as session:
        record = await IterationRepository.append(session, agent.id, run.id, 1, "shell")

    assert record.id is not None
    assert record.iteration == 1
    assert record.action == "shell"


@pytest.mark.integration
async def test_list_for_run_returns_records_ordered_by_iteration():
    agent, run = await _agent_and_run()

    # Inserted as iterations 2, 1, 0 -- the reverse of iteration order --
    # all in one transaction so created_at ties. Only a query that truly
    # orders by iteration can produce the asserted result.
    async with session_scope() as session:
        records = [
            IterationRecord(
                agent_id=agent.id,
                run_id=run.id,
                iteration=iteration,
                action=f"action-{iteration}",
            )
            for iteration in [2, 1, 0]
        ]
        session.add_all(records)

    async with session_scope() as session:
        ordered = await IterationRepository.list_for_run(session, run.id)

    assert [r.action for r in ordered] == ["action-0", "action-1", "action-2"]

    # The query above filters on run_id, which the (run_id, iteration)
    # unique index covers, so Postgres can return iteration-sorted rows
    # even with the ORDER BY removed (increment 6 hit exactly this in the
    # model-level test). agent_id has no index on this table, so the same
    # assertion filtered by agent_id forces a sequential scan and sort,
    # and genuinely depends on the ORDER BY clause above.
    async with session_scope() as session:
        rows = await session.scalars(
            select(IterationRecord)
            .where(IterationRecord.agent_id == agent.id)
            .order_by(IterationRecord.iteration)
        )
        agent_scoped = list(rows)

    assert [r.action for r in agent_scoped] == ["action-0", "action-1", "action-2"]
