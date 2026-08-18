import asyncpg
import pytest

from juicebox.config.settings import Settings


@pytest.mark.integration
async def test_can_connect_to_database():
    dsn = Settings().database_url.replace("+asyncpg", "")

    connection = await asyncpg.connect(dsn)
    try:
        assert await connection.fetchval("SELECT 1") == 1
    finally:
        await connection.close()
