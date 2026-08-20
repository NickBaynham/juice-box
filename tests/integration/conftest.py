"""Shared fixtures for integration tests: schema at head, isolated rows."""

from pathlib import Path

import pytest
from sqlalchemy import text

from juicebox.persistence.database import session_scope

REPO_ROOT = Path(__file__).resolve().parents[2]
ALEMBIC_INI = REPO_ROOT / "alembic.ini"


@pytest.fixture(scope="session", autouse=True)
def schema_at_head():
    """Bring the database to the latest migration before the suite runs.

    A no-op until an increment adds `alembic.ini`; there is no migration
    to apply yet.
    """
    if not ALEMBIC_INI.exists():
        return

    from alembic import command
    from alembic.config import Config

    command.upgrade(Config(str(ALEMBIC_INI)), "head")


@pytest.fixture(autouse=True)
async def truncate_tables():
    """Truncate every table in `Base.metadata` before each test.

    Isolates tests from each other and from the persistent `db-data`
    Compose volume. A no-op until an increment adds
    `juicebox.persistence.models`; there are no tables to truncate yet.
    """
    try:
        from juicebox.persistence.models import Base
    except ModuleNotFoundError:
        return

    table_names = ", ".join(f'"{table.name}"' for table in Base.metadata.sorted_tables)

    async with session_scope() as session:
        await session.execute(text(f"TRUNCATE {table_names} RESTART IDENTITY CASCADE"))
