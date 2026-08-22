"""YAML entry points for the declarative schemas."""

import yaml

from juicebox.schemas.agent import AgentDefinition
from juicebox.schemas.objective import Objective, ObjectiveDocument


def load_agent_definition(document: str) -> AgentDefinition:
    """Parse and validate an agent definition document.

    Raises `yaml.YAMLError` on malformed YAML and
    `pydantic.ValidationError` on a document that is not a valid Juice Box
    agent. Both propagate to the caller; W3 maps them to a 422 response.
    """
    return AgentDefinition.model_validate(yaml.safe_load(document))


def load_objective(document: str) -> Objective:
    """Parse and validate an objective document.

    Validates through `ObjectiveDocument` rather than subscripting the
    parsed mapping, so a document missing the `objective:` key, or one
    that is a top-level list or empty, raises `pydantic.ValidationError`
    instead of `KeyError` or `TypeError`, neither of which W3 could map
    to a 422.

    Errors inside an objective carry an `("objective", ...)` `loc`
    prefix. A document that is not a mapping at all reports `loc == ()`,
    so a caller building a 422 body cannot assume a non-empty `loc`.
    """
    return ObjectiveDocument.model_validate(yaml.safe_load(document)).objective
