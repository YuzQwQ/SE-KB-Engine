"""Owned bounded executors; a cancelled running future keeps its capacity."""
from __future__ import annotations

from concurrent.futures import Future, ThreadPoolExecutor, wait
from contextvars import copy_context
from threading import RLock
from typing import Any, Callable

from se_kb_app.errors import ApplicationError, ErrorKind


class BoundedExecutor:
    def __init__(self, workers: int = 4, waiting: int = 16, *, name: str = "se-kb-work") -> None:
        self._executor = ThreadPoolExecutor(max_workers=workers, thread_name_prefix=name)
        self._capacity = workers + waiting
        self._pending: set[Future[Any]] = set()
        self._lock = RLock()
        self._accepting = True

    def submit(self, function: Callable[..., Any], *args: Any, **kwargs: Any) -> Future[Any]:
        with self._lock:
            if not self._accepting:
                raise RuntimeError("executor is shutting down")
            if len(self._pending) >= self._capacity:
                raise ApplicationError(ErrorKind.POLICY, "crawl_capacity_exceeded",
                                       "Work capacity is currently full.", retryable=True)
            context = copy_context()
            future = self._executor.submit(context.run, function, *args, **kwargs)
            self._pending.add(future)
        future.add_done_callback(self._finished)
        return future

    def _finished(self, future: Future[Any]) -> None:
        with self._lock:
            self._pending.discard(future)

    @property
    def pending(self) -> int:
        with self._lock:
            return len(self._pending)

    def close(self, deadline_seconds: float = 5) -> None:
        with self._lock:
            self._accepting = False
            pending = list(self._pending)
        for future in pending:
            future.cancel()
        wait(pending, timeout=deadline_seconds)
        self._executor.shutdown(wait=False, cancel_futures=True)
