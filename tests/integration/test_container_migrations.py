"""Integration test: the container image applies its own migrations."""

import subprocess

import pytest
from alembic import command

IMAGE = "juice-box:migrations-test"
NETWORK = "juice-box_default"
CONTAINER_DATABASE_URL = "postgresql+asyncpg://juicebox:juicebox@db:5432/juicebox"


@pytest.mark.integration
def test_container_applies_migrations_to_an_empty_database(alembic_config, run_query, application_tables):
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
        assert run_query(application_tables)
    finally:
        command.upgrade(alembic_config, "head")
