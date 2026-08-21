"""Agent definition envelope: specification section 8."""

from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, StringConstraints, field_validator

NAME_PATTERN = r"^[a-z0-9][a-z0-9-]*$"

# Skill and secret names are both identifiers something later resolves: a
# skill becomes a directory lookup in W7, a secret a lookup in a backend.
SlugName = Annotated[str, StringConstraints(pattern=NAME_PATTERN)]


class Metadata(BaseModel):
    """Identifying information for an agent definition.

    `name` must be safe for W6 to derive a work branch and a container
    name from directly.
    """

    model_config = ConfigDict(extra="forbid")

    name: str = Field(pattern=NAME_PATTERN)


class ModelSpec(BaseModel):
    """Which model provider and model an agent runs on."""

    model_config = ConfigDict(extra="forbid")

    provider: str
    model: str


class AgentSpec(BaseModel):
    """The `agent:` block of the definition."""

    model_config = ConfigDict(extra="forbid")

    model: ModelSpec
    system_prompt: str

    @field_validator("system_prompt")
    @classmethod
    def _strip_and_require_nonempty(cls, value: str) -> str:
        stripped = value.strip()
        if not stripped:
            raise ValueError("system_prompt must not be empty")
        return stripped


class AgentDefinition(BaseModel):
    """The full agent document envelope."""

    model_config = ConfigDict(extra="forbid")

    api_version: Literal["juicebox.ai/v1"] = Field(alias="apiVersion")
    kind: Literal["Agent"]
    metadata: Metadata
    agent: AgentSpec
    skills: list[SlugName] = []
    secrets: list[SlugName] = []
