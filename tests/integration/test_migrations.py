"""Integration test for the Alembic upgrade, downgrade, and re-upgrade cycle."""

import asyncio

import pytest
from alembic import command
from sqlalchemy import text

from juicebox.persistence.database import session_scope

APPLICATION_TABLES = text(
    "SELECT table_name FROM information_schema.tables "
    "WHERE table_schema = 'public' AND table_name <> 'alembic_version'"
)
VERSION_COUNT = text("SELECT count(*) FROM alembic_version")


def _scalars(statement):
    """Run a read-only statement on a fresh event loop and return its column."""

    async def query():
        async with session_scope() as session:
            return list(await session.scalars(statement))

    return asyncio.run(query())


@pytest.mark.integration
def test_migrations_upgrade_downgrade_and_upgrade_again(alembic_config):
    try:
        command.upgrade(alembic_config, "head")
        assert _scalars(VERSION_COUNT) == [1]
        assert _scalars(APPLICATION_TABLES)

        command.downgrade(alembic_config, "base")
        assert _scalars(APPLICATION_TABLES) == []

        command.upgrade(alembic_config, "head")
        assert _scalars(VERSION_COUNT) == [1]
    finally:
        command.upgrade(alembic_config, "head")
