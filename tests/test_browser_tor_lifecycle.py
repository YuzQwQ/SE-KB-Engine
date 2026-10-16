from __future__ import annotations

from pathlib import Path

import pytest

from se_kb_app.crawling.browser import PlaywrightRenderedFetcher
from se_kb_app.domain import FetchRequest
from se_kb_app.errors import ApplicationError
from se_kb_app.services.tor import TorController


class Resource:
    def __init__(self, name: str, events: list[str]) -> None:
        self.name = name
        self.events = events

    def close(self):
        self.events.append(f"close:{self.name}")


class Page(Resource):
    url = "https://example.com/final"

    def route(self, pattern, handler):
        self.events.append("route")

    def goto(self, url, **kwargs):
        self.events.append(f"goto:{kwargs['timeout']}")
        if "fail" in url:
            raise TimeoutError("private browser detail")

    def content(self):
        return "<article>rendered content</article>"

    def title(self):
        return "Rendered"


class Context(Resource):
    def new_page(self):
        return Page("page", self.events)

    def set_default_timeout(self, value):
        assert 0 < value <= 2000

    def route_web_socket(self, pattern, handler):
        self.events.append("websocket-block")

    def route(self, pattern, handler):
        self.events.append("route")


class Browser(Resource):
    def new_context(self, **kwargs):
        return Context("context", self.events)


class Runtime:
    def __init__(self, events):
        self.chromium = self
        self.events = events

    def launch(self, **kwargs):
        return Browser("browser", self.events)


class Manager:
    def __init__(self, events):
        self.events = events

    def __enter__(self):
        return Runtime(self.events)

    def __exit__(self, *args):
        self.events.append("close:playwright")


@pytest.mark.unit
def test_browser_context_is_isolated_timeout_bound_and_closed_on_failure(monkeypatch):
    monkeypatch.setattr("se_kb_app.crawling.browser.validate_url", lambda url: type("URL", (), {"url": url})())
    events: list[str] = []
    fetcher = PlaywrightRenderedFetcher(timeout_ms=2000, playwright_factory=lambda: Manager(events))
    with pytest.raises(ApplicationError):
        fetcher.fetch(FetchRequest("https://example.com/fail"))
    assert "route" in events and "websocket-block" in events
    assert any(event.startswith("goto:") and 0 < int(event.split(":")[1]) <= 2000 for event in events)
    assert events[-4:] == ["close:page", "close:context", "close:browser", "close:playwright"]


@pytest.mark.unit
@pytest.mark.parametrize("route_install_fails", [False, True])
def test_browser_child_request_and_interception_failure_are_closed(monkeypatch, route_install_fails):
    from types import SimpleNamespace
    from service_boundary.errors import PublicError

    events = []
    monkeypatch.setattr("se_kb_app.crawling.browser.validate_url", lambda url: SimpleNamespace(url=url))

    def reject_private(client, url, **kwargs):
        assert url == "http://127.0.0.1/private"
        raise PublicError("blocked_url", "Private target is blocked.", 422)

    monkeypatch.setattr("se_kb_app.crawling.browser.bounded_get", reject_private)

    class RoutedPage(Page):
        def goto(self, url, **kwargs):
            events.append("navigate")
            self.handler(SimpleNamespace(
                request=SimpleNamespace(url="http://127.0.0.1/private", method="GET", resource_type="document", headers={}),
                abort=lambda reason: events.append("abort"),
                fulfill=lambda **kwargs: pytest.fail("private request was fulfilled"),
            ))
            return None

    class RoutedContext(Context):
        def route(self, pattern, handler):
            if route_install_fails:
                raise RuntimeError("interception unavailable")
            self.handler = handler

        def new_page(self):
            page = RoutedPage("page", events)
            page.handler = self.handler
            return page

    class RoutedBrowser(Browser):
        def new_context(self, **kwargs):
            assert kwargs["service_workers"] == "block"
            return RoutedContext("context", events)

    class RoutedManager(Manager):
        def __enter__(self):
            return SimpleNamespace(chromium=SimpleNamespace(launch=lambda **kwargs: RoutedBrowser("browser", events)))

    fetcher = PlaywrightRenderedFetcher(timeout_ms=2000, playwright_factory=lambda: RoutedManager(events))
    with pytest.raises(ApplicationError):
        fetcher.fetch(FetchRequest("https://example.com/article"))
    assert ("navigate" in events) is not route_install_fails
    assert ("abort" in events) is not route_install_fails
    assert events[-3:] == ["close:context", "close:browser", "close:playwright"]


class Process:
    def __init__(self, *, exited: bool = False):
        self.exited = exited
        self.terminated = False

    def poll(self):
        return 1 if self.exited or self.terminated else None

    def terminate(self):
        self.terminated = True

    def wait(self, timeout):
        return 0

    def kill(self):
        self.terminated = True


@pytest.mark.unit
def test_tor_timeout_cleans_process_and_shutdown_is_idempotent(tmp_path: Path):
    process = Process()
    ticks = iter([0.0, 0.0, 2.0])
    controller = TorController(
        enabled=True,
        data_dir=tmp_path,
        process_factory=lambda *args, **kwargs: process,
        readiness_probe=lambda: False,
        startup_timeout_seconds=1,
        clock=lambda: next(ticks),
        sleeper=lambda _delay: None,
    )
    with pytest.raises(ApplicationError) as caught:
        controller.start()
    assert caught.value.public_code == "tor_start_timeout"
    assert process.terminated is True
    controller.close()


@pytest.mark.unit
def test_tor_startup_failure_leaves_no_owned_process(tmp_path: Path):
    def fail(*args, **kwargs):
        raise OSError("missing executable")

    controller = TorController(enabled=True, data_dir=tmp_path, process_factory=fail)
    with pytest.raises(ApplicationError) as caught:
        controller.start()
    assert caught.value.public_code == "tor_start_failed"
    assert controller.process is None
