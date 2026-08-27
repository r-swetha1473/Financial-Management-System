"""Async SQLAlchemy engine and session factory."""

import os
from collections.abc import AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.core.config import settings

_engine_kwargs: dict = {"pool_pre_ping": True}
if os.environ.get("VERCEL"):
    from sqlalchemy.pool import NullPool

    _engine_kwargs["poolclass"] = NullPool

engine = create_async_engine(settings.sqlalchemy_database_url, **_engine_kwargs)
SessionLocal = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    async with SessionLocal() as session:
        yield session
