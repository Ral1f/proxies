from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, Optional


@dataclass(frozen=True)
class ProxySpec:
    server: str
    username: Optional[str] = None
    password: Optional[str] = None
    protocol: str = "http"
    meta: Dict[str, Any] = field(default_factory=dict)
