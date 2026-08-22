"""Integration tests for `POST /agents`."""

import uuid
from pathlib import Path

import pytest

from juicebox.persistence.database import session_scope
from juicebox.persistence.repositories import AgentRepository

EXAMPLES = Path(__file__).resolve().parents[2] / "examples"
DEFINITION = (EXAMPLES / "test-commander.agent.yaml").read_text()
OBJECTIVE = (EXAMPLES / "improve-api-tests.objective.yaml").read_text()


@pytest.mark.integration
async def test_create_agent_returns_201_and_persists_the_row(client):
    response = await client.post("/agents", content=DEFINITION + "---\n" + OBJECTIVE)

    assert response.status_code == 201
    payload = response.json()
    assert "id" in payload
    assert payload["status"] == "created"

    async with session_scope() as session:
        agent = await AgentRepository.get(session, uuid.UUID(payload["id"]))
    assert agent is not None
    assert agent.name == "test-commander"
    assert agent.repository_url == "https://github.com/example/application"
    assert agent.base_branch == "juicebox/test-commander"


@pytest.mark.integration
async def test_create_agent_rejects_a_malformed_definition(client):
    bad_definition = DEFINITION.replace("juicebox.ai/v1", "juicebox.ai/v2")
    response = await client.post("/agents", content=bad_definition + "---\n" + OBJECTIVE)

    assert response.status_code == 422
    detail = response.json()["detail"]
    assert detail[0]["loc"] == ["apiVersion"]


@pytest.mark.integration
async def test_create_agent_rejects_a_single_document_body(client):
    response = await client.post("/agents", content=DEFINITION)

    assert response.status_code == 422


@pytest.mark.integration
async def test_every_422_body_has_the_same_shape(client):
    """A client parsing detail[0]["msg"] must not meet a bare string.

    Indexing a string yields a character rather than raising, so an
    inconsistent shape here corrupts a client silently instead of failing.
    """
    bodies = [
        DEFINITION,
        DEFINITION.replace("juicebox.ai/v1", "juicebox.ai/v2") + "---\n" + OBJECTIVE,
        "apiVersion: [unclosed\n",
    ]
    for body in bodies:
        response = await client.post("/agents", content=body)
        assert response.status_code == 422, body
        detail = response.json()["detail"]
        assert isinstance(detail, list), detail
        assert isinstance(detail[0], dict), detail
        assert set(detail[0]) == {"loc", "msg", "type"}
        assert isinstance(detail[0]["loc"], list)
