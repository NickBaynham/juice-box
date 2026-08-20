"""Integration tests for the Task model."""

import uuid

import pytest
from sqlalchemy.exc import IntegrityError

from juicebox.persistence.database import session_scope
from juicebox.persistence.models import (
    Agent,
    Run,
    RunStatus,
    Task,
    TaskPriority,
    TaskStatus,
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
async def test_task_round_trips_dependencies_and_defaults():
    agent, run = await _agent_and_run()
    dep_a, dep_b = str(uuid.uuid4()), str(uuid.uuid4())
    task = Task(
        agent_id=agent.id,
        run_id=run.id,
        title="Create authentication API tests",
        priority=TaskPriority.HIGH,
        dependencies=[dep_a, dep_b],
    )
    async with session_scope() as session:
        session.add(task)
    task_id = task.id

    async with session_scope() as session:
        stored = await session.get(Task, task_id)

    assert stored.dependencies == [dep_a, dep_b]
    assert stored.status == TaskStatus.PENDING
    assert stored.attempts == 0


@pytest.mark.integration
async def test_task_rejects_a_status_outside_task_management():
    agent, run = await _agent_and_run()
    task = Task(
        agent_id=agent.id,
        run_id=run.id,
        title="Create authentication API tests",
        priority=TaskPriority.HIGH,
        dependencies=[],
        status="ASCENDED",
    )

    with pytest.raises(IntegrityError):
        async with session_scope() as session:
            session.add(task)


@pytest.mark.integration
async def test_deleting_the_parent_agent_deletes_the_task():
    agent, run = await _agent_and_run()
    task = Task(
        agent_id=agent.id,
        run_id=run.id,
        title="Create authentication API tests",
        priority=TaskPriority.HIGH,
        dependencies=[],
    )
    async with session_scope() as session:
        session.add(task)
    task_id = task.id

    async with session_scope() as session:
        stored_agent = await session.get(Agent, agent.id)
        await session.delete(stored_agent)

    async with session_scope() as session:
        assert await session.get(Task, task_id) is None
