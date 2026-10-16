from __future__ import annotations

import threading
from datetime import datetime, timedelta, timezone

import pytest

from se_kb_app.errors import ApplicationError
from se_kb_app.jobs.models import JobProgress, JobResultReference, JobSnapshot, JobStatus, JobSubmission
from se_kb_app.jobs.runner import ManagedJobRunner
from se_kb_app.jobs.store import JobStore


class DeterministicSources:
    def __init__(self) -> None:
        self.current = datetime(2026, 9, 15, tzinfo=timezone.utc)
        self.identifier = 0
        self.lock = threading.Lock()

    def now(self) -> datetime:
        with self.lock:
            self.current += timedelta(milliseconds=1)
            return self.current

    def next_id(self) -> str:
        with self.lock:
            self.identifier += 1
            return f"job-{self.identifier}"


def make_store(*, maximum_events: int = 20) -> JobStore:
    sources = DeterministicSources()
    return JobStore(
        clock=sources.now,
        identifier_factory=sources.next_id,
        maximum_events=maximum_events,
    )


@pytest.mark.unit
def test_submission_is_immutable_and_invalid_transition_is_rejected():
    store = make_store()
    parameters = {"url": "https://example.com"}
    queued = store.submit("crawl", parameters)
    parameters["url"] = "mutated"
    assert queued.submission.parameters["url"] == "https://example.com"
    with pytest.raises(TypeError):
        queued.submission.parameters["url"] = "nope"
    with pytest.raises(ApplicationError) as caught:
        store.succeed(queued.identifier)
    assert caught.value.public_code == "invalid_job_transition"


@pytest.mark.unit
def test_late_success_after_cancel_preserves_cancelled_and_records_diagnostic():
    store = make_store()
    job = store.submit("crawl", {})
    store.start(job.identifier)
    store.cancel(job.identifier)
    snapshot = store.succeed(job.identifier, JobResultReference("late"))
    assert snapshot.status is JobStatus.CANCELLED
    assert store.events(job.identifier)[-1].kind == "late_transition"


@pytest.mark.unit
def test_simultaneous_reads_and_terminal_race_are_safe():
    store = make_store()
    job = store.submit("crawl", {})
    store.start(job.identifier)
    barrier = threading.Barrier(3)
    observed: list[JobStatus] = []

    def finish(status: JobStatus):
        barrier.wait()
        if status is JobStatus.SUCCEEDED:
            store.succeed(job.identifier)
        else:
            store.cancel(job.identifier)
        observed.append(store.get(job.identifier).status)

    threads = [
        threading.Thread(target=finish, args=(JobStatus.SUCCEEDED,)),
        threading.Thread(target=finish, args=(JobStatus.CANCELLED,)),
    ]
    for thread in threads:
        thread.start()
    barrier.wait()
    for thread in threads:
        thread.join(timeout=2)
    assert store.get(job.identifier).status in {JobStatus.SUCCEEDED, JobStatus.CANCELLED}
    assert all(status.terminal for status in observed)


@pytest.mark.unit
def test_event_history_is_bounded_and_cursor_based():
    store = make_store(maximum_events=3)
    job = store.submit("crawl", {})
    store.start(job.identifier)
    for completed in range(1, 5):
        store.progress(job.identifier, JobProgress(completed, 4, f"step-{completed}"))
    events = store.events(job.identifier)
    assert len(events) == 3
    assert [event.message for event in store.events(job.identifier, after_sequence=events[-2].sequence)] == [
        events[-1].message
    ]


@pytest.mark.unit
def test_restored_non_terminal_jobs_are_interrupted():
    submitted = datetime(2026, 9, 14, tzinfo=timezone.utc)
    prior = JobSnapshot(
        "old-job",
        JobSubmission("crawl", {"url": "https://example.com"}, submitted),
        JobStatus.RUNNING,
        JobProgress(50, 100, "half"),
        submitted,
    )
    store = JobStore(initial=[prior])
    recovered = store.get("old-job")
    assert recovered.status is JobStatus.INTERRUPTED
    assert recovered.error_code == "process_restarted"


@pytest.mark.integration
def test_queued_cancellation_never_runs_and_shutdown_stops_admission():
    store = make_store()
    runner = ManagedJobRunner(store, maximum_workers=1)
    first_started = threading.Event()
    release = threading.Event()
    second_ran = threading.Event()

    def first(token, progress):
        first_started.set()
        while not release.wait(timeout=0.01):
            token.checkpoint()
        return JobResultReference("first")

    def second(token, progress):
        second_ran.set()
        return JobResultReference("second")

    first_job = runner.submit("crawl", {}, first)
    assert first_started.wait(timeout=1)
    second_job = runner.submit("crawl", {}, second)
    runner.cancel(second_job.identifier)
    release.set()
    runner.shutdown(deadline_seconds=2)

    assert store.get(second_job.identifier).status is JobStatus.CANCELLED
    assert second_ran.is_set() is False
    assert store.get(first_job.identifier).status.terminal
    with pytest.raises(RuntimeError):
        runner.submit("crawl", {}, second)


@pytest.mark.contract
def test_web_compatibility_response_exposes_job_identity_in_headers(
    web_client, web_admin_headers, monkeypatch
):
    import web.app as web_app

    from concurrent.futures import Future
    monkeypatch.setattr(web_app.services.task_manager._executor, "submit", lambda *args, **kwargs: Future())
    web_app.services.task_manager.status = "idle"
    response = web_client.post(
        "/api/start", json={"query": "jobs", "limit": 1}, headers=web_admin_headers
    )
    identifier = response.headers["X-Job-ID"]
    assert set(response.get_json()) == {"message"}
    assert response.headers["Location"] == f"/api/jobs/{identifier}"

    state = web_client.get(
        f"/api/jobs/{identifier}", headers={"Authorization": "Bearer test-read-key"}
    )
    assert state.status_code == 200
    assert state.get_json()["status"] == "queued"

    cancelled = web_client.post(
        f"/api/jobs/{identifier}/cancel", headers=web_admin_headers
    )
    assert cancelled.status_code == 200
    assert cancelled.get_json()["status"] == "cancelled"


@pytest.mark.integration
def test_running_cancellation_reaches_worker_checkpoint_and_preserves_terminal_state():
    store = make_store()
    runner = ManagedJobRunner(store, maximum_workers=1)
    started = threading.Event()
    stopped = threading.Event()

    def cancellable(token, progress):
        started.set()
        try:
            while True:
                token.checkpoint()
                stopped.wait(timeout=0.005)
        finally:
            stopped.set()

    job = runner.submit("crawl", {}, cancellable)
    assert started.wait(timeout=1)
    runner.cancel(job.identifier)
    assert stopped.wait(timeout=1)
    runner.shutdown(deadline_seconds=1)
    assert store.get(job.identifier).status is JobStatus.CANCELLED


@pytest.mark.unit
def test_failure_cancel_race_and_partial_failure_keep_one_terminal_outcome():
    store = make_store()
    job = store.submit("crawl", {})
    store.start(job.identifier)
    barrier = threading.Barrier(3)

    def cancel():
        barrier.wait()
        store.cancel(job.identifier)

    def fail():
        barrier.wait()
        store.fail(job.identifier, "partial_failure")

    threads = [threading.Thread(target=cancel), threading.Thread(target=fail)]
    for thread in threads:
        thread.start()
    barrier.wait()
    for thread in threads:
        thread.join(timeout=1)
    snapshot = store.get(job.identifier)
    assert snapshot.status in {JobStatus.CANCELLED, JobStatus.FAILED}
    assert any(event.kind == "late_transition" for event in store.events(job.identifier))
