from __future__ import annotations

import threading
import ipaddress
from datetime import datetime, timezone
from urllib.parse import urlsplit

import pytest

from se_kb_app.crawling.backoff import BackoffPolicy
from se_kb_app.crawling.capacity import CrawlCapacity
from se_kb_app.crawling.http import PooledHttpFetcher, RequestMetadataCache, canonical_url
from se_kb_app.domain import FetchRequest
from se_kb_app.errors import ApplicationError
from service_boundary.fetch import FetchLimits
from service_boundary.url_policy import ValidatedURL
from tests.fixtures.http_server import local_http_fixture


@pytest.mark.unit
def test_backoff_is_exponential_jittered_capped_and_honors_retry_after():
    policy = BackoffPolicy(base_seconds=1, maximum_seconds=5, jitter_ratio=0.2)
    def now():
        return datetime(2026, 9, 15, tzinfo=timezone.utc)
    assert policy.delay(1, now=now, jitter=lambda: 0.5) == 1
    assert policy.delay(3, now=now, jitter=lambda: 0.5) == 4
    assert policy.delay(9, now=now, jitter=lambda: 1.0) == 5
    assert policy.delay(1, retry_after="3", now=now) == 3
    assert policy.delay(1, retry_after="Tue, 15 Sep 2026 00:00:04 GMT", now=now) == 4


@pytest.mark.unit
def test_capacity_rejects_beyond_bound_and_tracks_depth():
    capacity = CrawlCapacity(global_limit=1, per_host_limit=1, queue_capacity=1)
    entered = threading.Event()
    release = threading.Event()

    def occupy():
        with capacity.slot("https://example.com/a"):
            entered.set()
            release.wait(timeout=2)

    worker = threading.Thread(target=occupy)
    worker.start()
    assert entered.wait(timeout=1)
    with pytest.raises(ApplicationError) as caught:
        with capacity.slot("https://example.com/b"):
            pass
    assert caught.value.public_code == "crawl_capacity_exceeded"
    assert capacity.depths == (0, 1)
    release.set()
    worker.join(timeout=2)
    assert capacity.depths == (0, 0)


@pytest.mark.integration
def test_pooled_fetcher_streams_bounds_classifies_errors_and_reuses_conditionals():
    def local_validator(url: str) -> ValidatedURL:
        parsed = urlsplit(url)
        return ValidatedURL(
            url,
            parsed.hostname or "127.0.0.1",
            parsed.port or 80,
            (ipaddress.ip_address("127.0.0.1"),),
        )

    limits = FetchLimits(
        redirects=2,
        compressed_bytes=1024,
        decompressed_bytes=2048,
        total_seconds=2,
        connect_seconds=1,
        read_seconds=1,
        write_seconds=1,
        pool_seconds=1,
    )
    cache = RequestMetadataCache()
    with local_http_fixture() as (base_url, counts):
        fetcher = PooledHttpFetcher(limits=limits, metadata=cache, url_validator=local_validator, conditional_requests=True)
        try:
            result = fetcher.fetch(FetchRequest(f"{base_url}/ok"))
            assert result.title == "Fixture"
            with pytest.raises(ApplicationError) as retry_error:
                fetcher.fetch(FetchRequest(f"{base_url}/retry"))
            assert retry_error.value.retryable is True
            with pytest.raises(ApplicationError) as size_error:
                fetcher.fetch(FetchRequest(f"{base_url}/large"))
            assert size_error.value.retryable is False
            fetcher.fetch(FetchRequest(f"{base_url}/etag"))
            assert cache.headers_for(f"{base_url}/etag") == {"If-None-Match": '"fixture-v1"'}
            fetcher.fetch(FetchRequest(f"{base_url}/etag"))
            assert counts["/etag"] == 2
        finally:
            fetcher.close()
        assert fetcher.client.is_closed


@pytest.mark.unit
def test_canonical_deduplication_does_not_mutate_input():
    original = "HTTPS://Example.COM/path?utm_source=x&b=2&a=1#fragment"
    assert canonical_url(original) == "https://example.com/path?b=2&a=1"
    assert original.endswith("#fragment")
