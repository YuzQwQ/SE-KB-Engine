from __future__ import annotations

import argparse
import hashlib
import os
import threading
from collections import Counter, deque
import ipaddress
import json
import statistics
import sys
import time
import tracemalloc
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import Any
from urllib.parse import urlsplit

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from se_kb_app.crawling.capacity import CrawlCapacity
from se_kb_app.crawling.http import PooledHttpFetcher
from se_kb_app.crawling.machine import FetchStateMachine
from se_kb_app.crawling.models import FetchPolicy
from se_kb_app.services.crawl import CrawlService
from se_kb_app.crawling.resources import process_resources
from se_kb_app.domain import FetchRequest
from service_boundary.fetch import FetchLimits
from service_boundary.url_policy import ValidatedURL
from tests.fixtures.http_server import local_http_fixture


def _local_validator(url: str) -> ValidatedURL:
    parsed = urlsplit(url)
    return ValidatedURL(
        url,
        parsed.hostname or "127.0.0.1",
        parsed.port or 80,
        (ipaddress.ip_address("127.0.0.1"),),
    )


def run_soak(*, requests: int = 100, workers: int = 8) -> dict[str, Any]:
    limits = FetchLimits(total_seconds=5, connect_seconds=1, read_seconds=2)
    capacity = CrawlCapacity(global_limit=min(4, workers), per_host_limit=1, queue_capacity=max(20, workers))
    latencies: list[float] = []
    errors: dict[str, int] = {}
    tracemalloc.start()
    started = time.perf_counter()
    with local_http_fixture() as (base_url, _counts):
        fetcher = PooledHttpFetcher(
            limits=limits,
            max_connections=workers,
            max_keepalive_connections=workers,
            url_validator=_local_validator,
        )

        service = CrawlService(FetchStateMachine(fetcher, policy=FetchPolicy(allow_rendered_fallback=False)), capacity=capacity)

        def fetch_one(index: int) -> None:
            item_started = time.perf_counter()
            try:
                service.fetch(FetchRequest(f"{base_url}/article?item={index}"))
            except Exception as error:
                name = type(error).__name__
                errors[name] = errors.get(name, 0) + 1
            finally:
                latencies.append(time.perf_counter() - item_started)

        with ThreadPoolExecutor(max_workers=workers, thread_name_prefix="crawl-soak") as executor:
            list(executor.map(fetch_one, range(requests)))
        service.close()
    elapsed = time.perf_counter() - started
    _current, peak_memory = tracemalloc.get_traced_memory()
    tracemalloc.stop()
    sorted_latencies = sorted(latencies)
    p95_index = min(len(sorted_latencies) - 1, max(0, round(len(sorted_latencies) * 0.95) - 1))
    return {
        "requests": requests,
        "successes": requests - sum(errors.values()),
        "errors": errors,
        "throughput_per_second": round(requests / elapsed, 2),
        "p95_latency_ms": round(sorted_latencies[p95_index] * 1000, 2),
        "mean_latency_ms": round(statistics.mean(latencies) * 1000, 2),
        "peak_python_memory_bytes": peak_memory,
        "queue_high_watermark": capacity.high_watermark,
        "final_queue_depth": capacity.depths[0],
        "final_active": capacity.depths[1],
        "client_closed": fetcher.client.is_closed,
    }


def run_endurance(seconds: float) -> dict[str, Any]:
    """Local mixed-outcome acceptance; bounded samples and persistent production service."""
    limits = FetchLimits(total_seconds=2, connect_seconds=1, read_seconds=0.3,
                         compressed_bytes=4096, decompressed_bytes=8192)
    capacity = CrawlCapacity(global_limit=4, per_host_limit=1, queue_capacity=20)
    outcomes: Counter[str] = Counter()
    unexpected: Counter[str] = Counter()
    latencies: deque[float] = deque(maxlen=2048)
    paths = [("/article", "success"), ("/article-redirect", "success"), ("/article-gzip", "success"),
             ("/article-delay", "success"), ("/challenge", "permanent"), ("/large", "policy")]
    baseline_threads = {thread.ident for thread in threading.enumerate()}
    relevant = [PROJECT_ROOT / name for name in ("se_kb_app/services/crawl.py", "se_kb_app/crawling/machine.py",
                "se_kb_app/crawling/http.py", "se_kb_app/crawling/capacity.py", "service_boundary/fetch.py",
                "service_boundary/transport.py", "utils/html_cleaner.py", "se_kb_app/extraction/blocks.py")]
    fingerprint = hashlib.sha256(b"".join(path.read_bytes() for path in relevant)).hexdigest()
    baseline_resources = process_resources()
    warm_resources = None
    samples = []
    started, cpu_started = time.monotonic(), time.process_time()
    next_sample = 60.0
    tracemalloc.start()
    with local_http_fixture() as (base, _):
        fetcher = PooledHttpFetcher(limits=limits, url_validator=_local_validator)
        service = CrawlService(FetchStateMachine(fetcher, policy=FetchPolicy(
            total_timeout_seconds=2, allow_rendered_fallback=False)), capacity=capacity)
        def perform(item):
            path, expected = item
            item_started = time.monotonic()
            try:
                actual = service.run(FetchRequest(base + path)).kind.value
            except Exception as error:
                actual = type(error).__name__
            return path, expected, actual, (time.monotonic() - item_started) * 1000

        while time.monotonic() - started < seconds:
            futures = [service.submit(perform, item) for item in paths]
            for future in futures:
                path, expected, actual, latency = future.result(timeout=5)
                outcomes[actual] += 1
                if actual != expected:
                    unexpected[f"{path}:{actual}"] += 1
                latencies.append(latency)
            elapsed = time.monotonic() - started
            if warm_resources is None and elapsed >= min(10, seconds / 2):
                warm_resources = process_resources()
            if elapsed >= next_sample:
                snapshot = {"elapsed_seconds": round(elapsed, 1), "operations": sum(outcomes.values()),
                            **process_resources(), "queue_depth": capacity.depths[0], "active": capacity.depths[1]}
                samples.append(snapshot)
                print(json.dumps({"progress": snapshot}), flush=True)
                next_sample += 60
            time.sleep(0.2)
        service.close()
    _current, peak = tracemalloc.get_traced_memory()
    tracemalloc.stop()
    elapsed = time.monotonic() - started
    values = sorted(latencies)
    return {"mode": "local-production-service-mixed", "requested_seconds": seconds,
            "elapsed_seconds": round(elapsed, 2), "outcomes": dict(outcomes),
            "unexpected": dict(unexpected), "samples_retained": len(values),
            "p50_latency_ms": round(statistics.median(values), 2),
            "p95_latency_ms": round(values[max(0, int(len(values) * .95) - 1)], 2),
            "cpu_seconds": round(time.process_time() - cpu_started, 2),
            "peak_python_memory_bytes": peak, "final_queue_depth": capacity.depths[0],
            "final_active": capacity.depths[1], "client_closed": fetcher.client.is_closed,
            "remaining_owned_threads": [thread.name for thread in threading.enumerate()
                                        if thread.ident not in baseline_threads and thread.name.startswith(("crawl-soak", "se-kb-crawl", "se-kb-browser"))],
            "browser_exercised": False, "rss_measured": process_resources()["rss_bytes"] is not None,
            "baseline_resources": baseline_resources, "warm_resources": warm_resources,
            "final_resources": process_resources(), "resource_samples": samples,
            "implementation_sha256": fingerprint,
            "implementation_unchanged": fingerprint == hashlib.sha256(b"".join(path.read_bytes() for path in relevant)).hexdigest(),
            "throughput_per_second": round(sum(outcomes.values()) / elapsed, 2)}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--seconds", type=float, default=0)
    parser.add_argument("--requests", type=int, default=100)
    parser.add_argument("--report", type=Path)
    args = parser.parse_args()
    if not 0 <= args.seconds <= 3600 or not 1 <= args.requests <= 10000:
        parser.error("seconds must be 0-3600 and requests 1-10000")
    os.environ["SE_KB_SKIP_DOTENV"] = "1"
    os.environ["NO_PROXY"] = "localhost,127.0.0.1,::1"
    report = run_endurance(args.seconds) if args.seconds else run_soak(requests=args.requests)
    payload = json.dumps(report, indent=2, sort_keys=True)
    if args.report:
        args.report.parent.mkdir(parents=True, exist_ok=True)
        args.report.write_text(payload + "\n", encoding="utf-8")
    print(payload)
    return int(bool(report.get("unexpected") or report.get("errors")))


if __name__ == "__main__":
    raise SystemExit(main())
