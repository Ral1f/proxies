from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import declarative_base, sessionmaker

Base = declarative_base()


def create_engine_from_url(database_url: str, echo: bool = False, **kwargs):
    return create_async_engine(database_url, echo=echo, future=True, **kwargs)


def create_session_factory(engine):
    return sessionmaker(bind=engine, expire_on_commit=False, class_=AsyncSession, future=True)


async def init_db(engine):
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
