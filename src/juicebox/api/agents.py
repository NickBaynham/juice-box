"""Agent routes: specification section 21."""

import uuid
from datetime import datetime
from typing import Annotated

import yaml
from fastapi import APIRouter, Depends, HTTPException, Query, Request
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from juicebox.api.dependencies import get_session
from juicebox.lifecycle.transitions import (
    IllegalTransition,
    LifecycleAction,
    next_status,
)
from juicebox.persistence.repositories import AgentRepository, RunRepository
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
async def delete_agent(agent_id: uuid.UUID, session: SessionDependency) -> None:
    """Delete an agent. Deleting an absent agent is a no-op: still 204."""
    await AgentRepository.delete(session, agent_id)


async def _apply_lifecycle_action(
    agent_id: uuid.UUID, action: LifecycleAction, session: SessionDependency
) -> AgentSummary:
    """Move an agent through `action`, 404 if absent, 409 if illegal.

    `START` and `RESTART` also create the agent's next run attempt.
    Shared by every lifecycle route so each one is a decorator naming its
    action, not a repeated body.
    """
    agent = await AgentRepository.get(session, agent_id)
    if agent is None:
        raise HTTPException(status_code=404, detail="agent not found")

    try:
        status = next_status(agent.status, action)
    except IllegalTransition as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc

    agent = await AgentRepository.set_status(session, agent_id, status)
    if action in (LifecycleAction.START, LifecycleAction.RESTART):
        await RunRepository.create_attempt(session, agent_id)
    return AgentSummary.model_validate(agent)


@router.post("/agents/{agent_id}/start")
async def start_agent(agent_id: uuid.UUID, session: SessionDependency) -> AgentSummary:
    """Start an agent, creating its first run attempt."""
    return await _apply_lifecycle_action(agent_id, LifecycleAction.START, session)


@router.post("/agents/{agent_id}/stop")
async def stop_agent(agent_id: uuid.UUID, session: SessionDependency) -> AgentSummary:
    """Stop an agent."""
    return await _apply_lifecycle_action(agent_id, LifecycleAction.STOP, session)


@router.post("/agents/{agent_id}/pause")
async def pause_agent(agent_id: uuid.UUID, session: SessionDependency) -> AgentSummary:
    """Pause a running agent."""
    return await _apply_lifecycle_action(agent_id, LifecycleAction.PAUSE, session)


@router.post("/agents/{agent_id}/resume")
async def resume_agent(agent_id: uuid.UUID, session: SessionDependency) -> AgentSummary:
    """Resume a paused agent."""
    return await _apply_lifecycle_action(agent_id, LifecycleAction.RESUME, session)


@router.post("/agents/{agent_id}/restart")
async def restart_agent(agent_id: uuid.UUID, session: SessionDependency) -> AgentSummary:
    """Restart a failed or stopped agent, creating a fresh run attempt."""
    return await _apply_lifecycle_action(agent_id, LifecycleAction.RESTART, session)
