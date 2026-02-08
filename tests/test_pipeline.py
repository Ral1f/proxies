import pytest

from proxy_pipeline.pipeline import ProxyPipeline
from proxy_pipeline.providers.base import BaseProvider
from proxy_pipeline.types import ProxySpec


class FakeProvider(BaseProvider):
    name = "fake"

    async def fetch(self):
        return [ProxySpec(server="10.0.0.1:3128")]


@pytest.mark.asyncio
async def test_pipeline_sync_provider(repo):
    pipeline = ProxyPipeline([FakeProvider()], repo)

    count = await pipeline.sync_provider("fake")
    assert count == 1

    proxy = await repo.get_random("fake")
    assert proxy is not None
    assert proxy.server == "10.0.0.1:3128"


@pytest.mark.asyncio
async def test_pipeline_sync_all(repo):
    pipeline = ProxyPipeline([FakeProvider()], repo)

    results = await pipeline.sync_all()
    assert results == {"fake": 1}
