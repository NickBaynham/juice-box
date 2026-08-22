"""FastAPI dependencies shared across routers."""

from collections.abc import AsyncIterator

from sqlalchemy.ext.asyncio import AsyncSession

from juicebox.persistence import session_scope


async def get_session() -> AsyncIterator[AsyncSession]:
    """Yield an `AsyncSession` scoped to one request, via `session_scope()`."""
    async with session_scope() as session:
        yield session
