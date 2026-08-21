import pytest
import yaml
from pydantic import ValidationError

from juicebox.schemas.loading import load_agent_definition

MINIMAL = """
apiVersion: juicebox.ai/v1
kind: Agent
metadata:
  name: test-commander
agent:
  model:
    provider: anthropic
    model: claude-sonnet
  system_prompt: Be useful.
"""


def test_loads_a_minimal_definition():
    definition = load_agent_definition(MINIMAL)
    assert definition.metadata.name == "test-commander"


def test_rejects_a_wrong_api_version():
    document = MINIMAL.replace("juicebox.ai/v1", "juicebox.ai/v2")
    with pytest.raises(ValidationError) as caught:
        load_agent_definition(document)
    assert caught.value.errors()[0]["loc"] == ("apiVersion",)


def test_rejects_an_unknown_field():
    with pytest.raises(ValidationError) as caught:
        load_agent_definition(MINIMAL + "\nunexpected: value\n")
    assert caught.value.errors()[0]["loc"] == ("unexpected",)


def test_propagates_a_yaml_syntax_error():
    with pytest.raises(yaml.YAMLError):
        load_agent_definition("apiVersion: [unclosed\n")
