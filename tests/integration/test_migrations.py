"""Integration test for the Alembic upgrade, downgrade, and re-upgrade cycle."""

import pytest
from alembic import command
from sqlalchemy import text

VERSION_COUNT = text("SELECT count(*) FROM alembic_version")


@pytest.mark.integration
def test_migrations_upgrade_downgrade_and_upgrade_again(alembic_config, run_query, application_tables):
    try:
        command.upgrade(alembic_config, "head")
        assert run_query(VERSION_COUNT) == [1]
        assert run_query(application_tables)

        command.downgrade(alembic_config, "base")
        assert run_query(application_tables) == []

        command.upgrade(alembic_config, "head")
        assert run_query(VERSION_COUNT) == [1]
    finally:
        command.upgrade(alembic_config, "head")
