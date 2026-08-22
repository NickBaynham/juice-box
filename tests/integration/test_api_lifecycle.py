"""Integration tests for `POST /agents/{agent_id}/start` and `.../stop`."""

import uuid
from pathlib import Path

import pytest

from juicebox.persistence.database import session_scope
from juicebox.persistence.repositories import RunRepository

EXAMPLES = Path(__file__).resolve().parents[2] / "examples"
DEFINITION = (EXAMPLES / "test-commander.agent.yaml").read_text()
OBJECTIVE = (EXAMPLES / "improve-api-tests.objective.yaml").read_text()


async def _create_agent(client) -> str:
    response = await client.post("/agents", content=DEFINITION + "---\n" + OBJECTIVE)
    return response.json()["id"]


@pytest.mark.integration
async def test_start_agent_transitions_to_starting_and_creates_attempt_one(client):
    agent_id = await _create_agent(client)

    response = await client.post(f"/agents/{agent_id}/start")

    assert response.status_code == 200
    assert response.json()["status"] == "starting"

    async with session_scope() as session:
        run = await RunRepository.get_current(session, uuid.UUID(agent_id))
    assert run is not None
    assert run.attempt == 1


@pytest.mark.integration
async def test_start_agent_twice_is_a_409_naming_status_and_action(client):
    agent_id = await _create_agent(client)
    await client.post(f"/agents/{agent_id}/start")

    response = await client.post(f"/agents/{agent_id}/start")

    assert response.status_code == 409
    assert response.json() == {"detail": "cannot start an agent that is starting"}


@pytest.mark.integration
async def test_stop_agent_transitions_to_stopped(client):
    agent_id = await _create_agent(client)
    await client.post(f"/agents/{agent_id}/start")

    response = await client.post(f"/agents/{agent_id}/stop")

    assert response.status_code == 200
    assert response.json()["status"] == "stopped"


@pytest.mark.integration
async def test_start_agent_returns_404_for_an_absent_agent(client):
    response = await client.post(f"/agents/{uuid.uuid4()}/start")

    assert response.status_code == 404
    assert response.json() == {"detail": "agent not found"}


@pytest.mark.integration
async def test_stop_agent_returns_404_for_an_absent_agent(client):
    response = await client.post(f"/agents/{uuid.uuid4()}/stop")

    assert response.status_code == 404
    assert response.json() == {"detail": "agent not found"}
