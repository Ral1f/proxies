from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional
from urllib.parse import parse_qs, urlparse

from .base import BaseProvider, ProviderError
from ..types import ProxySpec

logger = logging.getLogger(__name__)


class MobileProxySpaceProvider(BaseProvider):
    name = "mobileproxyspace"
    default_change_ip_url = "https://changeip.mobileproxy.space/"

    def __init__(
        self,
        api_token: str,
        base_url: str = "https://mobileproxy.space/api.html",
        proxy_ids: Optional[List[str]] = None,
        command: str = "get_my_proxy",
        retries: int = 4,
        timeout: int = 15,
    ):
        if not api_token:
            raise ValueError("MobileProxySpace: требуется api_token")
        super().__init__(retries=retries, timeout=timeout)
        self.api_token = api_token
        self.base_url = base_url
        self.proxy_ids = proxy_ids or []
        self.command = command

    @staticmethod
    def _extract_change_ip_url(item: Dict[str, Any]) -> Optional[str]:
        value = item.get("proxy_change_ip_url")
        if isinstance(value, str) and value:
            return value
        return None

    @staticmethod
    def _extract_proxy_key(item: Dict[str, Any], change_ip_url: Optional[str] = None) -> Optional[str]:
        value = item.get("proxy_key")
        if isinstance(value, str) and value:
            return value

        if not change_ip_url:
            return None

        parsed = urlparse(change_ip_url)
        query = parse_qs(parsed.query)
        key = query.get("proxy_key") or query.get("proxykey")
        if key:
            return key[0]
        return None

    @staticmethod
    def _proxy_key_from_url(url: str) -> Optional[str]:
        parsed = urlparse(url)
        query = parse_qs(parsed.query)
        key = query.get("proxy_key") or query.get("proxykey")
        if key:
            return key[0]
        return None

    @staticmethod
    def _extract_items(payload: Any) -> List[Dict[str, Any]]:
        items: Any
        if isinstance(payload, list):
            items = payload
        elif isinstance(payload, dict):
            if payload.get("success") is False:
                raise ProviderError(f"MobileProxySpace API error: {payload}")

            if "data" in payload:
                items = payload.get("data")
            elif "proxy_id" in payload:
                items = [payload]
            else:
                raise ProviderError("MobileProxySpace: в ответе отсутствует ключ data")
        else:
            raise ProviderError("MobileProxySpace: некорректный формат ответа")

        if isinstance(items, dict):
            items = [items]

        if not isinstance(items, list):
            raise ProviderError("MobileProxySpace: некорректный формат data")

        normalized: List[Dict[str, Any]] = []
        for item in items:
            if isinstance(item, dict):
                normalized.append(item)
        return normalized

    async def fetch(self) -> List[ProxySpec]:
        params: Dict[str, Any] = {"command": self.command}
        if self.proxy_ids:
            params["proxy_id"] = ",".join(self.proxy_ids)

        headers = {"Authorization": f"Bearer {self.api_token}"}

        async def _do():
            data = await self._request_json("GET", self.base_url, params=params, headers=headers)
            items = self._extract_items(data)

            proxies: List[ProxySpec] = []
            for item in items:
                host = item.get("proxy_host_ip") or item.get("proxy_hostname")
                port = item.get("proxy_http_port")
                user = item.get("proxy_login")
                pwd = item.get("proxy_pass")
                protocol = "http"

                if not host or not port:
                    continue

                change_ip_url = self._extract_change_ip_url(item)
                proxy_key = self._extract_proxy_key(item, change_ip_url)

                meta = {
                    "raw": item,
                    "proxy_id": item.get("proxy_id"),
                    "proxy_exp": item.get("proxy_exp"),
                    "proxy_geo": item.get("proxy_geo"),
                    "proxy_operator": item.get("proxy_operator"),
                }
                if change_ip_url:
                    meta["change_ip_url"] = change_ip_url
                if proxy_key:
                    meta["proxy_key"] = proxy_key

                proxies.append(
                    ProxySpec(
                        server=f"{host}:{port}",
                        username=user,
                        password=pwd,
                        protocol=protocol,
                        meta=meta,
                    )
                )

            return proxies

        proxies = await self._with_retries(_do, label="MobileProxySpace")
        if not proxies:
            logger.info("MobileProxySpace: пул пустой, возвращено 0 прокси")
        return proxies

    async def change_ip(
        self,
        *,
        proxy_key: Optional[str] = None,
        change_ip_url: Optional[str] = None,
        user_agent: Optional[str] = None,
        response_format: str = "json",
        base_url: Optional[str] = None,
    ) -> Dict[str, Any]:
        if not proxy_key and change_ip_url:
            proxy_key = self._proxy_key_from_url(change_ip_url)

        if not proxy_key:
            raise ValueError("MobileProxySpace: требуется proxy_key или change_ip_url")

        params = {"proxy_key": proxy_key, "format": response_format}
        headers = {
            "User-Agent": user_agent
            or "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        }

        url = base_url or self.default_change_ip_url

        async def _do():
            return await self._request_json("GET", url, params=params, headers=headers)

        return await self._with_retries(_do, label="MobileProxySpace change_ip")
