from __future__ import annotations

import asyncio
import gzip
import ipaddress
import threading
from time import monotonic, sleep
from types import SimpleNamespace

import httpx
import pytest

from se_kb_app.crawling.capacity import CrawlCapacity
from se_kb_app.crawling.http import PooledHttpFetcher
from se_kb_app.crawling.machine import FetchStateMachine, classify_document
from se_kb_app.crawling.models import FetchPolicy, OutcomeKind
from se_kb_app.crawling.site import SitePolicy
from se_kb_app.domain import FetchRequest, FetchedDocument
from se_kb_app.errors import ApplicationError
from se_kb_app.jobs.compat import LegacyTaskView
from se_kb_app.jobs.executor import BoundedExecutor
from se_kb_app.jobs.store import JobStore, CancellationToken
from se_kb_app.services.crawl import CrawlService
from service_boundary.errors import PublicError
from service_boundary.fetch import FetchLimits, bounded_async_get, bounded_get
from service_boundary.transport import VerifiedHTTPTransport, _Backend, stateless_cookie_jar
from service_boundary.url_policy import ValidatedURL
from utils.webpage_crawler import WebpageCrawler


def validator(url):
    parsed = httpx.URL(url)
    return ValidatedURL(url, parsed.host, parsed.port or 443, (ipaddress.ip_address("93.184.216.34"),))


def make_service(handler, *, rendered=None, sites=False):
    fetcher = PooledHttpFetcher(url_validator=validator)
    fetcher.client.close()
    fetcher.client = httpx.Client(transport=httpx.MockTransport(handler), trust_env=False,
                                  cookies=stateless_cookie_jar())
    machine = FetchStateMachine(fetcher, rendered=rendered, sleep=lambda _: None)
    return CrawlService(machine, capacity=CrawlCapacity(global_limit=4, per_host_limit=1, queue_capacity=20),
                        sites=SitePolicy(fetcher) if sites else None)


@pytest.mark.parametrize("status", [403, 404, 429, 503])
def test_network_failure_does_not_trigger_browser_or_third_party(status, tmp_path):
    calls = []
    browser = SimpleNamespace(fetch=lambda request: pytest.fail("unexpected browser"), close=lambda: None)
    def handler(request):
        calls.append(str(request.url))
        return httpx.Response(status)
    service = make_service(handler, rendered=browser)
    try:
        result = WebpageCrawler(str(tmp_path), service=service).crawl_and_parse("https://fixture.invalid/fail", save_data=False)
        assert result["success"] is False
        assert len(calls) == (3 if status in {429, 503} else 1)
        assert all(url.startswith("https://fixture.invalid/") for url in calls)
    finally:
        service.close()


def test_production_facade_final_url_and_raw_snapshot(tmp_path):
    calls = []
    def handler(request):
        calls.append(str(request.url))
        if request.url.path == "/old":
            return httpx.Response(302, headers={"location": "/new/article"})
        return httpx.Response(200, headers={"content-type": "text/html; charset=utf-8"},
            content=b'<article><h1>Fixture</h1><p>Enough useful content for the production facade.</p><a href="reference">Reference</a></article>')
    service = make_service(handler)
    try:
        result = WebpageCrawler(str(tmp_path), service=service).crawl_and_parse("https://fixture.invalid/old")
        assert result["success"]
        assert result["parsed_data"]["source_url"] == "https://fixture.invalid/new/article"
        assert result["parsed_data"]["links"][0]["url"] == "https://fixture.invalid/new/reference"
        from pathlib import Path
        assert Path(result["file_paths"]["body_file"]).read_bytes().startswith(b"<article>")
        assert Path(result["file_paths"]["manifest_file"]).is_file()
        assert len(calls) == 2 and not result["metrics"]["fallback_used"]
    finally:
        service.close()


@pytest.mark.parametrize("rule,permitted", [("Disallow: /", False), ("Allow: /", True)])
def test_automatic_batches_apply_robots_and_cache(rule, permitted):
    calls = []
    def handler(request):
        calls.append(request.url.path)
        if request.url.path == "/robots.txt":
            return httpx.Response(200, content=("User-agent: *\n" + rule).encode())
        return httpx.Response(200, content=b"<article>useful article body for site policy tests</article>")
    service = make_service(handler, sites=True)
    try:
        for _ in range(2):
            outcome = service.run(FetchRequest("https://fixture.invalid/article", automatic=True))
            assert (outcome.kind is OutcomeKind.SUCCESS) == permitted
        assert calls.count("/robots.txt") == 1
        assert calls.count("/article") == (2 if permitted else 0)
    finally:
        service.close()


def test_unknown_robots_is_terminal_without_target_request():
    calls = []
    def handler(request):
        calls.append(request.url.path)
        return httpx.Response(503)
    service = make_service(handler, sites=True)
    try:
        outcome = service.run(FetchRequest("https://fixture.invalid/article", automatic=True))
        assert outcome.kind is OutcomeKind.POLICY_FAILURE
        assert calls == ["/robots.txt"]
    finally:
        service.close()


def test_classifier_accepts_captcha_discussion_but_rejects_empty_spa():
    article = FetchedDocument("https://fixture.invalid", "Technical article",
        "<article><h1>CAPTCHA implementation</h1><p>Discuss captcha and login required handling in code.</p></article>")
    shell = FetchedDocument("https://fixture.invalid", "App",
        '<html><div id="root"></div><script src="app.js"></script></html>')
    assert classify_document(article, FetchPolicy()).value == "acceptable"
    assert classify_document(shell, FetchPolicy()).value == "no_content"


def test_robots_html_challenge_cannot_silently_allow_automatic_fetch():
    calls = []
    def handler(request):
        calls.append(request.url.path)
        return httpx.Response(200, text="<html><body>challenge instead of robots</body></html>")
    service = make_service(handler, sites=True)
    try:
        assert service.run(FetchRequest("https://fixture.invalid/article", automatic=True)).kind is OutcomeKind.POLICY_FAILURE
        assert calls == ["/robots.txt"]
    finally:
        service.close()


def test_cancelled_job_cannot_publish_or_contaminate_replacement():
    manager = LegacyTaskView()
    entered, release, stopped, second_done = (threading.Event() for _ in range(4))
    published = []
    def first(*, job_id):
        manager.set_status("running", 1)
        entered.set()
        release.wait(timeout=2)
        manager.log("late original diagnostic")
        try:
            manager.checkpoint()
            published.append(job_id)
        finally:
            stopped.set()
    def second(*, job_id):
        manager.set_status("running", 1)
        manager.log("replacement diagnostic")
        manager.set_status("completed", 100)
        second_done.set()
    try:
        first_id = manager.submit("first", {}, first)
        assert entered.wait(timeout=1)
        manager.cancel(first_id)
        second_id = manager.submit("second", {}, second)
        assert second_done.wait(timeout=1)
        release.set()
        assert stopped.wait(timeout=1)
        assert published == []
        assert manager.get_state(first_id)["status"] == "cancelled"
        assert manager.get_state(second_id)["status"] == "completed"
        assert all("original" not in item["message"] for item in manager.get_state(second_id)["logs"])
        assert any("original" in item["message"] for item in manager.get_state(first_id)["logs"])
    finally:
        release.set()
        manager.close()


def test_running_future_keeps_admission_until_it_exits():
    executor = BoundedExecutor(1, 1)
    entered, release = threading.Event(), threading.Event()
    def blocking():
        entered.set()
        release.wait(timeout=2)
    try:
        first = executor.submit(blocking)
        assert entered.wait(timeout=1)
        second = executor.submit(lambda: None)
        assert not first.cancel()
        with pytest.raises(ApplicationError):
            executor.submit(lambda: None)
        release.set()
        first.result(timeout=1)
        second.result(timeout=1)
    finally:
        release.set()
        executor.close()
    assert executor.pending == 0


def test_history_retention_preserves_live_worker_records():
    store = JobStore(maximum_history=2)
    held = store.submit("held", {})
    store.hold(held.identifier)
    store.cancel(held.identifier)
    for _ in range(6):
        job = store.submit("done", {})
        store.start(job.identifier)
        store.succeed(job.identifier)
    assert store.get(held.identifier).status.value == "cancelled"
    store.release(held.identifier)
    assert len(store.identifiers) <= 2


def test_gzip_expansion_is_rejected_before_unbounded_output():
    class Stream(httpx.SyncByteStream):
        def __iter__(self):
            yield gzip.compress(b"x" * 100_000)
    with httpx.Client(transport=httpx.MockTransport(lambda _: httpx.Response(
        200, headers={"content-encoding": "gzip"}, stream=Stream()))) as client:
        with pytest.raises(PublicError):
            bounded_get(client, "https://fixture.invalid", url_validator=validator,
                        limits=FetchLimits(decompressed_bytes=64))


def test_dns_transport_connects_verified_ip_and_keeps_tls_origin():
    seen = []
    class Stream:
        def write(self, buffer, timeout=None):
            seen.append(buffer)
        def read(self, max_bytes, timeout=None):
            return b"HTTP/1.1 200 OK\r\nContent-Length: 2\r\n\r\nok"
        def start_tls(self, ssl_context, server_hostname=None, timeout=None):
            seen.append(server_hostname)
            return self
        def get_extra_info(self, info):
            return None
        def close(self):
            return None
    class Backend:
        def connect_tcp(self, host, port, **kwargs):
            seen.append(host)
            return Stream()
    transport = VerifiedHTTPTransport()
    transport._pool._network_backend = _Backend(Backend())
    with httpx.Client(transport=transport, trust_env=False) as client:
        _, payload = bounded_get(client, "https://fixture.invalid/a", url_validator=validator)
    assert payload == b"ok"
    assert seen[0] == "93.184.216.34"
    assert "fixture.invalid" in seen
    assert any(isinstance(item, bytes) and b"Host: fixture.invalid" in item for item in seen)


def test_async_redirect_also_strips_credentials():
    observed = []
    def handler(request):
        observed.append(request)
        return httpx.Response(302, headers={"location": "https://two.invalid/"}) if len(observed) == 1 else httpx.Response(200, content=b"body")
    async def run():
        async with httpx.AsyncClient(transport=httpx.MockTransport(handler),
                                     headers={"Authorization": "Bearer fake"}, cookies={"session": "fake"}) as client:
            await bounded_async_get(client, "https://one.invalid/", url_validator=validator)
    asyncio.run(run())
    assert "authorization" not in observed[1].headers and "cookie" not in observed[1].headers


def test_long_retry_after_does_not_retry_early_or_fallback():
    attempts = []
    def handler(request):
        attempts.append(request)
        return httpx.Response(429, headers={"retry-after": "300"})
    service = make_service(handler)
    try:
        outcome = service.run(FetchRequest("https://fixture.invalid/a", deadline=monotonic() + 1))
        assert outcome.kind is OutcomeKind.TRANSIENT_FAILURE
        assert len(attempts) == 1
    finally:
        service.close()


def test_capacity_does_not_reserve_global_slot_for_waiting_host():
    capacity = CrawlCapacity(global_limit=2, per_host_limit=1, queue_capacity=4)
    first, release, other = threading.Event(), threading.Event(), threading.Event()
    def occupy():
        with capacity.slot("https://a.invalid/one"):
            first.set()
            release.wait(timeout=2)
    def wait_same():
        with capacity.slot("https://a.invalid/two"):
            return None
    def run_other():
        with capacity.slot("https://b.invalid/"):
            other.set()
    threads = [threading.Thread(target=occupy), threading.Thread(target=wait_same), threading.Thread(target=run_other)]
    threads[0].start()
    assert first.wait(timeout=1)
    threads[1].start()
    deadline = monotonic() + 1
    while capacity.depths[0] != 1 and monotonic() < deadline:
        sleep(.005)
    threads[2].start()
    try:
        assert other.wait(timeout=1)
    finally:
        release.set()
        for thread in threads:
            thread.join(timeout=2)
    assert capacity.depths == (0, 0)


def test_mcp_composite_calls_internal_service_after_auth(isolated_data_root, monkeypatch):
    import server
    monkeypatch.setenv("KB_ADMIN_KEYS", "test-admin")
    monkeypatch.setenv("KB_READ_KEYS", "")
    calls = []
    async def internal(url, **kwargs):
        calls.append((url, kwargs))
        return "fixture content"
    async def blocking(function, *args, **kwargs):
        return function(*args, **kwargs)
    monkeypatch.setattr(server, "_scrape_webpage", internal)
    monkeypatch.setattr(server, "_run_crawl_blocking", blocking)
    monkeypatch.setattr(server.crawler, "search_and_parse", lambda *args: {"parsed_response": {
        "success": True, "results": [{"url": "https://fixture.invalid/a", "title": "Fixture"}]}})
    monkeypatch.setattr(server, "get_deduplication_instance", lambda: SimpleNamespace(
        is_url_duplicate=lambda url: (False, None), get_stats=lambda: {}))
    result = asyncio.run(server.search_and_scrape("fixture", 1, authorization="Bearer test-admin"))
    assert len(calls) == 1 and calls[0][1]["automatic"] is True
    assert "fixture content" in result
    with pytest.raises(PublicError):
        asyncio.run(server.search_and_scrape("fixture", 1))


def test_cancel_before_snapshot_has_no_publication(tmp_path):
    token = CancellationToken()
    def handler(request):
        token.cancel()
        return httpx.Response(200, content=b"<article>content that must not be published after cancellation</article>")
    service = make_service(handler)
    try:
        with pytest.raises(ApplicationError):
            WebpageCrawler(str(tmp_path), service=service).crawl_and_parse(
                "https://fixture.invalid/a", cancellation=token)
        assert not list(tmp_path.rglob("*.json"))
    finally:
        service.close()


def test_pathological_dom_is_terminal_without_browser():
    body = "<div>" * 150 + "content" + "</div>" * 150
    browser = SimpleNamespace(fetch=lambda request: pytest.fail("unexpected browser"), close=lambda: None)
    service = make_service(lambda request: httpx.Response(200, text=body), rendered=browser)
    try:
        assert service.run(FetchRequest("https://fixture.invalid/deep")).kind is OutcomeKind.POLICY_FAILURE
    finally:
        service.close()


def test_selected_unavailable_transport_never_sends_direct_request():
    service = make_service(lambda request: pytest.fail("unexpected direct connection"))
    service.use_tor = True
    try:
        with pytest.raises(ApplicationError) as error:
            service.run(FetchRequest("https://fixture.invalid/a"))
        assert error.value.public_code == "crawl_transport_unavailable"
    finally:
        service.close()


def test_deflate_split_header_and_encoding_fallback():
    import zlib
    from service_boundary.decoding import decode_payload
    payload = zlib.compress(b"bounded deflate content")
    class Stream(httpx.SyncByteStream):
        def __iter__(self):
            yield payload[:1]
            yield payload[1:]
    with httpx.Client(transport=httpx.MockTransport(lambda request: httpx.Response(
        200, headers={"content-encoding": "deflate"}, stream=Stream()))) as client:
        _, actual = bounded_get(client, "https://fixture.invalid/a", url_validator=validator)
        assert actual == b"bounded deflate content"
    text = "中文编码测试"
    assert decode_payload(text.encode("gb18030"), "text/html; charset=gb18030")[0] == text
    assert decode_payload(text.encode("utf-8"), "text/html; charset=not-a-codec")[0] == text


def test_shared_fetcher_does_not_retain_cross_job_cookies():
    seen = []
    def handler(request):
        seen.append(request.headers.get("cookie"))
        return httpx.Response(200, content=b"<article>public article for cookie isolation</article>",
                              headers={"set-cookie": "session=private; Path=/"})
    service = make_service(handler)
    try:
        service.fetch(FetchRequest("https://fixture.invalid/a"))
        service.fetch(FetchRequest("https://fixture.invalid/b"))
        assert seen == [None, None]
    finally:
        service.close()


def test_content_dedup_preserves_operators_indentation_and_legacy_rows(tmp_path):
    from utils.web_deduplication import WebDeduplication
    dedup = WebDeduplication(str(tmp_path / "cache.db"))
    dedup.enable_content_dedup = True
    dedup.enable_near_content_dedup = False
    dedup.add_content_cache("if x > 0:\n    accept()", "positive", "https://fixture.invalid/a")
    found, info = dedup.is_content_duplicate("if x > 0:\n    accept()")
    assert found and info["cached_title"] == "positive"
    assert dedup.is_content_duplicate("if x < 0:\n    accept()") == (False, None)
    assert dedup.is_content_duplicate("if x > 0:\naccept()") == (False, None)
    assert dedup.generate_content_hash("a\r\nb") == dedup.generate_content_hash("a\nb")
    assert len(dedup.generate_content_fingerprint("中文" * 10000)) <= 2048


def test_web_worker_uses_shared_acquisition_and_unique_publication(isolated_data_root, monkeypatch):
    import json
    from pathlib import Path
    import web.services as services

    calls = []
    def handler(request):
        calls.append(request.url.path)
        return httpx.Response(200, text="<article><h1>Fixture</h1><p>Shared production worker fixture.</p><pre><code>x = 1\n  y = 2</code></pre></article>")

    service = make_service(handler)
    manager = LegacyTaskView()
    monkeypatch.setattr(services, "task_manager", manager)
    monkeypatch.setattr(services, "crawl_service", service)
    index = services.UrlIndex()
    index.index_file = isolated_data_root / "data" / "index.json"
    index.urls = {}
    monkeypatch.setattr(services, "url_index", index)
    monkeypatch.setattr(services, "WebpageCrawler", lambda **kwargs: WebpageCrawler(
        str(isolated_data_root / "data"), **kwargs))
    try:
        identifier = manager.submit("manual-crawl", {"url": "https://fixture.invalid/a"},
                                    services.run_manual_crawl_task, "https://fixture.invalid/a", None, False)
        end = monotonic() + 3
        while not manager.store.get(identifier).status.terminal and monotonic() < end:
            sleep(.01)
        assert manager.get_state(identifier)["status"] == "completed"
        assert calls == ["/a"]
        manifests = list((isolated_data_root / "data" / "crawl_snapshots").glob("*.json"))
        assert len(manifests) == 1
        manifest = json.loads(manifests[0].read_text(encoding="utf-8"))
        parsed = json.loads(Path(manifest["parsed_file"]).read_text(encoding="utf-8"))
        assert parsed["blocks"][-1]["text"] == "x = 1\n  y = 2"
        assert index.exists("https://fixture.invalid/a")
    finally:
        manager.close()
        service.close()


def test_mcp_compatibility_publication_is_unique_atomic_and_guarded(isolated_data_root, monkeypatch):
    import server
    monkeypatch.setattr(server, "JSON_LLM_READY_DIR", isolated_data_root / "json")
    monkeypatch.setattr(server, "MARKDOWN_LLM_READY_DIR", isolated_data_root / "markdown")
    first = server._save_crawl_compatibility({"page": 1}, "first", "中文标题", "2026-10-16T18-00-00")
    second = server._save_crawl_compatibility({"page": 2}, "second", "中文标题", "2026-10-16T18-00-00")
    assert first[0] != second[0] and first[1] != second[1]
    from service_boundary.inputs import path_component
    assert path_component(first[2], "base_filename") == first[2]
    assert first[1].read_text(encoding="utf-8") == "first"
    assert second[1].read_text(encoding="utf-8") == "second"
    token = CancellationToken()
    token.cancel()
    from se_kb_app.jobs.context import current_cancellation
    context = current_cancellation.set(token)
    try:
        with pytest.raises(ApplicationError):
            server._save_crawl_compatibility({}, "cancelled", "same title", "2026-10-16T18-00-00")
    finally:
        current_cancellation.reset(context)
    assert len(list((isolated_data_root / "json").glob("*.json"))) == 2


def test_mcp_knowledge_storage_has_authenticated_adapter_and_internal_business_call(isolated_data_root, monkeypatch):
    import server
    monkeypatch.setenv("KB_ADMIN_KEYS", "test-admin")
    monkeypatch.setenv("KB_READ_KEYS", "")
    calls = []
    class Processor:
        def __init__(self, **kwargs):
            pass
        def get_format_name(self):
            return "fixture"
        def save_knowledge_base(self, data, name):
            calls.append((data, name))
            return {"success": True, "saved_files": [], "summary_file": "fixture.json", "statistics": {}}
    monkeypatch.setattr(server, "FormatProcessor", Processor)
    assert "SUCCESS" in server._save_to_knowledge_base('{"page": 1}', "fixture")
    assert "SUCCESS" in server.save_to_knowledge_base('{"page": 2}', "fixture", authorization="Bearer test-admin")
    assert len(calls) == 2
    with pytest.raises(PublicError):
        server.save_to_knowledge_base('{"page": 3}', "fixture")


def test_legacy_knowledge_categories_and_summary_are_persisted(tmp_path):
    import json
    from pathlib import Path
    from scripts.format_processor import FormatProcessor
    processor = FormatProcessor.__new__(FormatProcessor)
    processor.template = {"json_structure": {"knowledge_categories": [
        {"key": "dfd_concepts", "description": "concepts", "fields": {"name": "string"}}]}}
    data = {"dfd_concepts": [{"name": "fixture"}], "metadata": {"source_url": "https://fixture.invalid/a"}}
    result = processor.save_knowledge_base(data, "crawl_unique", tmp_path)
    assert result["success"]
    category = json.loads(Path(result["saved_files"][0]).read_text(encoding="utf-8"))
    assert category["data"] == data["dfd_concepts"]
    assert json.loads(Path(result["summary_file"]).read_text(encoding="utf-8"))["saved_files"] == result["saved_files"]
