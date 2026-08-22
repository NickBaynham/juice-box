"""Lifecycle state machine: whether an agent status transition is legal."""

from juicebox.lifecycle.transitions import (
    IllegalTransition,
    LifecycleAction,
    is_legal,
    next_status,
)

__all__ = ["IllegalTransition", "LifecycleAction", "is_legal", "next_status"]
