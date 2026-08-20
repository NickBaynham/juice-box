"""Unit tests pinning the status enums to the specification's state lists."""

from juicebox.persistence.models import AgentStatus, RunStatus, TaskPriority, TaskStatus

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


# Specification section 11, task management, verbatim and in order. Section
# 11 renders task states lowercase, unlike section 6's uppercase agent
# lifecycle, so TaskStatus follows suit rather than inventing a third
# convention.
SECTION_11_STATES = [
    "pending",
    "ready",
    "running",
    "blocked",
    "waiting",
    "completed",
    "failed",
    "cancelled",
]


def test_task_status_holds_the_section_11_states():
    assert [member.value for member in TaskStatus] == SECTION_11_STATES


def test_task_priority_holds_low_medium_high():
    assert [member.value for member in TaskPriority] == ["low", "medium", "high"]
