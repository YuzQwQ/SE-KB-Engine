from __future__ import annotations

from collections.abc import Callable, Mapping
from concurrent.futures import Future
from threading import RLock
from time import perf_counter
from typing import Any

from se_kb_app.errors import ApplicationError
from se_kb_app.jobs.executor import BoundedExecutor
from se_kb_app.jobs.context import current_cancellation
from se_kb_app.jobs.models import JobProgress, JobResultReference, JobSnapshot
from se_kb_app.jobs.store import CancellationToken, JobStore
from se_kb_app.observability import METRICS, event_context


JobFunction = Callable[[CancellationToken, Callable[[JobProgress], None]], JobResultReference | None]


class ManagedJobRunner:
    def __init__(self, store: JobStore, *, maximum_workers: int = 4) -> None:
        self.store = store
        self._executor = BoundedExecutor(maximum_workers, 16, name="se-kb-job")
        self._futures: dict[str, Future[Any]] = {}
        self._lock = RLock()
        self._accepting = True

    def submit(
        self,
        operation: str,
        parameters: Mapping[str, object],
        function: JobFunction,
    ) -> JobSnapshot:
        with self._lock:
            if not self._accepting:
                raise RuntimeError("job runner is shutting down")
            snapshot = self.store.submit(operation, parameters)
            self.store.hold(snapshot.identifier)
            try:
                future = self._executor.submit(self._run, snapshot.identifier, function)
            except BaseException:
                self.store.cancel(snapshot.identifier)
                self.store.release(snapshot.identifier)
                raise
            self._futures[snapshot.identifier] = future
            future.add_done_callback(lambda item: self._finished(snapshot.identifier))
            METRICS.increment("jobs_total", operation=operation, outcome="submitted")
            METRICS.gauge("job_queue_depth", sum(not item.done() for item in self._futures.values()))
            return snapshot

    def _finished(self, identifier: str) -> None:
        with self._lock:
            self._futures.pop(identifier, None)
        self.store.release(identifier)

    def cancel(self, identifier: str) -> JobSnapshot:
        snapshot = self.store.cancel(identifier)
        with self._lock:
            future = self._futures.get(identifier)
        if future is not None:
            future.cancel()
        return snapshot

    def shutdown(self, *, deadline_seconds: float = 5.0) -> None:
        with self._lock:
            self._accepting = False
            identifiers = list(self._futures)
        for identifier in identifiers:
            if not self.store.get(identifier).status.terminal:
                self.store.cancel(identifier)
        self._executor.close(deadline_seconds)

    def close(self) -> None:
        self.shutdown()

    def _run(self, identifier: str, function: JobFunction) -> None:
        started = perf_counter()
        token = self.store.token(identifier)
        if token.cancelled:
            return
        submission = self.store.get(identifier).submission
        correlation = str(submission.parameters.get("correlation_id", identifier))

        with event_context(
            correlation_id=correlation,
            job_id=identifier,
            stage="managed_job",
        ):
            self.store.start(identifier)

            def report(progress: JobProgress) -> None:
                self.store.progress(identifier, progress)
                METRICS.increment("job_progress_events_total", operation=submission.operation)

            outcome = "succeeded"
            context = current_cancellation.set(token)
            try:
                result = function(token, report)
                token.checkpoint()
                self.store.succeed(identifier, result)
            except ApplicationError as error:
                if error.kind.value == "cancellation":
                    outcome = "cancelled"
                    self.store.cancel(identifier)
                else:
                    outcome = "failed"
                    self.store.fail(identifier, error.public_code)
            except Exception:
                outcome = "failed"
                self.store.fail(identifier, "job_failed")
            finally:
                current_cancellation.reset(context)
                METRICS.increment("jobs_total", operation=submission.operation, outcome=outcome)
                METRICS.observe(
                    "stage_duration_ms",
                    (perf_counter() - started) * 1000,
                    stage="managed_job",
                    outcome=outcome,
                )
                with self._lock:
                    METRICS.gauge(
                        "job_queue_depth",
                        sum(not item.done() for item in self._futures.values()),
                    )
