import pytest

from proxy_pipeline.providers.base import ProviderError
from proxy_pipeline.providers.mobileproxyspace import MobileProxySpaceProvider


def test_extract_proxy_key_from_url():
    url = "https://changeip.mobileproxy.space/?proxy_key=abc123&format=json"
    assert MobileProxySpaceProvider._proxy_key_from_url(url) == "abc123"


@pytest.mark.asyncio
async def test_fetch_maps_real_get_my_proxy_payload():
    provider = MobileProxySpaceProvider(
        api_token="test-token",
        base_url="https://mobileproxy.space/api.html",
        proxy_ids=["453401"],
        command="get_my_proxy",
    )

    async def fake_request_json(method, url, *, params=None, headers=None):
        assert method == "GET"
        assert url == "https://mobileproxy.space/api.html"
        assert params == {"command": "get_my_proxy", "proxy_id": "453401"}
        assert headers == {"Authorization": "Bearer test-token"}
        return {
            "data": [
                {
                    "proxy_id": "453401",
                    "proxy_exp": "2026-04-25 12:27:58",
                    "proxy_login": "user_login",
                    "proxy_pass": "user_pass",
                    "proxy_hostname": "ip.mobileproxy.space",
                    "proxy_host_ip": "91.147.101.46",
                    "proxy_http_port": "1013",
                    "proxy_socks5_port": 1014,
                    "proxy_operator": "beeline(KZ)",
                    "proxy_geo": "Казахстан, Алматы",
                    "proxy_change_ip_url": "https://changeip.mobileproxy.space/?proxy_key=ec592186315da186e148c7f33473b230",
                    "proxy_key": "ec592186315da186e148c7f33473b230",
                }
            ]
        }

    provider._request_json = fake_request_json  # type: ignore[method-assign]

    proxies = await provider.fetch()
    assert len(proxies) == 1

    proxy = proxies[0]
    assert proxy.server == "91.147.101.46:1013"
    assert proxy.username == "user_login"
    assert proxy.password == "user_pass"
    assert proxy.protocol == "http"
    assert proxy.meta["proxy_id"] == "453401"
    assert proxy.meta["proxy_key"] == "ec592186315da186e148c7f33473b230"
    assert proxy.meta["change_ip_url"].startswith("https://changeip.mobileproxy.space/")


@pytest.mark.asyncio
async def test_fetch_raises_if_data_key_missing():
    provider = MobileProxySpaceProvider(api_token="test-token")

    async def fake_request_json(method, url, *, params=None, headers=None):
        return {"status": "ok"}

    provider._request_json = fake_request_json  # type: ignore[method-assign]

    with pytest.raises(ProviderError):
        await provider.fetch()


@pytest.mark.asyncio
async def test_change_ip_uses_proxy_key_from_change_ip_url():
    provider = MobileProxySpaceProvider(api_token="test-token")

    async def fake_request_json(method, url, *, params=None, headers=None):
        assert method == "GET"
        assert url == "https://changeip.mobileproxy.space/"
        assert params == {"proxy_key": "abc123", "format": "json"}
        assert "User-Agent" in headers
        return {"status": "ok"}

    provider._request_json = fake_request_json  # type: ignore[method-assign]

    resp = await provider.change_ip(
        change_ip_url="https://changeip.mobileproxy.space/?proxy_key=abc123"
    )
    assert resp == {"status": "ok"}
