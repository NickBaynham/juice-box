import pytest
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


def test_accepts_skills_and_secrets():
    definition = load_agent_definition(
        MINIMAL + "skills:\n  - git\n  - playwright\nsecrets:\n  - github-token\n"
    )
    assert definition.skills == ["git", "playwright"]
    assert definition.secrets == ["github-token"]


def test_defaults_skills_and_secrets_to_empty():
    definition = load_agent_definition(MINIMAL)
    assert definition.skills == []
    assert definition.secrets == []


def test_rejects_an_empty_system_prompt():
    document = MINIMAL.replace("system_prompt: Be useful.", 'system_prompt: "  "')
    with pytest.raises(ValidationError) as caught:
        load_agent_definition(document)
    assert caught.value.errors()[0]["loc"] == ("agent", "system_prompt")


def test_rejects_a_secret_name_that_is_not_a_slug():
    with pytest.raises(ValidationError) as caught:
        load_agent_definition(MINIMAL + "secrets:\n  - Github_Token\n")
    assert caught.value.errors()[0]["loc"] == ("secrets", 0)
