"""Agent definition envelope: specification section 8."""

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

NAME_PATTERN = r"^[a-z0-9][a-z0-9-]*$"


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


class AgentDefinition(BaseModel):
    """The full agent document envelope."""

    model_config = ConfigDict(extra="forbid")

    api_version: Literal["juicebox.ai/v1"] = Field(alias="apiVersion")
    kind: Literal["Agent"]
    metadata: Metadata
    agent: AgentSpec
