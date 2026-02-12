import os

import pytest
from aiohttp import ClientResponseError

from proxy_pipeline.config import load_config
from proxy_pipeline.providers.mobileproxyspace import MobileProxySpaceProvider
from proxy_pipeline.providers.proxy6 import Proxy6Provider
from proxy_pipeline.providers.proxyline import ProxyLineProvider


def _integration_enabled() -> bool:
    return os.getenv("RUN_PROVIDER_INTEGRATION", "").strip().lower() in {"1", "true", "yes"}


def _assert_proxy_shape(proxy):
    assert proxy.server
    assert ":" in proxy.server
    assert proxy.protocol in {"http", "socks5"}


@pytest.mark.integration
@pytest.mark.asyncio
async def test_proxyline_fetch_integration():
    if not _integration_enabled():
        pytest.skip("Set RUN_PROVIDER_INTEGRATION=1 to run provider integration tests")

    cfg = load_config().proxyline
    if not cfg.get("proxies_url"):
        pytest.skip("PROXYLINE URL is not configured")

    provider = ProxyLineProvider(
        proxies_url=cfg["proxies_url"],
        proxies_params=cfg.get("proxies_params"),
    )
    proxies = await provider.fetch()
    if not proxies:
        pytest.skip("proxyline: empty proxy pool for current account/filters")
    _assert_proxy_shape(proxies[0])


@pytest.mark.integration
@pytest.mark.asyncio
async def test_proxy6_fetch_integration():
    if not _integration_enabled():
        pytest.skip("Set RUN_PROVIDER_INTEGRATION=1 to run provider integration tests")

    cfg = load_config().proxy6
    if not cfg.get("api_key"):
        pytest.skip("PROXY6 API key is not configured")

    provider = Proxy6Provider(
        api_key=cfg["api_key"],
        state=cfg.get("state", "active"),
    )
    proxies = await provider.fetch()
    if not proxies:
        pytest.skip("proxy6: empty proxy pool for current account/filters")
    _assert_proxy_shape(proxies[0])


@pytest.mark.integration
@pytest.mark.asyncio
async def test_mobileproxyspace_fetch_integration():
    if not _integration_enabled():
        pytest.skip("Set RUN_PROVIDER_INTEGRATION=1 to run provider integration tests")

    cfg = load_config().mobileproxyspace
    if not cfg.get("api_token"):
        pytest.skip("MOBILEPROXYSPACE API token is not configured")

    provider = MobileProxySpaceProvider(
        api_token=cfg["api_token"],
        base_url=cfg.get("base_url", "https://mobileproxy.space/api.html"),
        proxy_ids=cfg.get("proxy_ids") or [],
        command=cfg.get("command", "get_my_proxy"),
    )
    try:
        proxies = await provider.fetch()
    except ClientResponseError as exc:
        if exc.status == 429:
            pytest.skip("mobileproxyspace: rate limited (HTTP 429)")
        raise
    if not proxies:
        pytest.skip("mobileproxyspace: empty proxy pool for current account/filters")
    _assert_proxy_shape(proxies[0])
    assert "proxy_key" in proxies[0].meta
