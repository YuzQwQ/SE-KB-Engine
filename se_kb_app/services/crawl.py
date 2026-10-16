from __future__ import annotations

from collections.abc import Callable
from contextlib import contextmanager
from dataclasses import replace
from threading import Lock
from time import monotonic
from typing import Any

from se_kb_app.domain import FetchRequest, FetchedDocument, Fetcher
from se_kb_app.errors import ApplicationError, ErrorKind, wrap_error
from se_kb_app.jobs.context import current_cancellation
from se_kb_app.jobs.store import CancellationToken
from se_kb_app.jobs.executor import BoundedExecutor


class _LinkedCancellation(CancellationToken):
    def __init__(self, parent) -> None:
        super().__init__()
        self.parent = parent

    def checkpoint(self) -> None:
        super().checkpoint()
        if self.parent is not None:
            self.parent.checkpoint()


class CrawlService:
    """One acquisition policy, injected transport collaborators and lifecycle owner."""

    def __init__(self, machine: Any, *, capacity: Any, sites: Any = None,
                 use_tor: bool = False, proxy_selected: bool = False, limits: Any = None) -> None:
        self.machine, self.capacity, self.sites = machine, capacity, sites
        self.use_tor, self.limits = use_tor, limits
        self.proxy_selected = proxy_selected
        self._active: set[_LinkedCancellation] = set()
        self._lock = Lock()
        self._closed = False
        self.executor = BoundedExecutor(capacity.global_limit,
            max(0, capacity.queue_capacity - capacity.global_limit), name="se-kb-crawl")

    def submit(self, function, *args, **kwargs):
        return self.executor.submit(function, *args, **kwargs)

    def run(self, request: FetchRequest):
        token = _LinkedCancellation(request.cancellation or current_cancellation.get())
        with self._lock:
            if self._closed:
                raise ApplicationError(ErrorKind.CONFIGURATION, "crawl_closed", "Crawl service is closed.")
            self._active.add(token)
        end = min(request.deadline if request.deadline is not None else float("inf"),
                  monotonic() + self.machine.policy.total_timeout_seconds)

        def basic_scope(url):
            return self.capacity.slot(url, deadline=end, cancellation=token)

        @contextmanager
        def scope(url):
            token.checkpoint()
            if request.automatic and self.sites is not None:
                delay = self.sites.check(replace(request, url=url, deadline=end,
                                                cancellation=token, headers={}, cookies={},
                                                automatic=False, request_scope=basic_scope))
                self.capacity.set_interval(url, delay)
            with basic_scope(url):
                token.checkpoint()
                yield

        try:
            token.checkpoint()
            if self.use_tor or self.proxy_selected:
                raise ApplicationError(ErrorKind.CONFIGURATION, "crawl_transport_unavailable",
                                       "The selected proxy/Tor requires a verified transport adapter.")
            return self.machine.run(replace(request, deadline=end, cancellation=token,
                                            request_scope=scope))
        finally:
            with self._lock:
                self._active.discard(token)

    def fetch(self, request: FetchRequest) -> FetchedDocument:
        outcome = self.run(request)
        if outcome.document is not None:
            return outcome.document
        reason = outcome.transitions[-1].reason if outcome.transitions else "fetch_failed"
        kind = (ErrorKind.CANCELLATION if outcome.kind.value == "cancelled" else
                ErrorKind.POLICY if outcome.kind.value in {"policy", "challenge"} else ErrorKind.NETWORK)
        raise ApplicationError(kind, reason, "Page acquisition did not produce usable content.",
                               retryable=outcome.kind.value == "transient")

    def close(self) -> None:
        with self._lock:
            if self._closed:
                return
            self._closed = True
            tokens = list(self._active)
        for token in tokens:
            token.cancel()
        self.executor.close()
        if self.machine.rendered is not None:
            self.machine.rendered.close()
        self.machine.static.close()


class CrawlOrchestrator:
    """Coordinates bounded direct attempts and an optional rendered fallback."""

    def __init__(
        self,
        direct: Fetcher,
        *,
        rendered: Fetcher | None = None,
        max_retries: int = 0,
        on_attempt: Callable[[str, int], None] | None = None,
    ) -> None:
        self.direct = direct
        self.rendered = rendered
        self.max_retries = max_retries
        self.on_attempt = on_attempt or (lambda _mode, _attempt: None)

    def fetch(self, request: FetchRequest) -> FetchedDocument:
        from se_kb_app.crawling.machine import FetchStateMachine
        from se_kb_app.crawling.models import FetchPolicy

        callback = self.on_attempt
        class Attempted:
            def __init__(self, fetcher, mode):
                self.fetcher, self.mode, self.calls = fetcher, mode, 0
            def fetch(self, value):
                self.calls += 1
                callback(self.mode, self.calls)
                try:
                    return self.fetcher.fetch(value)
                except ApplicationError:
                    raise
                except Exception as error:
                    raise wrap_error(ErrorKind.NETWORK, "direct_fetch_failed", "Page acquisition failed.",
                                     retryable=False, cause=error) from error
            def close(self):
                return None
        machine = FetchStateMachine(Attempted(self.direct, "direct"),
            rendered=Attempted(self.rendered, "rendered") if self.rendered is not None else None,
            policy=FetchPolicy(maximum_static_attempts=min(3, self.max_retries + 1)))
        outcome = machine.run(request)
        if outcome.document is not None:
            return outcome.document
        code = outcome.transitions[-1].reason
        raise ApplicationError(ErrorKind.POLICY if outcome.kind.value == "policy" else ErrorKind.NETWORK,
                               code, "Page acquisition did not produce usable content.")

    def close(self) -> None:
        self.direct.close()
        if self.rendered is not None:
            self.rendered.close()
