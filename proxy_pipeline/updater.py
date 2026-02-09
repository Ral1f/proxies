from __future__ import annotations

import argparse
import asyncio
import logging
import signal
from dataclasses import dataclass
from logging.handlers import RotatingFileHandler
from pathlib import Path
from typing import Dict, List, Optional, Sequence

from .client import ProxyClient, build_default_client

logger = logging.getLogger(__name__)
DEFAULT_LOG_DIR = "/home/trade/logs/others"
DEFAULT_LOG_FILE = "proxy_pipeline_updater.log"


@dataclass
class UpdaterOptions:
    interval_seconds: int = 300
    providers: Optional[List[str]] = None


class ProxyUpdater:
    def __init__(self, client: ProxyClient, options: Optional[UpdaterOptions] = None):
        self.client = client
        self.options = options or UpdaterOptions()

    def _providers_to_sync(self) -> Optional[List[str]]:
        if not self.options.providers:
            return None

        available = set(self.client.available_providers())
        requested = [name.strip() for name in self.options.providers if name and name.strip()]
        unknown = [name for name in requested if name not in available]
        if unknown:
            raise ValueError(f"Неизвестные провайдеры: {', '.join(sorted(unknown))}")
        return requested

    async def sync_once(self) -> Dict[str, int]:
        providers = self._providers_to_sync()
        if not providers:
            result = await self.client.refresh_all()
            logger.info("Sync completed: %s", result)
            return result

        result: Dict[str, int] = {}
        for provider_name in providers:
            result[provider_name] = await self.client.refresh_provider(provider_name)
        logger.info("Sync completed: %s", result)
        return result

    async def run_forever(self, stop_event: asyncio.Event):
        if self.options.interval_seconds <= 0:
            raise ValueError("interval_seconds must be > 0")

        while not stop_event.is_set():
            try:
                await self.sync_once()
            except Exception:
                logger.exception("Sync failed")

            try:
                await asyncio.wait_for(stop_event.wait(), timeout=self.options.interval_seconds)
            except asyncio.TimeoutError:
                continue


class ProcessLock:
    def __init__(self, path: str):
        self.path = Path(path)
        self._file = None

    def acquire(self):
        import fcntl

        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._file = self.path.open("w")
        try:
            fcntl.flock(self._file.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError as exc:
            raise RuntimeError(f"Updater уже запущен (lock: {self.path})") from exc

    def release(self):
        import fcntl

        if self._file is None:
            return
        try:
            fcntl.flock(self._file.fileno(), fcntl.LOCK_UN)
        finally:
            self._file.close()
            self._file = None


def _parse_providers(raw: str) -> Optional[List[str]]:
    if not raw:
        return None
    providers = [item.strip() for item in raw.split(",") if item.strip()]
    return providers or None


def _setup_signals(stop_event: asyncio.Event):
    loop = asyncio.get_running_loop()
    for signame in (signal.SIGINT, signal.SIGTERM):
        try:
            loop.add_signal_handler(signame, stop_event.set)
        except NotImplementedError:
            pass


def _configure_logging(log_level: str, log_dir: str, log_file: str) -> Path:
    level = getattr(logging, log_level.upper(), logging.INFO)
    log_path = Path(log_dir) / log_file
    log_path.parent.mkdir(parents=True, exist_ok=True)

    fmt = "%(asctime)s %(levelname)s %(name)s: %(message)s"
    formatter = logging.Formatter(fmt)

    root = logging.getLogger()
    root.setLevel(level)
    root.handlers.clear()

    stream_handler = logging.StreamHandler()
    stream_handler.setFormatter(formatter)
    root.addHandler(stream_handler)

    file_handler = RotatingFileHandler(
        filename=log_path,
        maxBytes=20 * 1024 * 1024,
        backupCount=5,
        encoding="utf-8",
    )
    file_handler.setFormatter(formatter)
    root.addHandler(file_handler)

    return log_path


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Proxy pipeline updater")
    parser.add_argument("--once", action="store_true", help="Run one sync and exit")
    parser.add_argument("--interval-seconds", type=int, default=300, help="Polling interval for continuous mode")
    parser.add_argument("--providers", type=str, default="", help="Comma-separated providers to sync")
    parser.add_argument("--deactivate-missing", action="store_true", help="Deactivate proxies missing in provider response")
    parser.add_argument("--echo-sql", action="store_true", help="Enable SQLAlchemy SQL echo")
    parser.add_argument("--lock-file", type=str, default="/tmp/proxy_pipeline_updater.lock", help="Single-process lock file path")
    parser.add_argument("--log-level", type=str, default="INFO", help="Logging level")
    parser.add_argument("--log-dir", type=str, default=DEFAULT_LOG_DIR, help="Directory for updater logs")
    parser.add_argument("--log-file", type=str, default=DEFAULT_LOG_FILE, help="Updater log filename")
    return parser


async def _run(args: argparse.Namespace):
    lock = ProcessLock(args.lock_file)
    lock.acquire()

    log_path = _configure_logging(args.log_level, args.log_dir, args.log_file)
    logger.info("Logging to %s", log_path)

    client = build_default_client(echo_sql=args.echo_sql, deactivate_missing=args.deactivate_missing)
    updater = ProxyUpdater(
        client,
        UpdaterOptions(
            interval_seconds=args.interval_seconds,
            providers=_parse_providers(args.providers),
        ),
    )

    try:
        await client.init_db()
        if args.once:
            await updater.sync_once()
            return

        stop_event = asyncio.Event()
        _setup_signals(stop_event)
        logger.info("Updater started with interval=%ss", args.interval_seconds)
        await updater.run_forever(stop_event)
        logger.info("Updater stopped")
    finally:
        await client.close()
        lock.release()


def main(argv: Optional[Sequence[str]] = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    asyncio.run(_run(args))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
