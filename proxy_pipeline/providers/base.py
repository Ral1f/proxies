from __future__ import annotations

import asyncio
import logging
import socket
from typing import Any, Dict, List, Optional

import aiohttp

from ..types import ProxySpec

logger = logging.getLogger(__name__)


class ProviderError(RuntimeError):
    pass


class BaseProvider:
    name = "base"

    def __init__(self, retries: int = 4, timeout: int = 60):
        self.retries = retries
        self.timeout = timeout

    async def fetch(self) -> List[ProxySpec]:
        raise NotImplementedError

    async def _request_json(
        self,
        method: str,
        url: str,
        *,
        params: Optional[Dict[str, Any]] = None,
        headers: Optional[Dict[str, str]] = None,
    ) -> Dict[str, Any]:
        timeout = aiohttp.ClientTimeout(total=self.timeout)
        connector = aiohttp.TCPConnector(family=socket.AF_INET)
        async with aiohttp.ClientSession(timeout=timeout, headers=headers, connector=connector) as session:
            async with session.request(method, url, params=params) as resp:
                resp.raise_for_status()
                response_json = await resp.json(content_type=None)
                logger.info(response_json)
                return response_json

    async def _with_retries(self, fn, *, label: str):
        for attempt in range(self.retries):
            try:
                return await fn()
            except Exception as exc:
                if attempt + 1 >= self.retries:
                    raise
                logger.warning(
                    "%s: ошибка (попытка %d/%d): %s",
                    label,
                    attempt + 1,
                    self.retries,
                    exc,
                )
                await asyncio.sleep(10)

        raise ProviderError(f"{label}: не удалось получить данные после {self.retries} попыток")
