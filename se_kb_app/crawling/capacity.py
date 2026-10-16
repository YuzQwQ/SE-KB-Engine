from __future__ import annotations

from collections import OrderedDict
from contextlib import contextmanager
from threading import Condition
from time import monotonic
from typing import Iterator
from urllib.parse import urlsplit

from se_kb_app.domain import Cancellation
from se_kb_app.errors import ApplicationError, ErrorKind
from se_kb_app.observability import METRICS


class CrawlCapacity:
    """Bounded admission with per-host FIFO, without reserving global slots while waiting."""

    def __init__(self, *, global_limit: int, per_host_limit: int, queue_capacity: int,
                 minimum_interval: float = 0.0) -> None:
        if min(global_limit, per_host_limit, queue_capacity) < 1:
            raise ValueError("capacity limits must be positive")
        self.global_limit, self.per_host_limit = global_limit, per_host_limit
        self.queue_capacity = queue_capacity
        self.minimum_interval = minimum_interval
        self._condition = Condition()
        self._queued = self._active = self.high_watermark = 0
        self._hosts: dict[str, int] = {}
        self._waiting: list[tuple[object, str]] = []
        self._next: OrderedDict[str, float] = OrderedDict()
        self._intervals: dict[str, float] = {}

    def set_interval(self, url: str, seconds: float) -> None:
        host = (urlsplit(url).hostname or "").lower()
        with self._condition:
            interval = max(self.minimum_interval, seconds)
            previous = self._intervals.get(host, self.minimum_interval)
            if interval != previous:
                self._next[host] = self._next.get(host, monotonic()) - previous + interval
            self._intervals[host] = interval
            while len(self._intervals) > 1024:
                old = next((key for key in self._intervals if key not in self._hosts
                            and all(value != key for _, value in self._waiting)), None)
                if old is None:
                    break
                del self._intervals[old]
                self._next.pop(old, None)

    @property
    def depths(self) -> tuple[int, int]:
        with self._condition:
            return self._queued, self._active

    @contextmanager
    def slot(self, url: str, *, deadline: float | None = None,
             cancellation: Cancellation | None = None) -> Iterator[None]:
        host = (urlsplit(url).hostname or "").lower()
        ticket = object()
        active = False
        end = deadline if deadline is not None else monotonic() + 60
        with self._condition:
            if self._queued + self._active >= self.queue_capacity:
                raise ApplicationError(ErrorKind.POLICY, "crawl_capacity_exceeded",
                                       "Crawl capacity is currently full.", retryable=True)
            self._queued += 1
            self._waiting.append((ticket, host))
            self.high_watermark = max(self.high_watermark, self._queued)
        try:
            with self._condition:
                while True:
                    if cancellation:
                        cancellation.checkpoint()
                    remaining = end - monotonic()
                    if remaining <= 0:
                        raise ApplicationError(ErrorKind.NETWORK, "crawl_deadline", "Crawl deadline exceeded.")
                    prior = next(item[0] for item in self._waiting if item[1] == host)
                    if (prior is ticket and self._active < self.global_limit
                            and self._hosts.get(host, 0) < self.per_host_limit
                            and monotonic() >= self._next.get(host, 0)):
                        self._waiting.remove((ticket, host))
                        self._queued -= 1
                        self._active += 1
                        self._hosts[host] = self._hosts.get(host, 0) + 1
                        self._next[host] = monotonic() + self._intervals.get(host, self.minimum_interval)
                        self._next.move_to_end(host)
                        while len(self._next) > 1024:
                            old = next((key for key in self._next if key not in self._hosts
                                        and all(value != key for _, value in self._waiting)), None)
                            if old is None:
                                break
                            del self._next[old]
                            self._intervals.pop(old, None)
                        active = True
                        self._metrics()
                        break
                    self._condition.wait(timeout=min(0.05, remaining))
            yield
        finally:
            with self._condition:
                if active:
                    self._active -= 1
                    self._hosts[host] -= 1
                    if not self._hosts[host]:
                        del self._hosts[host]
                else:
                    self._queued -= 1
                    self._waiting.remove((ticket, host))
                self._metrics()
                self._condition.notify_all()

    def _metrics(self) -> None:
        METRICS.gauge("crawl_queue_depth", self._queued)
        METRICS.gauge("crawl_active_workers", self._active)
