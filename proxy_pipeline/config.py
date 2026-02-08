from __future__ import annotations

import json
import os
from dataclasses import dataclass
from typing import Any, Dict, List, Optional


@dataclass
class AppConfig:
    database_url: str
    proxyline: Dict[str, Any]
    proxy6: Dict[str, Any]
    mobileproxyspace: Dict[str, Any]


def _load_module():
    try:
        import proxies_config as cfg  # type: ignore
    except Exception:
        cfg = None
    return cfg


def _get_env_json(name: str) -> Optional[Dict[str, Any]]:
    raw = os.getenv(name)
    if not raw:
        return None
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        return None


def _get_env_list(name: str) -> List[str]:
    raw = os.getenv(name, "")
    return [item.strip() for item in raw.split(",") if item.strip()]


def load_config() -> AppConfig:
    cfg = _load_module()

    database_url = (
        os.getenv("DATABASE_URL")
        or getattr(cfg, "DATABASE_URL", None)
        or "sqlite+aiosqlite:///proxies.db"
    )

    proxyline_cfg = dict(getattr(cfg, "PROXYLINE", {}) or {})
    proxyline_cfg["proxies_url"] = os.getenv("PROXYLINE_URL", proxyline_cfg.get("proxies_url"))
    env_params = _get_env_json("PROXYLINE_PARAMS")
    if env_params is not None:
        proxyline_cfg["proxies_params"] = env_params

    proxy6_cfg = dict(getattr(cfg, "PROXY6", {}) or {})
    proxy6_cfg["api_key"] = os.getenv("PROXY6_API_KEY", proxy6_cfg.get("api_key"))
    proxy6_cfg["state"] = os.getenv("PROXY6_STATE", proxy6_cfg.get("state"))

    mps_cfg = dict(getattr(cfg, "MOBILEPROXYSPACE", {}) or {})
    mps_cfg["api_token"] = os.getenv("MOBILEPROXYSPACE_API_TOKEN", mps_cfg.get("api_token"))
    mps_cfg["base_url"] = os.getenv("MOBILEPROXYSPACE_BASE_URL", mps_cfg.get("base_url"))
    env_ids = _get_env_list("MOBILEPROXYSPACE_PROXY_IDS")
    if env_ids:
        mps_cfg["proxy_ids"] = env_ids

    return AppConfig(
        database_url=database_url,
        proxyline=proxyline_cfg,
        proxy6=proxy6_cfg,
        mobileproxyspace=mps_cfg,
    )
