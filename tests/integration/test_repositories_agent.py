"""Integration tests for the Agent and Run repositories."""

import uuid

import pytest

from juicebox.persistence.database import session_scope
from juicebox.persistence.models import (
    Agent,
    AgentStatus,
    Artifact,
    Event,
    IterationRecord,
    Message,
    MessageType,
    Run,
    RunStatus,
    Task,
    TaskPriority,
    TaskStatus,
)
from juicebox.persistence.repositories import AgentRepository, RunRepository

DEFINITION = {"skills": ["playwright"], "permissions": {"network": False}}
OBJECTIVE = {"goal": "raise coverage", "completion_criteria": ["suite passes"]}


async def _create_agent(name: str = "test-commander") -> Agent:
    async with session_scope() as session:
        return await AgentRepository.create(session, name, DEFINITION, OBJECTIVE)


@pytest.mark.integration
async def test_create_returns_an_agent_with_an_id():
    agent = await _create_agent()

    assert agent.id is not None


@pytest.mark.integration
async def test_get_returns_the_agent_and_none_for_an_unknown_id():
    created = await _create_agent()

    async with session_scope() as session:
        found = await AgentRepository.get(session, created.id)
        missing = await AgentRepository.get(session, uuid.uuid4())

    assert found.id == created.id
    assert missing is None


@pytest.mark.integration
async def test_list_returns_agents_newest_first_and_honours_limit_and_offset():
    # Each agent is created in its own session_scope, so each gets its own
    # transaction and its own created_at. Three inserts sharing one
    # transaction would tie under now()'s transaction scoping and let
    # insertion order stand in for a real ORDER BY.
    created = [await _create_agent(f"agent-{i}") for i in range(3)]

    async with session_scope() as session:
        newest_first = await AgentRepository.list(session)
        second_page = await AgentRepository.list(session, limit=1, offset=1)

    assert [agent.id for agent in newest_first] == [a.id for a in reversed(created)]
    assert [agent.id for agent in second_page] == [created[1].id]


@pytest.mark.integration
async def test_set_status_persists_and_strictly_advances_updated_at():
    created = await _create_agent()

    # created and the status change are in separate session_scope blocks
    # (separate transactions), so they cannot share a transaction-scoped
    # now(); an implementation that let both share a transaction would
    # make the inequality below pass vacuously.
    async with session_scope() as session:
        original = await AgentRepository.get(session, created.id)
        original_updated_at = original.updated_at

    async with session_scope() as session:
        await AgentRepository.set_status(session, created.id, AgentStatus.RUNNING)

    async with session_scope() as session:
        stored = await AgentRepository.get(session, created.id)

    assert stored.status == AgentStatus.RUNNING
    assert stored.updated_at > original_updated_at


@pytest.mark.integration
async def test_delete_cascades_to_the_run_task_and_every_run_scoped_row():
    agent = await _create_agent()

    async with session_scope() as session:
        run = await RunRepository.create_attempt(session, agent.id)

    async with session_scope() as session:
        task = Task(
            agent_id=agent.id,
            run_id=run.id,
            title="write tests",
            status=TaskStatus.PENDING,
            priority=TaskPriority.MEDIUM,
            dependencies=[],
        )
        message = Message(
            agent_id=agent.id, run_id=run.id, type=MessageType.QUESTION, body={"q": "?"}
        )
        event = Event(agent_id=agent.id, run_id=run.id, name="started", payload={})
        artifact = Artifact(
            agent_id=agent.id,
            run_id=run.id,
            kind="report",
            name="summary.md",
            path="/tmp/summary.md",
            content_type="text/markdown",
            size_bytes=10,
        )
        iteration = IterationRecord(
            agent_id=agent.id, run_id=run.id, iteration=1, action="shell"
        )
        session.add_all([task, message, event, artifact, iteration])
    ids = {
        "task": task.id,
        "message": message.id,
        "event": event.id,
        "artifact": artifact.id,
        "iteration": iteration.id,
    }

    async with session_scope() as session:
        await AgentRepository.delete(session, agent.id)

    async with session_scope() as session:
        assert await session.get(Agent, agent.id) is None
        assert await session.get(Run, run.id) is None
        assert await session.get(Task, ids["task"]) is None
        assert await session.get(Message, ids["message"]) is None
        assert await session.get(Event, ids["event"]) is None
        assert await session.get(Artifact, ids["artifact"]) is None
        assert await session.get(IterationRecord, ids["iteration"]) is None


@pytest.mark.integration
async def test_create_attempt_numbers_attempts_sequentially_per_agent():
    agent = await _create_agent()

    async with session_scope() as session:
        first = await RunRepository.create_attempt(session, agent.id)
    async with session_scope() as session:
        second = await RunRepository.create_attempt(session, agent.id)

    assert first.attempt == 1
    assert second.attempt == 2
    assert second.status == RunStatus.STARTING


@pytest.mark.integration
async def test_get_current_returns_the_latest_attempt():
    agent = await _create_agent()
    async with session_scope() as session:
        await RunRepository.create_attempt(session, agent.id)
    async with session_scope() as session:
        latest = await RunRepository.create_attempt(session, agent.id)

    async with session_scope() as session:
        current = await RunRepository.get_current(session, agent.id)

    assert current.id == latest.id
    assert current.attempt == 2


@pytest.mark.integration
async def test_get_current_returns_none_for_an_agent_with_no_runs():
    agent = await _create_agent()

    async with session_scope() as session:
        current = await RunRepository.get_current(session, agent.id)

    assert current is None


@pytest.mark.integration
async def test_list_is_deterministic_for_agents_sharing_a_created_at():
    """Agents created in one transaction share created_at, since now() is
    transaction-scoped. Without a tiebreaker their order is arbitrary and
    paging over them could skip or repeat rows."""
    async with session_scope() as session:
        created = [
            await AgentRepository.create(
                session, name=f"agent-{index}", definition={}, objective={}
            )
            for index in range(3)
        ]
        ids = [agent.id for agent in created]

    async with session_scope() as session:
        listed = await AgentRepository.list(session)

    timestamps = {agent.created_at for agent in listed}
    assert len(timestamps) == 1, "expected one shared created_at"
    assert [agent.id for agent in listed] == sorted(ids)
