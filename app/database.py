import os

from sqlalchemy import text
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import DeclarativeBase
from sqlalchemy.pool import NullPool


DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql+asyncpg://rate_limiter:rate_limiter_password"
    "@localhost:5432/rate_limiter",
)


class Base(DeclarativeBase):
    pass


engine = create_async_engine(
    DATABASE_URL,
    poolclass=NullPool,
)


AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


async def get_db():
    async with AsyncSessionLocal() as session:
        yield session


async def init_database() -> None:
    """
    Create database tables from the SQLAlchemy models.
    """

    from app import models  # noqa: F401

    async with engine.begin() as connection:
        await connection.run_sync(
            Base.metadata.create_all
        )


async def check_database_connection() -> bool:
    """
    Verify that PostgreSQL is reachable.
    """

    async with engine.connect() as connection:
        result = await connection.execute(
            text("SELECT 1")
        )

        return result.scalar() == 1


async def close_database() -> None:
    """
    Dispose of the SQLAlchemy engine.
    """

    await engine.dispose()