from __future__ import annotations

from typing import Any, Dict, List

from .base import BaseProvider, ProviderError
from ..types import ProxySpec


class Proxy6Provider(BaseProvider):
    name = "proxy6"

    def __init__(self, api_key: str, state: str = "active", retries: int = 4, timeout: int = 15):
        if not api_key:
            raise ValueError("Proxy6: требуется api_key")
        super().__init__(retries=retries, timeout=timeout)
        self.api_key = api_key
        self.state = state or "active"

    async def fetch(self) -> List[ProxySpec]:
        url = f"https://px6.link/api/{self.api_key}/getproxy"
        params = {"state": self.state}

        async def _do():
            data = await self._request_json("GET", url, params=params)
            if data.get("status") != "yes":
                raise ProviderError(f"Proxy6 API error {data.get('error_id')}: {data.get('error')}")

            items = data.get("list") or {}
            values = items.values() if isinstance(items, dict) else items

            proxies: List[ProxySpec] = []
            for item in values:
                host = item.get("host")
                port = item.get("port")
                user = item.get("user")
                pwd = item.get("pass")
                ptype = item.get("type")
                if not all([host, port]):
                    continue
                scheme = "socks5" if ptype == "socks" else "http"
                proxies.append(
                    ProxySpec(
                        server=f"{host}:{port}",
                        username=user,
                        password=pwd,
                        protocol=scheme,
                        meta={"raw": item},
                    )
                )
            return proxies

        proxies = await self._with_retries(_do, label="Proxy6")
        if not proxies:
            raise ProviderError("Proxy6: не удалось получить список прокси")
        return proxies
