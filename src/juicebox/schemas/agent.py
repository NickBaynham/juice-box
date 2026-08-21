"""Agent definition envelope: specification section 8."""

import re
from datetime import timedelta
from enum import StrEnum
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, StringConstraints, field_validator

NAME_PATTERN = r"^[a-z0-9][a-z0-9-]*$"
MEMORY_PATTERN = re.compile(r"^(\d+)(Ki|Mi|Gi|Ti)$")
TIMEOUT_PATTERN = re.compile(r"^(\d+)(s|m|h)$")
MEMORY_MULTIPLIERS = {"Ki": 1024, "Mi": 1024**2, "Gi": 1024**3, "Ti": 1024**4}
TIMEOUT_UNITS = {"s": "seconds", "m": "minutes", "h": "hours"}

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


class Runtime(BaseModel):
    """The `runtime:` block: container sizing for an agent's execution.

    `memory` and `timeout` are strings with units (`4Gi`, `8h`) rather than
    bare numbers, since the specification never writes a bare number and a
    bare `memory: 4` is ambiguous about its unit.
    """

    model_config = ConfigDict(extra="forbid")

    cpu: float = Field(gt=0)
    memory: str
    timeout: str

    @field_validator("memory")
    @classmethod
    def _validate_memory(cls, value: str) -> str:
        if not MEMORY_PATTERN.match(value):
            raise ValueError("memory must match \\d+(Ki|Mi|Gi|Ti), e.g. 4Gi")
        return value

    @field_validator("timeout")
    @classmethod
    def _validate_timeout(cls, value: str) -> str:
        if not TIMEOUT_PATTERN.match(value):
            raise ValueError("timeout must match \\d+(s|m|h), e.g. 8h")
        return value

    @property
    def memory_bytes(self) -> int:
        """`memory` converted to bytes.

        A plain property, not `@computed_field`: a computed field appears
        in `model_dump()`, and under `extra="forbid"` the dumped document
        would no longer re-validate, breaking the round trip W3 needs when
        reading a definition back out of JSONB.
        """
        amount, unit = MEMORY_PATTERN.match(self.memory).groups()
        return int(amount) * MEMORY_MULTIPLIERS[unit]

    @property
    def timeout_delta(self) -> timedelta:
        """`timeout` converted to a `timedelta`. See `memory_bytes`."""
        amount, unit = TIMEOUT_PATTERN.match(self.timeout).groups()
        return timedelta(**{TIMEOUT_UNITS[unit]: int(amount)})


class FilesystemAccess(StrEnum):
    """The filesystem modes a running agent may be granted, per ADR-0009."""

    READ_ONLY = "read-only"
    READ_WRITE = "read-write"


class Permissions(BaseModel):
    """The `permissions:` block ADR-0004 enforces.

    Defaults are least privilege: an omitted block must not grant more
    access than a present one that spells out every field.
    """

    model_config = ConfigDict(extra="forbid")

    filesystem: FilesystemAccess = FilesystemAccess.READ_ONLY
    network: bool = False
    shell: bool = False


class AgentDefinition(BaseModel):
    """The full agent document envelope."""

    model_config = ConfigDict(extra="forbid")

    api_version: Literal["juicebox.ai/v1"] = Field(alias="apiVersion")
    kind: Literal["Agent"]
    metadata: Metadata
    agent: AgentSpec
    skills: list[SlugName] = []
    secrets: list[SlugName] = []
    runtime: Runtime | None = None
    permissions: Permissions = Permissions()
