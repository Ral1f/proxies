from __future__ import annotations

from typing import Dict, Iterable, List, Optional

from .providers import BaseProvider
from .repository import ProxyRepository
from .types import ProxySpec


class ProxyPipeline:
    def __init__(
        self,
        providers: Iterable[BaseProvider],
        repository: ProxyRepository,
        deactivate_missing: bool = False,
    ):
        self.providers: Dict[str, BaseProvider] = {provider.name: provider for provider in providers}
        self.repository = repository
        self.deactivate_missing = deactivate_missing

    def get_provider(self, name: str) -> BaseProvider:
        if name not in self.providers:
            raise KeyError(f"Провайдер не зарегистрирован: {name}")
        return self.providers[name]

    async def sync_provider(self, name: str, deactivate_missing: Optional[bool] = None) -> int:
        provider = self.get_provider(name)
        proxies: List[ProxySpec] = await provider.fetch()
        count = await self.repository.upsert_many(provider.name, proxies)

        if deactivate_missing if deactivate_missing is not None else self.deactivate_missing:
            await self.repository.deactivate_missing(provider.name, [p.server for p in proxies])

        return count

    async def sync_all(self) -> Dict[str, int]:
        results: Dict[str, int] = {}
        for name in self.providers:
            results[name] = await self.sync_provider(name)
        return results
