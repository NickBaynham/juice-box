"""Integration tests for the Artifact and IterationRecord models."""

from decimal import Decimal

import pytest
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from juicebox.persistence.database import session_scope
from juicebox.persistence.models import (
    Agent,
    Artifact,
    IterationRecord,
    Run,
    RunStatus,
    Task,
    TaskPriority,
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
async def test_iteration_record_rejects_a_duplicate_run_and_iteration():
    agent, run = await _agent_and_run()
    first = IterationRecord(agent_id=agent.id, run_id=run.id, iteration=1, action="shell")
    async with session_scope() as session:
        session.add(first)

    duplicate = IterationRecord(
        agent_id=agent.id, run_id=run.id, iteration=1, action="shell"
    )
    with pytest.raises(IntegrityError):
        async with session_scope() as session:
            session.add(duplicate)


@pytest.mark.integration
async def test_iteration_records_are_returned_in_iteration_order_for_a_run():
    agent, run = await _agent_and_run()

    # Inserted as records 0, 1, 2, all in one transaction so created_at
    # collides. The `iteration` values below are the reverse of insertion
    # order, so the assertion can only pass if the query truly orders by
    # `iteration`; ordering by created_at or insertion order would produce
    # the opposite sequence.
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
        rows = await session.scalars(
            select(IterationRecord)
            .where(IterationRecord.run_id == run.id)
            .order_by(IterationRecord.iteration)
        )
        ordered = list(rows)

    assert [row.action for row in ordered] == ["action-0", "action-1", "action-2"]


@pytest.mark.integration
async def test_artifact_round_trips():
    agent, run = await _agent_and_run()
    artifact = Artifact(
        agent_id=agent.id,
        run_id=run.id,
        kind="report",
        name="coverage.html",
        path="/workspace/artifacts/coverage.html",
        content_type="text/html",
        size_bytes=4096,
    )
    async with session_scope() as session:
        session.add(artifact)
    artifact_id = artifact.id

    async with session_scope() as session:
        stored = await session.get(Artifact, artifact_id)

    assert stored.kind == "report"
    assert stored.name == "coverage.html"
    assert stored.path == "/workspace/artifacts/coverage.html"
    assert stored.content_type == "text/html"
    assert stored.size_bytes == 4096
    assert stored.created_at is not None


@pytest.mark.integration
async def test_iteration_record_round_trips_metrics_and_cost():
    agent, run = await _agent_and_run()
    record = IterationRecord(
        agent_id=agent.id,
        run_id=run.id,
        iteration=14,
        action="shell",
        command="npx playwright test tests/api",
        result="3 failed, 41 passed",
        next_action="Analyze the three failures",
        model="claude-sonnet-5",
        input_tokens=1200,
        output_tokens=340,
        cost_usd=Decimal("0.018420"),
    )
    async with session_scope() as session:
        session.add(record)
    record_id = record.id

    async with session_scope() as session:
        stored = await session.get(IterationRecord, record_id)

    assert stored.model == "claude-sonnet-5"
    assert stored.input_tokens == 1200
    assert stored.output_tokens == 340
    assert stored.cost_usd == Decimal("0.018420")
    assert stored.task_id is None


@pytest.mark.integration
async def test_iteration_record_may_reference_a_task():
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

    record = IterationRecord(
        agent_id=agent.id, run_id=run.id, iteration=0, action="shell", task_id=task.id
    )
    async with session_scope() as session:
        session.add(record)
    record_id = record.id

    async with session_scope() as session:
        stored_task = await session.get(Task, task.id)
        await session.delete(stored_task)

    async with session_scope() as session:
        stored = await session.get(IterationRecord, record_id)

    assert stored is not None
    assert stored.task_id is None


@pytest.mark.integration
async def test_deleting_the_parent_agent_deletes_the_artifact_and_iteration_record():
    agent, run = await _agent_and_run()
    artifact = Artifact(
        agent_id=agent.id,
        run_id=run.id,
        kind="log",
        name="run.log",
        path="/workspace/artifacts/run.log",
        content_type="text/plain",
        size_bytes=10,
    )
    record = IterationRecord(agent_id=agent.id, run_id=run.id, iteration=0, action="shell")
    async with session_scope() as session:
        session.add_all([artifact, record])
    artifact_id, record_id = artifact.id, record.id

    async with session_scope() as session:
        stored_agent = await session.get(Agent, agent.id)
        await session.delete(stored_agent)

    async with session_scope() as session:
        assert await session.get(Artifact, artifact_id) is None
        assert await session.get(IterationRecord, record_id) is None


@pytest.mark.integration
async def test_deleting_the_parent_run_deletes_the_artifact_and_iteration_record():
    agent, run = await _agent_and_run()
    artifact = Artifact(
        agent_id=agent.id,
        run_id=run.id,
        kind="log",
        name="run.log",
        path="/workspace/artifacts/run.log",
        content_type="text/plain",
        size_bytes=10,
    )
    record = IterationRecord(agent_id=agent.id, run_id=run.id, iteration=0, action="shell")
    async with session_scope() as session:
        session.add_all([artifact, record])
    artifact_id, record_id = artifact.id, record.id

    async with session_scope() as session:
        stored_run = await session.get(Run, run.id)
        await session.delete(stored_run)

    async with session_scope() as session:
        assert await session.get(Artifact, artifact_id) is None
        assert await session.get(IterationRecord, record_id) is None
