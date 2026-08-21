"""YAML entry points for the declarative schemas."""

import yaml

from juicebox.schemas.agent import AgentDefinition


def load_agent_definition(document: str) -> AgentDefinition:
    """Parse and validate an agent definition document.

    Raises `yaml.YAMLError` on malformed YAML and
    `pydantic.ValidationError` on a document that is not a valid Juice Box
    agent. Both propagate to the caller; W3 maps them to a 422 response.
    """
    return AgentDefinition.model_validate(yaml.safe_load(document))
