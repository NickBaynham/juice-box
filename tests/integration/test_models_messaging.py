"""Integration tests for the Message and Event models."""

from datetime import UTC, datetime

import pytest
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from juicebox.persistence.database import session_scope
from juicebox.persistence.models import (
    Agent,
    Event,
    Message,
    MessageType,
    Run,
    RunStatus,
)

DEFINITION = {"skills": ["playwright"], "permissions": {"network": False}}
OBJECTIVE = {"goal": "raise coverage", "completion_criteria": ["suite passes"]}


def _agent() -> Agent:
    return Agent(name="test-commander", definition=DEFINITION, objective=OBJECTIVE)


async def _agent_and_run() -> tuple[Agent, Run]:
    agent = _agent()
    async with session_scope() as session:
        session.add(agent)
    run = Run(agent_id=agent.id, attempt=1, status=RunStatus.RUNNING)
    async with session_scope() as session:
        session.add(run)
    return agent, run


@pytest.mark.integration
async def test_unconsumed_messages_are_returned_oldest_first_by_seq():
    agent, run = await _agent_and_run()

    # All three rows are added in one session/transaction so their
    # created_at values collide; a table scan happens to return rows in
    # insertion order in that case, which would make a query ordered by
    # created_at pass by coincidence. To rule that out, seq is assigned
    # in the reverse of insertion order below, so only a genuinely
    # seq-ordered query can produce the asserted result.
    async with session_scope() as session:
        inserted_first = Message(
            agent_id=agent.id,
            run_id=run.id,
            type=MessageType.INSTRUCTION,
            body={"message": "b"},
        )
        inserted_second = Message(
            agent_id=agent.id,
            run_id=run.id,
            type=MessageType.INSTRUCTION,
            body={"message": "a"},
        )
        consumed = Message(
            agent_id=agent.id,
            run_id=run.id,
            type=MessageType.INSTRUCTION,
            body={"message": "c"},
            consumed_at=datetime.now(UTC),
        )
        inserted_first.seq = 300
        inserted_second.seq = 100
        consumed.seq = 200
        session.add_all([inserted_first, inserted_second, consumed])

    async with session_scope() as session:
        rows = await session.scalars(
            select(Message)
            .where(Message.agent_id == agent.id, Message.consumed_at.is_(None))
            .order_by(Message.seq)
        )
        unconsumed = list(rows)

    assert [row.body["message"] for row in unconsumed] == ["a", "b"]


@pytest.mark.integration
async def test_events_are_returned_in_seq_order_for_an_agent():
    agent, run = await _agent_and_run()

    # Inserted as step-0, step-1, step-2, all in one transaction so
    # created_at collides. seq is assigned in reverse of insertion order
    # so the assertion can only pass if the query truly orders by seq;
    # ordering by created_at would fall back to insertion order instead.
    async with session_scope() as session:
        events = [
            Event(agent_id=agent.id, run_id=run.id, name=f"step-{i}", payload={"i": i})
            for i in range(3)
        ]
        for event, seq in zip(events, [300, 200, 100], strict=True):
            event.seq = seq
        session.add_all(events)

    async with session_scope() as session:
        rows = await session.scalars(
            select(Event).where(Event.agent_id == agent.id).order_by(Event.seq)
        )
        ordered = list(rows)

    assert [row.name for row in ordered] == ["step-2", "step-1", "step-0"]


@pytest.mark.integration
async def test_message_rejects_a_type_outside_section_7():
    agent, run = await _agent_and_run()
    message = Message(
        agent_id=agent.id,
        run_id=run.id,
        type="teleport",
        body={"message": "nope"},
    )

    with pytest.raises(IntegrityError):
        async with session_scope() as session:
            session.add(message)


@pytest.mark.integration
async def test_deleting_the_parent_agent_deletes_the_message_and_event():
    agent, run = await _agent_and_run()
    message = Message(
        agent_id=agent.id, run_id=run.id, type=MessageType.QUESTION, body={"q": "?"}
    )
    event = Event(agent_id=agent.id, run_id=run.id, name="started", payload={})
    async with session_scope() as session:
        session.add_all([message, event])
    message_id, event_id = message.id, event.id

    async with session_scope() as session:
        stored_agent = await session.get(Agent, agent.id)
        await session.delete(stored_agent)

    async with session_scope() as session:
        assert await session.get(Message, message_id) is None
        assert await session.get(Event, event_id) is None


@pytest.mark.integration
async def test_deleting_the_parent_run_deletes_the_message_and_event():
    agent, run = await _agent_and_run()
    message = Message(
        agent_id=agent.id, run_id=run.id, type=MessageType.QUESTION, body={"q": "?"}
    )
    event = Event(agent_id=agent.id, run_id=run.id, name="started", payload={})
    async with session_scope() as session:
        session.add_all([message, event])
    message_id, event_id = message.id, event.id

    async with session_scope() as session:
        stored_run = await session.get(Run, run.id)
        await session.delete(stored_run)

    async with session_scope() as session:
        assert await session.get(Message, message_id) is None
        assert await session.get(Event, event_id) is None


@pytest.mark.integration
async def test_seq_is_assigned_automatically_and_increases():
    """seq must auto-assign monotonically: W4 and W10 page on it as a cursor.

    Every other test sets seq by hand to force a divergence from created_at,
    so without this one a column that never incremented would still pass.
    """
    agent, run = await _agent_and_run()

    for index in range(3):
        async with session_scope() as session:
            session.add(
                Event(
                    agent_id=agent.id,
                    run_id=run.id,
                    name=f"event-{index}",
                    payload={"index": index},
                )
            )

    async with session_scope() as session:
        assigned = (
            await session.scalars(
                select(Event.seq).where(Event.agent_id == agent.id).order_by(Event.name)
            )
        ).all()

    assert all(value is not None for value in assigned)
    assert assigned == sorted(assigned)
    assert len(set(assigned)) == 3
