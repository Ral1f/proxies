from __future__ import annotations

from datetime import datetime, timezone
from typing import Iterable, List, Optional

from sqlalchemy import func, select, update

from .models import Proxy
from .types import ProxySpec
from .utils import normalize_server


class ProxyRepository:
    def __init__(self, session_factory):
        self.session_factory = session_factory

    async def upsert_many(self, provider: str, proxies: Iterable[ProxySpec]) -> int:
        now = datetime.now(timezone.utc)
        count = 0
        async with self.session_factory() as session:
            for spec in proxies:
                server, scheme = normalize_server(spec.server)
                protocol = spec.protocol or scheme or "http"

                stmt = select(Proxy).where(
                    Proxy.provider == provider,
                    Proxy.server == server,
                    Proxy.username == spec.username,
                    Proxy.password == spec.password,
                )
                existing = (await session.execute(stmt)).scalar_one_or_none()

                if existing:
                    existing.protocol = protocol
                    existing.is_active = True
                    existing.last_seen_at = now
                    existing.meta = spec.meta or {}
                else:
                    session.add(
                        Proxy(
                            provider=provider,
                            server=server,
                            username=spec.username,
                            password=spec.password,
                            protocol=protocol,
                            is_active=True,
                            last_seen_at=now,
                            meta=spec.meta or {},
                        )
                    )

                count += 1

            await session.commit()

        return count

    async def deactivate_missing(self, provider: str, active_servers: Iterable[str]) -> int:
        servers = [normalize_server(server)[0] for server in active_servers]
        async with self.session_factory() as session:
            if servers:
                stmt = (
                    update(Proxy)
                    .where(Proxy.provider == provider, Proxy.server.notin_(servers))
                    .values(is_active=False)
                )
            else:
                stmt = update(Proxy).where(Proxy.provider == provider).values(is_active=False)
            result = await session.execute(stmt)
            await session.commit()
            return result.rowcount or 0

    async def get_random(self, provider: Optional[str] = None, only_active: bool = True) -> Optional[Proxy]:
        async with self.session_factory() as session:
            stmt = select(Proxy)
            if provider:
                stmt = stmt.where(Proxy.provider == provider)
            if only_active:
                stmt = stmt.where(Proxy.is_active.is_(True))

            stmt = stmt.order_by(func.random()).limit(1)
            return (await session.execute(stmt)).scalar_one_or_none()

    async def get_by_id(self, proxy_id: int) -> Optional[Proxy]:
        async with self.session_factory() as session:
            stmt = select(Proxy).where(Proxy.id == proxy_id)
            return (await session.execute(stmt)).scalar_one_or_none()

    async def list_active(self, provider: Optional[str] = None) -> List[Proxy]:
        async with self.session_factory() as session:
            stmt = select(Proxy).where(Proxy.is_active.is_(True))
            if provider:
                stmt = stmt.where(Proxy.provider == provider)
            return list((await session.execute(stmt)).scalars())

    async def ban_proxy(self, proxy_id: Optional[int] = None, server: Optional[str] = None, provider: Optional[str] = None) -> int:
        if proxy_id is None and server is None:
            raise ValueError("Укажите proxy_id или server")

        async with self.session_factory() as session:
            stmt = update(Proxy).values(is_active=False)
            if proxy_id is not None:
                stmt = stmt.where(Proxy.id == proxy_id)
            if server is not None:
                stmt = stmt.where(Proxy.server == normalize_server(server)[0])
            if provider:
                stmt = stmt.where(Proxy.provider == provider)

            result = await session.execute(stmt)
            await session.commit()
            return result.rowcount or 0
