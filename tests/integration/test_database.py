"""Integration tests for the session-scoped transaction helper."""

import pytest
from sqlalchemy import text

from juicebox.persistence.database import session_scope


@pytest.mark.integration
async def test_session_scope_yields_a_working_session():
    async with session_scope() as session:
        result = await session.scalar(text("SELECT 1"))
    assert result == 1


@pytest.mark.integration
async def test_session_scope_rolls_back_and_reraises_on_error():
    async with session_scope() as session:
        await session.execute(text("CREATE TABLE session_scope_probe (id integer)"))

    try:
        with pytest.raises(RuntimeError):
            async with session_scope() as session:
                await session.execute(
                    text("INSERT INTO session_scope_probe (id) VALUES (1)")
                )
                raise RuntimeError("boom")

        async with session_scope() as session:
            count = await session.scalar(
                text("SELECT count(*) FROM session_scope_probe")
            )
        assert count == 0
    finally:
        async with session_scope() as session:
            await session.execute(text("DROP TABLE session_scope_probe"))
