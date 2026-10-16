"""Explicit browser-only acceptance, restricted to an owned loopback fixture.

Run only after installing Playwright/Chromium and choosing browser validation:
  python -m pytest tests/test_crawl_browser_acceptance.py --override-ini=addopts= -m browser -q
"""
from __future__ import annotations

import ipaddress
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from threading import Thread
from time import monotonic
from urllib.parse import urlsplit

import pytest

from se_kb_app.crawling.browser import PlaywrightRenderedFetcher
from se_kb_app.crawling.capacity import CrawlCapacity
from se_kb_app.crawling.http import PooledHttpFetcher
from se_kb_app.crawling.machine import FetchStateMachine
from se_kb_app.crawling.models import FetchPolicy, OutcomeKind
from se_kb_app.domain import FetchRequest
from se_kb_app.services.crawl import CrawlService
from service_boundary.errors import public_error
from service_boundary.url_policy import ValidatedURL


@pytest.mark.browser
@pytest.mark.parametrize("path,expected,attempts", [
    ("/static", OutcomeKind.SUCCESS, 1),
    ("/dynamic", OutcomeKind.SUCCESS, 2),
    ("/never", OutcomeKind.PERMANENT_FAILURE, 2),
])
def test_real_browser_wait_and_single_fallback(monkeypatch, path, expected, attempts):
    pytest.importorskip("playwright.sync_api")

    class Handler(BaseHTTPRequestHandler):
        def do_GET(self):
            if self.path == "/static":
                body = b"<article>Static technical content without browser acquisition.</article>"
            elif self.path == "/dynamic":
                body = (b"<main id='content'></main><script>setTimeout(() => {"
                        b"document.getElementById('content').textContent = "
                        b"'Delayed technical body reached its ready condition.';}, 150);</script>")
            else:
                body = b"<main id='content'></main>"
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def log_message(self, *args):
            pass

    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    thread = Thread(target=server.serve_forever, name="browser-acceptance-fixture", daemon=True)
    thread.start()
    port = server.server_address[1]
    origin = f"http://127.0.0.1:{port}"

    def fixture_only(url):
        parsed = urlsplit(url)
        # This test injection permits only our exact loopback origin. No global
        # production allow-private flag or external target is enabled.
        if (parsed.scheme, parsed.hostname, parsed.port) != ("http", "127.0.0.1", port):
            raise public_error("url_not_allowed")
        return ValidatedURL(url, "127.0.0.1", port, (ipaddress.ip_address("127.0.0.1"),))

    monkeypatch.setattr("service_boundary.fetch.validate_url", lambda value, **kwargs: fixture_only(value))
    monkeypatch.setattr("se_kb_app.crawling.browser.validate_url", fixture_only)
    fetcher = PooledHttpFetcher(url_validator=fixture_only)
    machine = FetchStateMachine(fetcher, rendered=PlaywrightRenderedFetcher(timeout_ms=3000),
                                policy=FetchPolicy(total_timeout_seconds=5))
    service = CrawlService(machine, capacity=CrawlCapacity(global_limit=2, per_host_limit=1, queue_capacity=4))
    started = monotonic()
    try:
        outcome = service.run(FetchRequest(origin + path))
        assert outcome.kind is expected
        assert len(outcome.attempts) == attempts
        if path == "/dynamic":
            assert outcome.document is not None
            assert "Delayed technical body" in outcome.document.content
        assert monotonic() - started < 8  # Includes a conservative cleanup allowance.
    finally:
        service.close()
        server.shutdown()
        server.server_close()
        thread.join(timeout=2)
