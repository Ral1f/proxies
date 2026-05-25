from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import declarative_base, sessionmaker

Base = declarative_base()


def create_engine_from_url(database_url: str, echo: bool = False, **kwargs):
    # pool_pre_ping: проверять connection при checkout, переcreate если мёртв.
    # pool_recycle: закрывать connection после 1 часа, чтобы не зависал на серверной стороне.
    # Без этого долгоживущие сервисы (csfloat parser etc) падают с InterfaceError
    # "connection is closed" когда PG закрывает idle connection первым.
    kwargs.setdefault("pool_pre_ping", True)
    kwargs.setdefault("pool_recycle", 3600)
    return create_async_engine(database_url, echo=echo, future=True, **kwargs)


def create_session_factory(engine):
    return sessionmaker(bind=engine, expire_on_commit=False, class_=AsyncSession, future=True)


async def init_db(engine):
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
