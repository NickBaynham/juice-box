"""Shared fixtures for integration tests: schema at head, isolated rows."""

from pathlib import Path

import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import text

from juicebox.persistence.database import session_scope
from juicebox.persistence.models import Base

ALEMBIC_INI = Path(__file__).resolve().parents[2] / "alembic.ini"


def _config() -> Config:
    return Config(str(ALEMBIC_INI))


@pytest.fixture(scope="session", autouse=True)
def schema_at_head():
    """Bring the database to the latest migration before the suite runs."""
    command.upgrade(_config(), "head")


@pytest.fixture
def alembic_config() -> Config:
    """Alembic configuration for tests that drive migrations themselves."""
    return _config()


@pytest.fixture(autouse=True)
async def truncate_tables():
    """Truncate every table in `Base.metadata` before each test.

    Isolates tests from each other and from the persistent `db-data`
    Compose volume. The assertion is a tripwire: an empty metadata would
    make this fixture silently stop isolating anything.
    """
    assert Base.metadata.sorted_tables, "no tables registered on Base.metadata"

    table_names = ", ".join(f'"{table.name}"' for table in Base.metadata.sorted_tables)

    async with session_scope() as session:
        await session.execute(text(f"TRUNCATE {table_names} RESTART IDENTITY CASCADE"))
