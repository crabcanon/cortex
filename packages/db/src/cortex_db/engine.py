"""Async database engine and session helpers."""

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

SessionFactory = async_sessionmaker[AsyncSession]


def create_database_engine(
    dsn: str,
    *,
    echo: bool = False,
    pool_pre_ping: bool = True,
) -> AsyncEngine:
    """Create a shared async engine for Cortex services."""
    return create_async_engine(
        dsn,
        echo=echo,
        pool_pre_ping=pool_pre_ping,
        future=True,
    )


def create_session_factory(engine: AsyncEngine) -> SessionFactory:
    """Create an async session factory with stable defaults."""
    return async_sessionmaker(
        bind=engine,
        expire_on_commit=False,
        autoflush=False,
        class_=AsyncSession,
    )


@asynccontextmanager
async def session_scope(session_factory: SessionFactory) -> AsyncIterator[AsyncSession]:
    """Provide a commit/rollback guarded async session context."""
    session = session_factory()
    try:
        yield session
        await session.commit()
    except Exception:
        await session.rollback()
        raise
    finally:
        await session.close()


def normalize_alembic_dsn(dsn: str) -> str:
    """Convert an async runtime DSN to a sync Alembic-compatible DSN."""
    if "+aiosqlite" in dsn:
        return dsn.replace("+aiosqlite", "", 1)
    if "+asyncpg" in dsn:
        return dsn.replace("+asyncpg", "+psycopg", 1)
    return dsn
