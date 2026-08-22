import pytest

from juicebox.lifecycle.transitions import (
    IllegalTransition,
    LifecycleAction,
    is_legal,
    next_status,
)
from juicebox.persistence.models import AgentStatus


@pytest.mark.parametrize(
    ("current", "action", "expected"),
    [
        (AgentStatus.CREATED, LifecycleAction.START, AgentStatus.STARTING),
        (AgentStatus.RUNNING, LifecycleAction.PAUSE, AgentStatus.PAUSED),
        (AgentStatus.PAUSED, LifecycleAction.RESUME, AgentStatus.RUNNING),
        (AgentStatus.RUNNING, LifecycleAction.STOP, AgentStatus.STOPPED),
        (AgentStatus.STARTING, LifecycleAction.STOP, AgentStatus.STOPPED),
        (AgentStatus.FAILED, LifecycleAction.RESTART, AgentStatus.STARTING),
        (AgentStatus.STOPPED, LifecycleAction.RESTART, AgentStatus.STARTING),
    ],
)
def test_legal_transitions(current, action, expected):
    assert next_status(current, action) is expected


@pytest.mark.parametrize(
    ("current", "action"),
    [
        (AgentStatus.CREATED, LifecycleAction.PAUSE),
        (AgentStatus.COMPLETED, LifecycleAction.RESTART),
        (AgentStatus.COMPLETED, LifecycleAction.START),
        (AgentStatus.RUNNING, LifecycleAction.START),
        (AgentStatus.PAUSED, LifecycleAction.PAUSE),
    ],
)
def test_illegal_transitions_raise(current, action):
    with pytest.raises(IllegalTransition) as caught:
        next_status(current, action)
    assert current.value in str(caught.value)
    assert action.value in str(caught.value)


def test_completed_is_terminal_for_every_action():
    for action in LifecycleAction:
        with pytest.raises(IllegalTransition):
            next_status(AgentStatus.COMPLETED, action)


def test_no_action_reaches_waiting():
    """No caller action reaches WAITING. ADR-0004 has approval-gated
    operations fail closed rather than suspend, so nothing in the MVP
    enters it; the state exists because section 6 defines it and Phase 2
    will use it. This proves the transition table has no edge into WAITING,
    not that the column can never hold it; W9 could still set it directly,
    which is why decision 6 gives W9 `is_legal` to ask instead."""
    reachable = set()
    for current in AgentStatus:
        for action in LifecycleAction:
            try:
                reachable.add(next_status(current, action))
            except IllegalTransition:
                pass
    assert reachable, "no transition is legal; the table is empty"
    assert AgentStatus.WAITING not in reachable


def test_is_legal_true_for_a_system_transition():
    """`starting -> running` names no `LifecycleAction`; W9 performs it and
    asks `is_legal` rather than calling `set_status` directly."""
    assert is_legal(AgentStatus.STARTING, AgentStatus.RUNNING)


def test_is_legal_false_for_an_edge_not_in_the_table():
    assert not is_legal(AgentStatus.CREATED, AgentStatus.RUNNING)
