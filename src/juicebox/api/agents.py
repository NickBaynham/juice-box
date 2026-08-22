"""Agent routes: specification section 21."""

from typing import Annotated

import yaml
from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.ext.asyncio import AsyncSession

from juicebox.api.dependencies import get_session
from juicebox.persistence.repositories import AgentRepository
from juicebox.schemas.agent import AgentDefinition
from juicebox.schemas.objective import ObjectiveDocument

router = APIRouter()

SessionDependency = Annotated[AsyncSession, Depends(get_session)]


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
            detail=f"expected exactly two YAML documents, got {len(documents)}",
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
