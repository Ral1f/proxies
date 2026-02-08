from __future__ import annotations

from typing import Optional
from urllib.parse import quote


def build_proxy_url(protocol: str, server: str, username: Optional[str], password: Optional[str]) -> str:
    scheme = (protocol or "http").lower()
    if username is None and password is None:
        return f"{scheme}://{server}"

    user = quote(username or "", safe="")
    pwd = quote(password or "", safe="")
    return f"{scheme}://{user}:{pwd}@{server}"


def normalize_server(server: str) -> tuple[str, str]:
    if "://" in server:
        scheme, rest = server.split("://", 1)
        return rest, scheme
    return server, ""
