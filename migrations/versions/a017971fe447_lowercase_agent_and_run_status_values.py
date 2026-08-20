"""lowercase agent and run status values

Revision ID: a017971fe447
Revises: d87365651814
Create Date: 2026-08-20 14:15:27.308905

"""
from collections.abc import Sequence

from alembic import op

# revision identifiers, used by Alembic.
revision: str = 'a017971fe447'
down_revision: str | Sequence[str] | None = 'd87365651814'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

AGENT_STATUSES_UPPER = "'CREATED', 'STARTING', 'RUNNING', 'PAUSED', 'WAITING', 'COMPLETED', 'FAILED', 'STOPPED'"
AGENT_STATUSES_LOWER = "'created', 'starting', 'running', 'paused', 'waiting', 'completed', 'failed', 'stopped'"
RUN_STATUSES_UPPER = "'STARTING', 'RUNNING', 'PAUSED', 'WAITING', 'COMPLETED', 'FAILED', 'STOPPED'"
RUN_STATUSES_LOWER = "'starting', 'running', 'paused', 'waiting', 'completed', 'failed', 'stopped'"


def upgrade() -> None:
    """Lowercase agent and run status values, unifying them with task's."""
    op.drop_constraint("ck_agent_status", "agent", type_="check")
    op.drop_constraint("ck_run_status", "run", type_="check")

    op.execute("UPDATE agent SET status = lower(status)")
    op.execute("UPDATE run SET status = lower(status)")

    op.create_check_constraint("ck_agent_status", "agent", f"status IN ({AGENT_STATUSES_LOWER})")
    op.create_check_constraint("ck_run_status", "run", f"status IN ({RUN_STATUSES_LOWER})")


def downgrade() -> None:
    """Restore uppercase agent and run status values and constraints."""
    op.drop_constraint("ck_agent_status", "agent", type_="check")
    op.drop_constraint("ck_run_status", "run", type_="check")

    op.execute("UPDATE agent SET status = upper(status)")
    op.execute("UPDATE run SET status = upper(status)")

    op.create_check_constraint("ck_agent_status", "agent", f"status IN ({AGENT_STATUSES_UPPER})")
    op.create_check_constraint("ck_run_status", "run", f"status IN ({RUN_STATUSES_UPPER})")
