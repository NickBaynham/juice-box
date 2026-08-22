"""Integration tests for `GET /agents`, `GET /agents/{agent_id}`, and delete."""

import uuid
from pathlib import Path

import pytest

EXAMPLES = Path(__file__).resolve().parents[2] / "examples"
DEFINITION = (EXAMPLES / "test-commander.agent.yaml").read_text()
OBJECTIVE = (EXAMPLES / "improve-api-tests.objective.yaml").read_text()


async def _create_agent(client) -> str:
    response = await client.post("/agents", content=DEFINITION + "---\n" + OBJECTIVE)
    return response.json()["id"]


@pytest.mark.integration
async def test_list_agents_returns_them_newest_first(client):
    ids = [await _create_agent(client) for _ in range(3)]

    response = await client.get("/agents")

    assert response.status_code == 200
    payload = response.json()
    assert [row["id"] for row in payload] == list(reversed(ids))


@pytest.mark.integration
async def test_list_agents_honours_limit_and_offset(client):
    ids = [await _create_agent(client) for _ in range(3)]

    response = await client.get("/agents", params={"limit": 1, "offset": 1})

    assert response.status_code == 200
    payload = response.json()
    assert len(payload) == 1
    assert payload[0]["id"] == ids[1]


@pytest.mark.integration
async def test_list_agents_rejects_a_negative_limit(client):
    response = await client.get("/agents", params={"limit": -1})

    assert response.status_code == 422


@pytest.mark.integration
async def test_get_agent_returns_one_agent_with_a_lowercase_status(client):
    agent_id = await _create_agent(client)

    response = await client.get(f"/agents/{agent_id}")

    assert response.status_code == 200
    payload = response.json()
    assert payload["id"] == agent_id
    assert payload["status"] == "created"


@pytest.mark.integration
async def test_get_agent_returns_404_for_an_absent_but_valid_uuid(client):
    """The body is asserted, not just the status.

    Starlette answers an unmatched path with its own 404, so a status-only
    assertion passes even with the route deleted, and passes again if the
    handler returns 404 for every id including agents that exist.
    """
    response = await client.get(f"/agents/{uuid.uuid4()}")

    assert response.status_code == 404
    assert response.json() == {"detail": "agent not found"}


@pytest.mark.integration
async def test_get_agent_returns_422_for_a_malformed_id(client):
    response = await client.get("/agents/not-a-uuid")

    assert response.status_code == 422


@pytest.mark.integration
async def test_delete_agent_returns_204_and_the_agent_is_gone(client):
    agent_id = await _create_agent(client)

    # Fetch before deleting, so the 404 afterwards means the delete worked
    # rather than that the handler answers 404 unconditionally.
    assert (await client.get(f"/agents/{agent_id}")).status_code == 200

    response = await client.delete(f"/agents/{agent_id}")
    assert response.status_code == 204

    follow_up = await client.get(f"/agents/{agent_id}")
    assert follow_up.status_code == 404
    assert follow_up.json() == {"detail": "agent not found"}


@pytest.mark.integration
async def test_delete_agent_is_idempotent_for_an_absent_agent(client):
    response = await client.delete(f"/agents/{uuid.uuid4()}")

    assert response.status_code == 204
