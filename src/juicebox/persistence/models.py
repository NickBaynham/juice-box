"""Declarative base, lifecycle status enums, and the agent, run, and task tables."""

import uuid
from datetime import datetime
from enum import StrEnum
from typing import Annotated, Any

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    """Declarative base whose metadata Alembic autogenerates migrations from."""


class AgentStatus(StrEnum):
    """The agent lifecycle states of specification section 6, stored
    lowercase like every other status column even though section 6's
    ASCII diagram renders them uppercase; that diagram never appears in
    an API payload, unlike section 11's task JSON example."""

    CREATED = "created"
    STARTING = "starting"
    RUNNING = "running"
    PAUSED = "paused"
    WAITING = "waiting"
    COMPLETED = "completed"
    FAILED = "failed"
    STOPPED = "stopped"


class RunStatus(StrEnum):
    """The states one run attempt can occupy; a run is never CREATED."""

    STARTING = "starting"
    RUNNING = "running"
    PAUSED = "paused"
    WAITING = "waiting"
    COMPLETED = "completed"
    FAILED = "failed"
    STOPPED = "stopped"


class TaskStatus(StrEnum):
    """The task states of specification section 11."""

    PENDING = "pending"
    READY = "ready"
    RUNNING = "running"
    BLOCKED = "blocked"
    WAITING = "waiting"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class TaskPriority(StrEnum):
    """A task's scheduling priority."""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


def status_check(column: str, statuses: type[StrEnum], name: str) -> CheckConstraint:
    """Return a CHECK constraint restricting `column` to `statuses`' values.

    Status columns are plain strings guarded by a CHECK rather than native
    PostgreSQL enum types, which survive DROP TABLE and make a downgrade
    followed by an upgrade fail with DuplicateObjectError.
    """
    allowed = ", ".join(f"'{status.value}'" for status in statuses)
    return CheckConstraint(f"{column} IN ({allowed})", name=name)


UuidPk = Annotated[uuid.UUID, mapped_column(primary_key=True, default=uuid.uuid4)]
CreatedAt = Annotated[
    datetime, mapped_column(DateTime(timezone=True), server_default=func.now())
]
UpdatedAt = Annotated[
    datetime,
    mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    ),
]
# started_at and finished_at record events that may not have happened yet, so
# they are nullable and carry no default.
OptionalAt = Annotated[datetime | None, mapped_column(DateTime(timezone=True))]
Json = Annotated[dict[str, Any], mapped_column(JSONB)]


class Agent(Base):
    """An agent: its definition, objective, repository, and lifecycle status."""

    __tablename__ = "agent"
    __table_args__ = (status_check("status", AgentStatus, "ck_agent_status"),)

    id: Mapped[UuidPk]
    name: Mapped[str]
    definition: Mapped[Json]
    objective: Mapped[Json]
    repository_url: Mapped[str | None]
    base_branch: Mapped[str | None]
    work_branch: Mapped[str | None]
    status: Mapped[str] = mapped_column(default=AgentStatus.CREATED.value)
    failure_reason: Mapped[str | None]
    created_at: Mapped[CreatedAt]
    updated_at: Mapped[UpdatedAt]
    started_at: Mapped[OptionalAt]
    finished_at: Mapped[OptionalAt]


class Run(Base):
    """One numbered attempt at an agent's objective, per ADR-0006."""

    __tablename__ = "run"
    __table_args__ = (
        UniqueConstraint("agent_id", "attempt", name="uq_run_agent_attempt"),
        status_check("status", RunStatus, "ck_run_status"),
    )

    id: Mapped[UuidPk]
    agent_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("agent.id", ondelete="CASCADE")
    )
    attempt: Mapped[int]
    status: Mapped[str]
    iteration_count: Mapped[int] = mapped_column(default=0)
    current_task_id: Mapped[uuid.UUID | None]
    checkpoint: Mapped[Json | None]
    failure_reason: Mapped[str | None]
    started_at: Mapped[OptionalAt]
    finished_at: Mapped[OptionalAt]
    created_at: Mapped[CreatedAt]
    updated_at: Mapped[UpdatedAt]


class Task(Base):
    """One node in the task graph an agent decomposes its objective into."""

    __tablename__ = "task"
    __table_args__ = (
        status_check("status", TaskStatus, "ck_task_status"),
        status_check("priority", TaskPriority, "ck_task_priority"),
    )

    id: Mapped[UuidPk]
    agent_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("agent.id", ondelete="CASCADE")
    )
    run_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("run.id", ondelete="CASCADE"))
    title: Mapped[str]
    status: Mapped[str] = mapped_column(default=TaskStatus.PENDING.value)
    priority: Mapped[str]
    dependencies: Mapped[list[str]] = mapped_column(JSONB)
    attempts: Mapped[int] = mapped_column(default=0)
    result: Mapped[Json | None]
    error: Mapped[str | None]
    created_at: Mapped[CreatedAt]
    updated_at: Mapped[UpdatedAt]
    started_at: Mapped[OptionalAt]
    finished_at: Mapped[OptionalAt]
