"""Unit tests pinning the status enums to the specification's state lists."""

from juicebox.persistence.models import AgentStatus, RunStatus

# Specification section 6, the agent lifecycle, verbatim and in order.
SECTION_6_STATES = [
    "CREATED",
    "STARTING",
    "RUNNING",
    "PAUSED",
    "WAITING",
    "COMPLETED",
    "FAILED",
    "STOPPED",
]


def test_agent_status_holds_the_section_6_states():
    assert [member.name for member in AgentStatus] == SECTION_6_STATES
    assert [member.value for member in AgentStatus] == SECTION_6_STATES


def test_run_status_holds_every_agent_state_except_created():
    expected = [state for state in SECTION_6_STATES if state != "CREATED"]
    assert [member.name for member in RunStatus] == expected
    assert [member.value for member in RunStatus] == expected
