"""The agent lifecycle state machine: specification section 6.

Pure and stateless — no HTTP, no database. `TRANSITIONS` covers the
caller-initiated actions section 21 exposes as routes; `next_status` looks
a `(current, action)` pair up in it and raises on a missing key.
`is_legal` answers a broader question over states alone, so W9 can check
the system transitions no caller action names (`starting -> running`,
`running -> completed`, `running -> failed`) instead of calling
`set_status` directly.
"""

from enum import StrEnum

from juicebox.persistence.models import AgentStatus


class LifecycleAction(StrEnum):
    """The caller-initiated lifecycle operations of specification section 6."""

    START = "start"
    STOP = "stop"
    RESTART = "restart"
    PAUSE = "pause"
    RESUME = "resume"


class IllegalTransition(Exception):
    """Raised when `action` is not legal from `current`.

    Carries both in its message so a 409 body can quote them.
    """

    def __init__(self, current: AgentStatus, action: LifecycleAction):
        super().__init__(f"cannot {action} an agent that is {current}")


# The seven caller-initiated edges. `starting -> stopped` is not in
# specification section 6's diagram: nothing advances an agent out of
# `starting` until W9 exists, so without this edge every started agent
# would be unstoppable until then. `failed -> starting` and
# `stopped -> starting` are restart edges required by ADR-0002 even
# though section 6 draws those states as terminal.
TRANSITIONS: dict[tuple[AgentStatus, LifecycleAction], AgentStatus] = {
    (AgentStatus.CREATED, LifecycleAction.START): AgentStatus.STARTING,
    (AgentStatus.STARTING, LifecycleAction.STOP): AgentStatus.STOPPED,
    (AgentStatus.RUNNING, LifecycleAction.PAUSE): AgentStatus.PAUSED,
    (AgentStatus.RUNNING, LifecycleAction.STOP): AgentStatus.STOPPED,
    (AgentStatus.PAUSED, LifecycleAction.RESUME): AgentStatus.RUNNING,
    (AgentStatus.FAILED, LifecycleAction.RESTART): AgentStatus.STARTING,
    (AgentStatus.STOPPED, LifecycleAction.RESTART): AgentStatus.STARTING,
}

# The system transitions no caller action names, performed by W9 rather
# than a route.
_SYSTEM_EDGES: set[tuple[AgentStatus, AgentStatus]] = {
    (AgentStatus.STARTING, AgentStatus.RUNNING),
    (AgentStatus.RUNNING, AgentStatus.COMPLETED),
    (AgentStatus.RUNNING, AgentStatus.FAILED),
}

_LEGAL_EDGES: set[tuple[AgentStatus, AgentStatus]] = _SYSTEM_EDGES | {
    (current, target) for (current, _action), target in TRANSITIONS.items()
}


def next_status(current: AgentStatus, action: LifecycleAction) -> AgentStatus:
    """The status `action` moves an agent to from `current`.

    Raises `IllegalTransition` if `(current, action)` has no edge.
    """
    try:
        return TRANSITIONS[(current, action)]
    except KeyError:
        raise IllegalTransition(current, action) from None


def is_legal(current: AgentStatus, target: AgentStatus) -> bool:
    """Whether `current -> target` is an edge in the full lifecycle graph,
    caller-initiated or system-performed."""
    return (current, target) in _LEGAL_EDGES
