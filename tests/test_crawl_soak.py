from __future__ import annotations

import threading
import time

import pytest

from scripts.run_offline_crawl_soak import run_soak
from se_kb_app.jobs.models import JobResultReference
from se_kb_app.jobs.runner import ManagedJobRunner
from se_kb_app.jobs.store import JobStore
from se_kb_app.services.events import InMemoryEventPublisher


@pytest.mark.integration
def test_offline_concurrent_soak_is_bounded_and_leaves_no_active_resources():
    baseline_threads = {thread.ident for thread in threading.enumerate()}
    report = run_soak(requests=40, workers=6)
    assert report["successes"] == 40
    assert report["errors"] == {}
    assert report["p95_latency_ms"] < 2000
    assert report["peak_python_memory_bytes"] < 64 * 1024 * 1024
    assert report["final_queue_depth"] == 0
    assert report["final_active"] == 0
    assert report["client_closed"] is True
    remaining = {thread.ident for thread in threading.enumerate() if thread.name.startswith("crawl-soak")}
    assert remaining.issubset(baseline_threads)


@pytest.mark.integration
def test_job_threads_and_event_subscriptions_return_to_baseline():
    baseline_names = {thread.name for thread in threading.enumerate()}
    events = InMemoryEventPublisher()
    runner = ManagedJobRunner(JobStore(), maximum_workers=1)
    done = threading.Event()

    def work(token, progress):
        done.set()
        return JobResultReference("done")

    runner.submit("cleanup", {}, work)
    assert done.wait(timeout=1)
    runner.shutdown(deadline_seconds=1)
    events.close()
    deadline = time.monotonic() + 1
    while time.monotonic() < deadline and any(
        thread.name.startswith("se-kb-job") for thread in threading.enumerate()
    ):
        time.sleep(0.01)
    assert events.snapshot() == ()
    assert not {
        thread.name
        for thread in threading.enumerate()
        if thread.name.startswith("se-kb-job") and thread.name not in baseline_names
    }
