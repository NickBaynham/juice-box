"""Agent routes: specification section 21."""

import uuid
from datetime import datetime
from typing import Annotated

import yaml
from fastapi import APIRouter, Depends, HTTPException, Query, Request, Response
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from juicebox.api.dependencies import get_session
from juicebox.persistence.repositories import AgentRepository
from juicebox.schemas.agent import AgentDefinition
from juicebox.schemas.objective import ObjectiveDocument

router = APIRouter()

SessionDependency = Annotated[AsyncSession, Depends(get_session)]


class AgentSummary(BaseModel):
    """An agent as listed or fetched: no `definition` or `objective` blob."""

    model_config = {"from_attributes": True}

    id: uuid.UUID
    name: str
    status: str
    repository_url: str | None
    base_branch: str | None
    work_branch: str | None
    created_at: datetime
    updated_at: datetime
    started_at: datetime | None
    finished_at: datetime | None


@router.post("/agents", status_code=201)
async def create_agent(request: Request, session: SessionDependency) -> dict[str, str]:
    """Create an agent from a two-document body: a definition, then an objective.

    Parses the raw request body with `yaml.safe_load_all`; a body that is
    not exactly two documents is rejected. `pydantic.ValidationError` and
    `yaml.YAMLError` propagate to the handlers `create_app()` registers,
    which map both to a 422.
    """
    body = (await request.body()).decode()
    documents = list(yaml.safe_load_all(body))
    if len(documents) != 2:
        raise HTTPException(
            status_code=422,
            detail=[
                {
                    "loc": [],
                    "msg": (
                        "expected exactly two YAML documents, a definition and an "
                        f"objective, got {len(documents)}"
                    ),
                    "type": "document_count",
                }
            ],
        )

    definition = AgentDefinition.model_validate(documents[0])
    objective = ObjectiveDocument.model_validate(documents[1]).objective

    repository = definition.repository
    agent = await AgentRepository.create(
        session,
        definition.metadata.name,
        definition.model_dump(by_alias=True),
        objective.model_dump(),
        repository_url=repository.url if repository else None,
        base_branch=repository.branch if repository else None,
    )
    return {"id": str(agent.id), "status": agent.status}


@router.get("/agents")
async def list_agents(
    session: SessionDependency,
    limit: Annotated[int, Query(ge=1, le=200)] = 50,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> list[AgentSummary]:
    """List agents newest-created first, paged by `limit` and `offset`."""
    agents = await AgentRepository.list(session, limit=limit, offset=offset)
    return [AgentSummary.model_validate(agent) for agent in agents]


@router.get("/agents/{agent_id}")
async def get_agent(agent_id: uuid.UUID, session: SessionDependency) -> AgentSummary:
    """Return one agent, or a 404 if `agent_id` does not exist."""
    agent = await AgentRepository.get(session, agent_id)
    if agent is None:
        raise HTTPException(status_code=404, detail="agent not found")
    return AgentSummary.model_validate(agent)


@router.delete("/agents/{agent_id}", status_code=204)
async def delete_agent(agent_id: uuid.UUID, session: SessionDependency) -> Response:
    """Delete an agent. Deleting an absent agent is a no-op: still 204."""
    await AgentRepository.delete(session, agent_id)
    return Response(status_code=204)
