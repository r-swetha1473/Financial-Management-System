"""Async SQLAlchemy engine and session factory."""

import os
import ssl
from collections.abc import AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.core.config import settings

_engine_kwargs: dict = {"pool_pre_ping": True}
if os.environ.get("VERCEL"):
    from sqlalchemy.pool import NullPool

    # Supabase pooler presents a chain Vercel's CA bundle rejects; encrypt anyway.
    ssl_context = ssl.create_default_context()
    ssl_context.check_hostname = False
    ssl_context.verify_mode = ssl.CERT_NONE
    _engine_kwargs["poolclass"] = NullPool
    _engine_kwargs["connect_args"] = {"ssl": ssl_context, "statement_cache_size": 0}

engine = create_async_engine(settings.sqlalchemy_database_url, **_engine_kwargs)
SessionLocal = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    async with SessionLocal() as session:
        yield session
