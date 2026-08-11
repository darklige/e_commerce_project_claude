"""Async SQLAlchemy engine, session factory, and FastAPI dependency."""

from __future__ import annotations

from collections.abc import AsyncIterator

from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from app.core.config import get_settings

_settings = get_settings()
_engine_kwargs: dict[str, object] = {
    "echo": _settings.DB_ECHO,
    "pool_pre_ping": True,
    "future": True,
}

if not _settings.DATABASE_URL.startswith("sqlite+"):
    _engine_kwargs.update(
        {
            "pool_size": _settings.DB_POOL_SIZE,
            "max_overflow": _settings.DB_MAX_OVERFLOW,
            "pool_timeout": _settings.DB_POOL_TIMEOUT,
        }
    )

engine: AsyncEngine = create_async_engine(_settings.DATABASE_URL, **_engine_kwargs)

async_session_factory: async_sessionmaker[AsyncSession] = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    autoflush=False,
    autocommit=False,
    expire_on_commit=False,
)


async def get_db() -> AsyncIterator[AsyncSession]:
    """FastAPI dependency yielding a scoped :class:`AsyncSession`.

    The session is committed on successful exit and rolled back on
    exception. Callers should ``await session.commit()`` explicitly for
    write operations; this helper still commits at the end to guarantee
    a clean state, matching FastAPI's dependency lifecycle.
    """
    async with async_session_factory() as session:
        try:
            yield session
        except Exception:
            await session.rollback()
            raise
        else:
            await session.commit()


async def dispose_engine() -> None:
    """Dispose engine connections. Called on graceful shutdown."""
    await engine.dispose()
