"""Integration tests for the Agent and Run models."""

import pytest
from sqlalchemy.exc import IntegrityError

from juicebox.persistence.database import session_scope
from juicebox.persistence.models import Agent, AgentStatus, Run, RunStatus

DEFINITION = {"skills": ["playwright"], "permissions": {"network": False}}
OBJECTIVE = {"goal": "raise coverage", "completion_criteria": ["suite passes"]}


def _agent() -> Agent:
    return Agent(
        name="test-commander",
        definition=DEFINITION,
        objective=OBJECTIVE,
        repository_url="https://github.com/example/project",
        base_branch="main",
    )


@pytest.mark.integration
async def test_agent_round_trips_json_and_defaults_to_created():
    agent = _agent()
    async with session_scope() as session:
        session.add(agent)
    agent_id = agent.id

    async with session_scope() as session:
        stored = await session.get(Agent, agent_id)

    assert stored.definition == DEFINITION
    assert stored.objective == OBJECTIVE
    assert stored.status == AgentStatus.CREATED
    assert stored.created_at.tzinfo is not None
    assert stored.started_at is None


@pytest.mark.integration
async def test_agent_rejects_a_status_outside_the_lifecycle():
    agent = _agent()
    agent.status = "ASCENDED"

    with pytest.raises(IntegrityError):
        async with session_scope() as session:
            session.add(agent)


@pytest.mark.integration
async def test_run_attempt_is_unique_per_agent():
    agent = _agent()
    async with session_scope() as session:
        session.add(agent)
    agent_id = agent.id

    async with session_scope() as session:
        session.add(Run(agent_id=agent_id, attempt=1, status=RunStatus.RUNNING))

    with pytest.raises(IntegrityError):
        async with session_scope() as session:
            session.add(Run(agent_id=agent_id, attempt=1, status=RunStatus.RUNNING))

    async with session_scope() as session:
        checkpointed = Run(
            agent_id=agent_id,
            attempt=2,
            status=RunStatus.RUNNING,
            checkpoint={"iteration": 3},
        )
        session.add(checkpointed)
    run_id = checkpointed.id

    async with session_scope() as session:
        stored = await session.get(Run, run_id)

    assert stored.checkpoint == {"iteration": 3}
    assert stored.iteration_count == 0
