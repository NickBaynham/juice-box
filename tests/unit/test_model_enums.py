"""Unit tests pinning the status enums to the specification's state lists."""

from juicebox.persistence.models import AgentStatus, RunStatus, TaskPriority, TaskStatus

# Specification section 6, the agent lifecycle, verbatim and in order.
# Member names stay uppercase Python identifiers; stored values are
# lowercase like every other status column.
SECTION_6_NAMES = [
    "CREATED",
    "STARTING",
    "RUNNING",
    "PAUSED",
    "WAITING",
    "COMPLETED",
    "FAILED",
    "STOPPED",
]
SECTION_6_VALUES = [name.lower() for name in SECTION_6_NAMES]


def test_agent_status_holds_the_section_6_states():
    assert [member.name for member in AgentStatus] == SECTION_6_NAMES
    assert [member.value for member in AgentStatus] == SECTION_6_VALUES


def test_run_status_holds_every_agent_state_except_created():
    expected_names = [name for name in SECTION_6_NAMES if name != "CREATED"]
    expected_values = [name.lower() for name in expected_names]
    assert [member.name for member in RunStatus] == expected_names
    assert [member.value for member in RunStatus] == expected_values


# Specification section 11, task management, verbatim and in order.
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
