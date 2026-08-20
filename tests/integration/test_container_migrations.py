"""Integration test: the container image applies its own migrations."""

import asyncio
import subprocess

import pytest
from alembic import command
from sqlalchemy import text

from juicebox.persistence.database import session_scope

IMAGE = "juice-box:migrations-test"
NETWORK = "juice-box_default"
CONTAINER_DATABASE_URL = "postgresql+asyncpg://juicebox:juicebox@db:5432/juicebox"
APPLICATION_TABLES = text(
    "SELECT table_name FROM information_schema.tables "
    "WHERE table_schema = 'public' AND table_name <> 'alembic_version'"
)


def _application_tables() -> list[str]:
    """Query the tables the container's migration run should have created."""

    async def query():
        async with session_scope() as session:
            return list(await session.scalars(APPLICATION_TABLES))

    return asyncio.run(query())


@pytest.mark.integration
def test_container_applies_migrations_to_an_empty_database(alembic_config):
    """The image carries alembic.ini and migrations/ and can build its own schema."""
    subprocess.run(["docker", "build", "-t", IMAGE, "."], check=True)

    command.downgrade(alembic_config, "base")
    try:
        result = subprocess.run(
            [
                "docker",
                "run",
                "--rm",
                "--network",
                NETWORK,
                "-e",
                f"JUICEBOX_DATABASE_URL={CONTAINER_DATABASE_URL}",
                IMAGE,
                "pdm",
                "run",
                "alembic",
                "upgrade",
                "head",
            ],
            capture_output=True,
            text=True,
            check=False,
        )
        assert result.returncode == 0, result.stderr
        assert _application_tables()
    finally:
        command.upgrade(alembic_config, "head")
