from datetime import timedelta

import pytest
from pydantic import ValidationError

from juicebox.schemas.agent import FilesystemAccess, Permissions, Runtime
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


def test_parses_memory_and_timeout():
    runtime = Runtime.model_validate({"cpu": 2, "memory": "4Gi", "timeout": "8h"})
    assert runtime.memory_bytes == 4 * 1024**3
    assert runtime.timeout_delta == timedelta(hours=8)


@pytest.mark.parametrize("memory", ["4GB", "4 Gi", "Gi", "-1Gi"])
def test_rejects_malformed_memory(memory):
    with pytest.raises(ValidationError) as caught:
        Runtime.model_validate({"cpu": 2, "memory": memory, "timeout": "8h"})
    assert caught.value.errors()[0]["loc"] == ("memory",)


@pytest.mark.parametrize("timeout", ["8 hours", "8H", "h", "-1h"])
def test_rejects_malformed_timeout(timeout):
    with pytest.raises(ValidationError) as caught:
        Runtime.model_validate({"cpu": 2, "memory": "4Gi", "timeout": timeout})
    assert caught.value.errors()[0]["loc"] == ("timeout",)


def test_rejects_zero_cpu():
    with pytest.raises(ValidationError) as caught:
        Runtime.model_validate({"cpu": 0, "memory": "4Gi", "timeout": "8h"})
    assert caught.value.errors()[0]["loc"] == ("cpu",)


def test_permissions_default_to_least_privilege():
    permissions = Permissions.model_validate({})
    assert permissions.filesystem is FilesystemAccess.READ_ONLY
    assert permissions.network is False
    assert permissions.shell is False


def test_rejects_an_unknown_filesystem_mode():
    with pytest.raises(ValidationError) as caught:
        Permissions.model_validate({"filesystem": "read-write-execute"})
    assert caught.value.errors()[0]["loc"] == ("filesystem",)


def test_a_document_without_permissions_is_least_privileged():
    """The default must survive being wired onto the document.

    An implementer who writes `permissions: Permissions | None = None`
    hands W6 a None meaning unrestricted, which is the ADR-0004 failure.
    """
    definition = load_agent_definition(MINIMAL)
    assert definition.permissions.filesystem is FilesystemAccess.READ_ONLY
    assert definition.permissions.network is False
    assert definition.runtime is None


@pytest.mark.parametrize("memory", ["4Gi\n", "4Gi\r\n"])
def test_rejects_memory_with_a_trailing_newline(memory):
    """`$` matches before a trailing newline; a YAML block scalar produces one."""
    with pytest.raises(ValidationError) as caught:
        Runtime.model_validate({"cpu": 2, "memory": memory, "timeout": "8h"})
    assert caught.value.errors()[0]["loc"] == ("memory",)
