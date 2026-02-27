from __future__ import annotations

from typing import Optional

from .config import load_config
from .db import create_engine_from_url, create_session_factory, init_db
from .pipeline import ProxyPipeline
from .providers import MobileProxySpaceProvider, Proxy6Provider, ProxyLineProvider, ProxyWingProvider
from .repository import ProxyRepository


class ProxyClient:
    def __init__(self, pipeline: ProxyPipeline, repository: ProxyRepository, engine):
        self.pipeline = pipeline
        self.repository = repository
        self.engine = engine

    async def init_db(self):
        await init_db(self.engine)

    async def close(self):
        await self.engine.dispose()

    def available_providers(self):
        return sorted(self.pipeline.providers.keys())

    async def ensure_provider(self, provider: Optional[str] = None):
        available = self.available_providers()
        if not available:
            raise RuntimeError("В proxy_pipeline не настроен ни один провайдер")
        if provider and provider not in available:
            raise RuntimeError(
                f"Провайдер '{provider}' не настроен. Доступно: {', '.join(available)}"
            )

    async def count_active_proxies(self, provider: Optional[str] = None) -> int:
        return len(await self.repository.list_active(provider=provider))

    async def initialize_for_parser(self, provider: Optional[str] = None) -> int:
        await self.init_db()
        await self.ensure_provider(provider=provider)
        return await self.count_active_proxies(provider=provider)

    async def refresh_provider(self, provider_name: str) -> int:
        return await self.pipeline.sync_provider(provider_name)

    async def refresh_proxyline(self) -> int:
        return await self.pipeline.sync_provider("proxyline")

    async def refresh_proxy6(self) -> int:
        return await self.pipeline.sync_provider("proxy6")

    async def refresh_mobileproxyspace(self) -> int:
        return await self.pipeline.sync_provider("mobileproxyspace")

    async def refresh_proxywing(self) -> int:
        return await self.pipeline.sync_provider("proxywing")

    async def refresh_all(self):
        return await self.pipeline.sync_all()

    async def get_random_proxy(self, provider: Optional[str] = None, as_url: bool = True):
        proxy = await self.repository.get_random(provider=provider)
        if not proxy:
            return None
        return proxy.as_url() if as_url else proxy

    async def get_random_proxy_or_raise(self, provider: Optional[str] = None, as_url: bool = True):
        proxy = await self.get_random_proxy(provider=provider, as_url=as_url)
        if proxy:
            return proxy
        provider_name = provider or "any"
        raise RuntimeError(
            f"Активные прокси не найдены для provider={provider_name}. "
            "Запусти updater из proxy_pipeline."
        )

    async def get_random_proxyline(self, as_url: bool = True):
        return await self.get_random_proxy("proxyline", as_url=as_url)

    async def get_random_proxy6(self, as_url: bool = True):
        return await self.get_random_proxy("proxy6", as_url=as_url)

    async def get_random_mobileproxyspace(self, as_url: bool = True):
        return await self.get_random_proxy("mobileproxyspace", as_url=as_url)

    async def get_random_proxywing(self, as_url: bool = True):
        return await self.get_random_proxy("proxywing", as_url=as_url)

    async def ban_proxy(self, proxy_id: Optional[int] = None, server: Optional[str] = None, provider: Optional[str] = None) -> int:
        return await self.repository.ban_proxy(proxy_id=proxy_id, server=server, provider=provider)

    async def reload_mobileproxyspace(
        self,
        *,
        proxy_key: Optional[str] = None,
        change_ip_url: Optional[str] = None,
        proxy_id: Optional[int] = None,
        user_agent: Optional[str] = None,
    ):
        provider = self.pipeline.get_provider("mobileproxyspace")
        if not isinstance(provider, MobileProxySpaceProvider):
            raise RuntimeError("MobileProxySpace провайдер не подключен")

        if not proxy_key and not change_ip_url and proxy_id is not None:
            proxy = await self.repository.get_by_id(proxy_id)
            if not proxy:
                raise ValueError(f"Proxy id не найден: {proxy_id}")
            meta = proxy.meta or {}
            proxy_key = meta.get("proxy_key")
            change_ip_url = change_ip_url or meta.get("change_ip_url")
            if not proxy_key and isinstance(meta.get("raw"), dict):
                proxy_key = meta["raw"].get("proxy_key")

        # Auto-discover: если ничего не передано — ищем в БД
        if not proxy_key and not change_ip_url:
            proxy = await self.repository.get_random(provider="mobileproxyspace")
            if proxy and proxy.meta:
                meta = proxy.meta
                proxy_key = proxy_key or meta.get("proxy_key") or (meta.get("raw") or {}).get("proxy_key")
                change_ip_url = change_ip_url or meta.get("change_ip_url")

        return await provider.change_ip(
            proxy_key=proxy_key,
            change_ip_url=change_ip_url,
            user_agent=user_agent,
        )


def build_default_client(echo_sql: bool = False, deactivate_missing: bool = False) -> ProxyClient:
    cfg = load_config()

    engine = create_engine_from_url(cfg.database_url, echo=echo_sql)
    session_factory = create_session_factory(engine)
    repository = ProxyRepository(session_factory)

    providers = []
    if cfg.proxyline.get("proxies_url"):
        providers.append(
            ProxyLineProvider(
                proxies_url=cfg.proxyline.get("proxies_url"),
                proxies_params=cfg.proxyline.get("proxies_params"),
                retries=cfg.proxyline.get("retries", 4),
                timeout=cfg.proxyline.get("timeout", 15),
            )
        )

    if cfg.proxyline_dedicated.get("proxies_url"):
        providers.append(
            ProxyLineProvider(
                name="proxyline_dedicated",
                proxies_url=cfg.proxyline_dedicated.get("proxies_url"),
                proxies_params=cfg.proxyline_dedicated.get("proxies_params"),
                retries=cfg.proxyline_dedicated.get("retries", 4),
                timeout=cfg.proxyline_dedicated.get("timeout", 15),
            )
        )

    if cfg.proxy6.get("api_key"):
        providers.append(
            Proxy6Provider(
                api_key=cfg.proxy6.get("api_key"),
                state=cfg.proxy6.get("state", "active"),
                retries=cfg.proxy6.get("retries", 4),
                timeout=cfg.proxy6.get("timeout", 15),
            )
        )

    if cfg.mobileproxyspace.get("api_token"):
        providers.append(
            MobileProxySpaceProvider(
                api_token=cfg.mobileproxyspace.get("api_token"),
                base_url=cfg.mobileproxyspace.get("base_url", "https://mobileproxy.space/api.html"),
                proxy_ids=cfg.mobileproxyspace.get("proxy_ids") or [],
                command=cfg.mobileproxyspace.get("command", "get_my_proxy"),
                retries=cfg.mobileproxyspace.get("retries", 4),
                timeout=cfg.mobileproxyspace.get("timeout", 15),
            )
        )

    if cfg.proxywing.get("file_path"):
        providers.append(
            ProxyWingProvider(
                file_path=cfg.proxywing.get("file_path"),
                protocol=cfg.proxywing.get("protocol", "http"),
            )
        )

    pipeline = ProxyPipeline(providers, repository, deactivate_missing=deactivate_missing)
    return ProxyClient(pipeline, repository, engine)
