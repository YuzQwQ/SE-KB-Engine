"""Infrastructure assembly for the shared crawl application service."""
from __future__ import annotations

import atexit
from concurrent.futures import TimeoutError
from threading import Lock
from time import monotonic

from se_kb_app.crawling.browser import PlaywrightRenderedFetcher
from se_kb_app.crawling.capacity import CrawlCapacity
from se_kb_app.crawling.http import PooledHttpFetcher
from se_kb_app.crawling.machine import FetchStateMachine
from se_kb_app.crawling.models import FetchPolicy
from se_kb_app.crawling.site import SitePolicy
from se_kb_app.domain import FetchRequest, FetchedDocument
from se_kb_app.errors import ApplicationError, ErrorKind
from se_kb_app.jobs.executor import BoundedExecutor
from se_kb_app.services.crawl import CrawlService
from se_kb_app.settings import AppSettings
from service_boundary.fetch import FetchLimits


class BrowserWorker:
    def __init__(self) -> None:
        self.executor = BoundedExecutor(1, 16, name="se-kb-browser")
        self.fetcher = PlaywrightRenderedFetcher(timeout_ms=60_000)

    def fetch(self, request: FetchRequest) -> FetchedDocument:
        future = self.executor.submit(self.fetcher.fetch, request)
        try:
            while True:
                if request.cancellation:
                    request.cancellation.checkpoint()
                if request.deadline is not None and monotonic() >= request.deadline:
                    raise ApplicationError(ErrorKind.NETWORK, "crawl_deadline", "Crawl deadline exceeded.")
                try:
                    return future.result(timeout=0.05)
                except TimeoutError:
                    if future.done():
                        return future.result()
        except BaseException:
            future.cancel()
            raise

    def close(self) -> None:
        self.executor.close()


def create_crawl_service(settings: AppSettings | None = None) -> CrawlService:
    resolved = settings or AppSettings.from_sources()
    limits = FetchLimits.from_environment()
    config = resolved.crawl
    static = PooledHttpFetcher(limits=limits, max_connections=config.workers,
                               max_keepalive_connections=config.workers)
    browser = BrowserWorker()
    capacity = CrawlCapacity(global_limit=config.workers, per_host_limit=config.per_host,
                             queue_capacity=config.workers + config.waiting, minimum_interval=config.min_interval)
    machine = FetchStateMachine(static, rendered=browser, policy=FetchPolicy(
        maximum_static_attempts=3, total_timeout_seconds=limits.total_seconds,
        connect_timeout_seconds=limits.connect_seconds, read_timeout_seconds=limits.read_seconds,
        maximum_body_bytes=limits.decompressed_bytes,
    ))
    return CrawlService(machine, capacity=capacity, sites=SitePolicy(static),
                        use_tor=resolved.use_tor, proxy_selected=bool(config.proxy_url), limits=limits)


_default: CrawlService | None = None
_lock = Lock()


def default_crawl_service() -> CrawlService:
    global _default
    with _lock:
        if _default is None:
            _default = create_crawl_service()
            atexit.register(_default.close)
        return _default
