import pytest

from proxy_pipeline.types import ProxySpec


@pytest.mark.asyncio
async def test_upsert_and_get_random(repo):
    specs = [ProxySpec(server="1.1.1.1:80", username="u", password="p", protocol="http")]
    count = await repo.upsert_many("proxyline", specs)
    assert count == 1

    proxy = await repo.get_random("proxyline")
    assert proxy is not None
    assert proxy.server == "1.1.1.1:80"
    assert proxy.as_url() == "http://u:p@1.1.1.1:80"

    # Upsert same proxy with new protocol + meta should update existing row
    specs2 = [
        ProxySpec(
            server="http://1.1.1.1:80",
            username="u",
            password="p",
            protocol="socks5",
            meta={"x": 1},
        )
    ]
    await repo.upsert_many("proxyline", specs2)
    proxy = await repo.get_random("proxyline")
    assert proxy is not None
    assert proxy.protocol == "socks5"
    assert proxy.meta == {"x": 1}


@pytest.mark.asyncio
async def test_deactivate_missing(repo):
    specs = [ProxySpec(server="1.1.1.1:80"), ProxySpec(server="2.2.2.2:80")]
    await repo.upsert_many("proxy6", specs)

    changed = await repo.deactivate_missing("proxy6", ["1.1.1.1:80"])
    assert changed == 1

    active = await repo.list_active("proxy6")
    assert len(active) == 1
    assert active[0].server == "1.1.1.1:80"

    await repo.deactivate_missing("proxy6", [])
    assert await repo.list_active("proxy6") == []
