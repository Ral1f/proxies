from __future__ import annotations

import logging
from pathlib import Path
from typing import List, Optional

from .base import BaseProvider, ProviderError
from ..types import ProxySpec

logger = logging.getLogger(__name__)


class ProxyWingProvider(BaseProvider):
    name = "proxywing"

    def __init__(self, file_path: str, protocol: str = "http", retries: int = 4, timeout: int = 15):
        if not file_path:
            raise ValueError("ProxyWing: требуется file_path")
        super().__init__(retries=retries, timeout=timeout)
        self.file_path = Path(file_path)
        self.protocol = protocol

    async def fetch(self) -> List[ProxySpec]:
        if not self.file_path.exists():
            raise ProviderError(f"ProxyWing: файл не найден: {self.file_path}")

        text = self.file_path.read_text(encoding="utf-8")
        proxies: List[ProxySpec] = []

        for line in text.splitlines():
            line = line.strip()
            if not line:
                continue
            spec = self._parse_line(line)
            if spec:
                proxies.append(spec)

        if not proxies:
            logger.info("ProxyWing: файл пустой или нет валидных строк, возвращено 0 прокси")
        return proxies

    def _parse_line(self, line: str) -> Optional[ProxySpec]:
        parts = line.split(":")
        if len(parts) < 2:
            logger.warning("ProxyWing: пропуск невалидной строки: %s", line)
            return None

        ip, port = parts[0], parts[1]
        username = parts[2] if len(parts) > 2 else None
        password = parts[3] if len(parts) > 3 else None

        return ProxySpec(
            server=f"{ip}:{port}",
            username=username,
            password=password,
            protocol=self.protocol,
        )
