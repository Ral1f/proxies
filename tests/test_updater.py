from __future__ import annotations

import asyncio

import pytest

from proxy_pipeline.updater import (
    DEFAULT_LOG_DIR,
    ProxyUpdater,
    UpdaterOptions,
    build_parser,
)


class FakeClient:
    def __init__(self):
        self.calls = []
        self.pipeline = type("P", (), {"providers": {"proxyline": object(), "proxy6": object()}})()

    def available_providers(self):
        return sorted(self.pipeline.providers.keys())

    async def refresh_all(self):
        self.calls.append(("all", None))
        return {"proxyline": 2, "proxy6": 1}

    async def refresh_provider(self, provider_name: str):
        self.calls.append(("provider", provider_name))
        return 1


@pytest.mark.asyncio
async def test_sync_once_all_providers():
    updater = ProxyUpdater(FakeClient(), UpdaterOptions(interval_seconds=60, providers=None))

    result = await updater.sync_once()

    assert result == {"proxyline": 2, "proxy6": 1}
    assert updater.client.calls == [("all", None)]


@pytest.mark.asyncio
async def test_sync_once_selected_providers():
    updater = ProxyUpdater(FakeClient(), UpdaterOptions(interval_seconds=60, providers=["proxy6"]))

    result = await updater.sync_once()

    assert result == {"proxy6": 1}
    assert updater.client.calls == [("provider", "proxy6")]


@pytest.mark.asyncio
async def test_sync_once_unknown_provider_raises():
    updater = ProxyUpdater(FakeClient(), UpdaterOptions(interval_seconds=60, providers=["unknown"]))

    with pytest.raises(ValueError):
        await updater.sync_once()


@pytest.mark.asyncio
async def test_run_forever_stops_on_event():
    updater = ProxyUpdater(FakeClient(), UpdaterOptions(interval_seconds=3600, providers=None))
    stop_event = asyncio.Event()

    async def stop_soon():
        await asyncio.sleep(0.01)
        stop_event.set()

    stopper = asyncio.create_task(stop_soon())
    await updater.run_forever(stop_event)
    await stopper

    assert updater.client.calls == [("all", None)]


def test_build_parser_has_default_log_path():
    parser = build_parser()
    args = parser.parse_args([])

    assert args.log_dir == DEFAULT_LOG_DIR
    assert args.log_file == "proxy_pipeline_updater.log"
