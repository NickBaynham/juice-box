"""Async engine, session factory, and the session-scoped transaction helper."""

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool

from juicebox.config.settings import Settings

# NullPool: pytest-asyncio's "auto" mode gives every test its own event
# loop, and a pooled asyncpg connection cached on one loop breaks the next
# test with "RuntimeError: Event loop is closed".
engine = create_async_engine(Settings().database_url, poolclass=NullPool)
async_session_factory = async_sessionmaker(engine, expire_on_commit=False)


@asynccontextmanager
async def session_scope() -> AsyncIterator[AsyncSession]:
    """Yield a session that commits on a clean exit and rolls back on error."""
    async with async_session_factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
