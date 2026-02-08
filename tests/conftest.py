import os
import uuid

import pytest_asyncio
from sqlalchemy import text

from proxy_pipeline.config import load_config
from proxy_pipeline.db import Base, create_engine_from_url, create_session_factory, init_db
from proxy_pipeline.repository import ProxyRepository


def _get_database_url() -> str:
    env_url = os.getenv("TEST_DATABASE_URL")
    if env_url:
        return env_url
    cfg = load_config()
    if cfg.database_url:
        return cfg.database_url
    raise RuntimeError("Не задан DATABASE_URL или TEST_DATABASE_URL")


@pytest_asyncio.fixture
async def repo():
    database_url = _get_database_url()
    schema = None
    connect_args = {}

    if database_url.startswith("postgresql+asyncpg"):
        schema = f"test_{uuid.uuid4().hex}"
        connect_args = {"server_settings": {"search_path": schema}}

    engine = create_engine_from_url(database_url, connect_args=connect_args)

    if schema:
        async with engine.begin() as conn:

            await conn.execute(text(f'CREATE SCHEMA IF NOT EXISTS "{schema}"'))
            await conn.execute(text(f'SET search_path TO "{schema}"'))
            await conn.run_sync(Base.metadata.create_all)
    else:
        await init_db(engine)

    repository = ProxyRepository(create_session_factory(engine))
    try:
        yield repository
    finally:
        if schema:
            async with engine.begin() as conn:
                await conn.execute(text(f'DROP SCHEMA IF EXISTS "{schema}" CASCADE'))
        await engine.dispose()
