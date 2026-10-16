from __future__ import annotations

from collections.abc import Callable
from contextlib import nullcontext
from dataclasses import replace
from time import monotonic
from typing import Any

import httpx

from se_kb_app.domain import FetchRequest, FetchedDocument
from se_kb_app.errors import ApplicationError, ErrorKind, wrap_error
from service_boundary.errors import PublicError
from service_boundary.fetch import FetchLimits, bounded_get
from service_boundary.resolution import bounded_validation
from service_boundary.transport import VerifiedHTTPTransport, stateless_cookie_jar
from service_boundary.url_policy import validate_url
from se_kb_app.observability import METRICS

DEFAULT_BLOCKED_RESOURCE_TYPES = frozenset({"font", "media", "websocket"})


class PlaywrightRenderedFetcher:
    """Offline browser networking: every routed response comes from verified HTTP.

    Browser routes are an application boundary, not a claim of OS sandboxing.
    WebRTC/background traffic requires deployment egress containment as documented.
    """

    def __init__(self, *, timeout_ms: int = 30_000,
                 playwright_factory: Callable[[], Any] | None = None) -> None:
        self.timeout_ms, self.playwright_factory = timeout_ms, playwright_factory

    def fetch(self, request: FetchRequest) -> FetchedDocument:
        deadline = min(request.deadline or float("inf"), monotonic() + self.timeout_ms / 1000)
        target = bounded_validation(validate_url, request.url, deadline)
        limits = FetchLimits.from_environment()
        browser = context = page = manager = None
        entered = False
        routed_error: list[BaseException] = []
        consumed = requests = redirects = 0
        client = httpx.Client(transport=VerifiedHTTPTransport(), trust_env=False, cookies=stateless_cookie_jar(),
                              headers={"Accept-Encoding": "gzip, deflate"})

        def checkpoint():
            if request.cancellation:
                request.cancellation.checkpoint()
            if monotonic() >= deadline:
                raise ApplicationError(ErrorKind.NETWORK, "crawl_deadline", "Crawl deadline exceeded.")

        def remaining_ms():
            checkpoint()
            return max(1, int((deadline - monotonic()) * 1000))

        try:
            if self.playwright_factory is None:
                try:
                    from playwright.sync_api import sync_playwright
                except ImportError as error:
                    raise ApplicationError(ErrorKind.CONFIGURATION, "browser_unavailable",
                                           "Install the crawl extra and browser runtime to render pages.") from error
                manager = sync_playwright()
            else:
                manager = self.playwright_factory()
            runtime = manager.__enter__()
            entered = True
            checkpoint()
            browser = runtime.chromium.launch(headless=True, timeout=remaining_ms(), args=[
                "--disable-background-networking", "--disable-quic",
                "--force-webrtc-ip-handling-policy=disable_non_proxied_udp",
            ])
            context = browser.new_context(service_workers="block", accept_downloads=False)
            context.set_default_timeout(remaining_ms())
            # Fail closed if required interception APIs cannot be installed.
            context.route_web_socket("**/*", lambda ws: ws.close())
            if request.cookies:
                context.add_cookies([{"name": key, "value": value, "url": target.url}
                                     for key, value in request.cookies.items()])

            def route_resource(route):
                nonlocal consumed, requests, redirects
                try:
                    checkpoint()
                    req = route.request
                    if req.resource_type in DEFAULT_BLOCKED_RESOURCE_TYPES or req.method != "GET":
                        route.abort("blockedbyclient")
                        return
                    requests += 1
                    if requests > 100:
                        raise PublicError("resource_limit", "Browser request budget exceeded.", 422)
                    headers = dict(req.headers)
                    original = httpx.URL(target.url)
                    current = httpx.URL(req.url)
                    if (current.scheme, current.host, current.port) == (original.scheme, original.host, original.port):
                        headers.update(request.headers)
                    # An ambient browser Cookie has proper domain scope; no global
                    # target credentials or model credentials live on this client.
                    response, payload = bounded_get(
                        client, req.url, limits=replace(limits, decompressed_bytes=min(
                            limits.decompressed_bytes, max(1, limits.decompressed_bytes - consumed))),
                        headers=headers, deadline=deadline, checkpoint=checkpoint,
                        allowed_media_types=("text", "application/javascript", "application/x-javascript",
                                             "application/json", "application/xhtml+xml", "image"),
                        request_scope=request.request_scope, follow_redirects=False,
                    )
                    if response.status_code in {301, 302, 303, 307, 308}:
                        redirects += 1
                        if redirects > limits.redirects:
                            raise PublicError("resource_limit", "Browser redirect budget exceeded.", 422)
                    consumed += len(payload)
                    if consumed > limits.decompressed_bytes:
                        raise PublicError("resource_limit", "Browser byte budget exceeded.", 422)
                    outgoing = {key: value for key, value in response.headers.items()
                                if key.lower() not in {"content-encoding", "content-length", "transfer-encoding"}}
                    route.fulfill(status=response.status_code, headers=outgoing, body=payload)
                except BaseException as error:
                    routed_error.append(error)
                    route.abort("blockedbyclient")

            context.route("**/*", route_resource)
            page = context.new_page()
            scope = nullcontext()
            with scope:
                response = page.goto(target.url, timeout=remaining_ms(), wait_until="domcontentloaded")
                if response is not None and response.status >= 400:
                    raise ApplicationError(ErrorKind.NETWORK, "rendered_http_failure", "Rendered page failed.")
                if routed_error:
                    raise routed_error[0]
                page.wait_for_function("""() => {
                    const root = document.querySelector('article,main,[role=main],#content,.content') || document.body;
                    return root && (root.innerText || '').trim().length >= 20;
                }""", timeout=remaining_ms())
                checkpoint()
                if routed_error:
                    raise routed_error[0]
                html = page.content()
                if len(html.encode("utf-8")) > limits.decompressed_bytes:
                    raise PublicError("resource_limit", "Rendered body exceeds its limit.", 422)
                final = bounded_validation(validate_url, page.url, deadline)
                return FetchedDocument(final.url, page.title(), html, requested_url=request.url,
                                       payload=html.encode("utf-8"), metadata={"rendered": True,
                                       "browser_requests": requests, "decoded_bytes": consumed})
        except ApplicationError:
            raise
        except PublicError as error:
            raise wrap_error(ErrorKind.POLICY, error.code, "Browser request violated policy.",
                             retryable=False, cause=error) from error
        except Exception as error:
            if routed_error:
                first = routed_error[0]
                if isinstance(first, ApplicationError):
                    raise first
                if isinstance(first, PublicError):
                    raise wrap_error(ErrorKind.POLICY, first.code, "Browser request violated policy.",
                                     retryable=False, cause=first) from first
            raise wrap_error(ErrorKind.NETWORK, "rendered_fetch_failed", "Rendered navigation failed.",
                             retryable=False, cause=error) from error
        finally:
            client.close()
            for resource in (page, context, browser):
                closer = getattr(resource, "close", None)
                if callable(closer):
                    try:
                        closer()
                        METRICS.increment("resource_cleanup_total", capability=type(resource).__name__, outcome="succeeded")
                    except Exception:
                        METRICS.increment("resource_cleanup_total", capability=type(resource).__name__, outcome="failed")
            if entered and manager is not None:
                manager.__exit__(None, None, None)

    def close(self) -> None:
        return None
