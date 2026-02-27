from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

from .base import BaseProvider
from ..types import ProxySpec

logger = logging.getLogger(__name__)


class ProxyLineProvider(BaseProvider):
    name = "proxyline"

    def __init__(self, proxies_url: str, proxies_params: Optional[Dict[str, Any]] = None, retries: int = 4, timeout: int = 15, name: str = "proxyline"):
        if not proxies_url:
            raise ValueError("ProxyLine: требуется proxies_url")
        super().__init__(retries=retries, timeout=timeout)
        self.name = name
        self.proxies_url = proxies_url
        self.proxies_params = proxies_params or {}

    async def fetch(self) -> List[ProxySpec]:
        async def _do():
            data = await self._request_json("GET", self.proxies_url, params=self.proxies_params)
            results = data.get("results") or []
            proxies: List[ProxySpec] = []
            for item in results:
                ip = item.get("ip")
                port = item.get("port_http") or item.get("port")
                user = item.get("username")
                pwd = item.get("password")
                if not ip or not port:
                    continue
                proxies.append(
                    ProxySpec(
                        server=f"{ip}:{port}",
                        username=user,
                        password=pwd,
                        protocol="http",
                        meta={"raw": item},
                    )
                )
            return proxies

        proxies = await self._with_retries(_do, label="ProxyLine")
        if not proxies:
            logger.info("ProxyLine: пул пустой, возвращено 0 прокси")
        return proxies
