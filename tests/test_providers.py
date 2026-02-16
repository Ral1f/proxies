import pytest

from proxy_pipeline.providers.base import ProviderError
from proxy_pipeline.providers.proxy6 import Proxy6Provider
from proxy_pipeline.providers.proxyline import ProxyLineProvider
from proxy_pipeline.providers.proxywing import ProxyWingProvider


@pytest.mark.asyncio
async def test_proxyline_fetch_returns_normalized_proxyspecs():
    provider = ProxyLineProvider(
        proxies_url="https://proxyline.example/api/proxies",
        proxies_params={"orders": [123]},
    )

    async def fake_request_json(method, url, *, params=None, headers=None):
        assert method == "GET"
        assert url == "https://proxyline.example/api/proxies"
        assert params == {"orders": [123]}
        return {
            "results": [
                {
                    "ip": "1.1.1.1",
                    "port_http": 8080,
                    "username": "user1",
                    "password": "pass1",
                },
                {
                    "ip": "2.2.2.2",
                    "port": 3128,
                    "username": "user2",
                    "password": "pass2",
                },
                {
                    "ip": "3.3.3.3",
                },
            ]
        }

    provider._request_json = fake_request_json  # type: ignore[method-assign]

    proxies = await provider.fetch()

    assert len(proxies) == 2
    assert proxies[0].server == "1.1.1.1:8080"
    assert proxies[0].username == "user1"
    assert proxies[0].password == "pass1"
    assert proxies[0].protocol == "http"

    assert proxies[1].server == "2.2.2.2:3128"
    assert proxies[1].username == "user2"
    assert proxies[1].password == "pass2"
    assert proxies[1].protocol == "http"


@pytest.mark.asyncio
async def test_proxyline_fetch_returns_empty_list_for_empty_pool():
    provider = ProxyLineProvider(
        proxies_url="https://proxyline.example/api/proxies",
        proxies_params={"orders": [123]},
    )

    async def fake_request_json(method, url, *, params=None, headers=None):
        return {"results": []}

    provider._request_json = fake_request_json  # type: ignore[method-assign]

    proxies = await provider.fetch()
    assert proxies == []


@pytest.mark.asyncio
async def test_proxy6_fetch_returns_normalized_proxyspecs():
    provider = Proxy6Provider(api_key="test-key", state="active")

    async def fake_request_json(method, url, *, params=None, headers=None):
        assert method == "GET"
        assert url == "https://px6.link/api/test-key/getproxy"
        assert params == {"state": "active"}
        return {
            "status": "yes",
            "list": {
                "1": {
                    "host": "10.10.10.10",
                    "port": "8000",
                    "user": "http_user",
                    "pass": "http_pass",
                    "type": "http",
                },
                "2": {
                    "host": "20.20.20.20",
                    "port": "9000",
                    "user": "socks_user",
                    "pass": "socks_pass",
                    "type": "socks",
                },
            },
        }

    provider._request_json = fake_request_json  # type: ignore[method-assign]

    proxies = await provider.fetch()

    assert len(proxies) == 2
    assert proxies[0].server == "10.10.10.10:8000"
    assert proxies[0].protocol == "http"
    assert proxies[0].username == "http_user"
    assert proxies[0].password == "http_pass"

    assert proxies[1].server == "20.20.20.20:9000"
    assert proxies[1].protocol == "socks5"
    assert proxies[1].username == "socks_user"
    assert proxies[1].password == "socks_pass"


@pytest.mark.asyncio
async def test_proxy6_fetch_raises_on_api_error():
    provider = Proxy6Provider(api_key="test-key")

    async def fake_request_json(method, url, *, params=None, headers=None):
        return {"status": "no", "error_id": 42, "error": "bad request"}

    provider._request_json = fake_request_json  # type: ignore[method-assign]

    with pytest.raises(ProviderError):
        await provider.fetch()


@pytest.mark.asyncio
async def test_proxy6_fetch_returns_empty_list_for_empty_pool():
    provider = Proxy6Provider(api_key="test-key", state="active")

    async def fake_request_json(method, url, *, params=None, headers=None):
        return {"status": "yes", "list": {}}

    provider._request_json = fake_request_json  # type: ignore[method-assign]

    proxies = await provider.fetch()
    assert proxies == []


@pytest.mark.asyncio
async def test_proxywing_fetch_parses_txt_file(tmp_path):
    txt = tmp_path / "proxywing.txt"
    txt.write_text(
        "128.65.166.58:5900:XGOQD71594:V12IFL8Y\n"
        "128.65.167.89:5557:XGOQD71594:V12IFL8Y\n"
        "10.0.0.1:3128\n"
    )

    provider = ProxyWingProvider(file_path=str(txt))
    proxies = await provider.fetch()

    assert len(proxies) == 3
    assert proxies[0].server == "128.65.166.58:5900"
    assert proxies[0].username == "XGOQD71594"
    assert proxies[0].password == "V12IFL8Y"
    assert proxies[0].protocol == "http"

    assert proxies[1].server == "128.65.167.89:5557"
    assert proxies[1].username == "XGOQD71594"

    assert proxies[2].server == "10.0.0.1:3128"
    assert proxies[2].username is None
    assert proxies[2].password is None


@pytest.mark.asyncio
async def test_proxywing_fetch_returns_empty_for_empty_file(tmp_path):
    txt = tmp_path / "proxywing.txt"
    txt.write_text("")

    provider = ProxyWingProvider(file_path=str(txt))
    proxies = await provider.fetch()
    assert proxies == []


@pytest.mark.asyncio
async def test_proxywing_fetch_raises_on_missing_file(tmp_path):
    provider = ProxyWingProvider(file_path=str(tmp_path / "nonexistent.txt"))

    with pytest.raises(ProviderError):
        await provider.fetch()


@pytest.mark.asyncio
async def test_proxywing_fetch_skips_invalid_lines(tmp_path):
    txt = tmp_path / "proxywing.txt"
    txt.write_text(
        "128.65.166.58:5900:user:pass\n"
        "badline\n"
        "\n"
        "10.0.0.1:8080:u:p\n"
    )

    provider = ProxyWingProvider(file_path=str(txt))
    proxies = await provider.fetch()

    assert len(proxies) == 2
    assert proxies[0].server == "128.65.166.58:5900"
    assert proxies[1].server == "10.0.0.1:8080"


@pytest.mark.asyncio
async def test_proxywing_fetch_respects_protocol(tmp_path):
    txt = tmp_path / "proxywing.txt"
    txt.write_text("1.1.1.1:1080:u:p\n")

    provider = ProxyWingProvider(file_path=str(txt), protocol="socks5")
    proxies = await provider.fetch()

    assert len(proxies) == 1
    assert proxies[0].protocol == "socks5"
