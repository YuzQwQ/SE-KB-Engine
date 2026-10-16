from __future__ import annotations

from collections import deque
from contextlib import contextmanager
from datetime import timedelta
from collections.abc import Callable, Iterable, Mapping
from dataclasses import dataclass
from datetime import datetime, timezone
from threading import Event, RLock
from uuid import uuid4

from se_kb_app.errors import ApplicationError, ErrorKind
from se_kb_app.jobs.models import (
    ALLOWED_TRANSITIONS,
    JobEvent,
    JobProgress,
    JobResultReference,
    JobSnapshot,
    JobStatus,
    JobSubmission,
)


class CancellationToken:
    def __init__(self) -> None:
        self._event = Event()
        self._publication_lock = RLock()

    @property
    def cancelled(self) -> bool:
        return self._event.is_set()

    def cancel(self) -> None:
        with self._publication_lock:
            self._event.set()

    def checkpoint(self) -> None:
        if self.cancelled:
            raise ApplicationError(
                ErrorKind.CANCELLATION,
                "job_cancelled",
                "The job was cancelled.",
                retryable=False,
            )

    @contextmanager
    def publication(self):
        # cancel() acknowledges only after an already-started publish completes.
        with self._publication_lock:
            self.checkpoint()
            yield


@dataclass
class _Record:
    snapshot: JobSnapshot
    events: deque[JobEvent]
    token: CancellationToken
    next_sequence: int = 1


class JobStore:
    def __init__(
        self,
        *,
        clock: Callable[[], datetime] | None = None,
        identifier_factory: Callable[[], str] | None = None,
        maximum_events: int = 200,
        initial: Iterable[JobSnapshot] = (),
        maximum_history: int = 256,
        history_ttl_seconds: float = 3600,
    ) -> None:
        if maximum_events < 1:
            raise ValueError("maximum_events must be positive")
        self.clock = clock or (lambda: datetime.now(timezone.utc))
        self.identifier_factory = identifier_factory or (lambda: str(uuid4()))
        self.maximum_events = maximum_events
        self.maximum_history = maximum_history
        self.history_ttl_seconds = history_ttl_seconds
        self._held: set[str] = set()
        self._lock = RLock()
        self._records: dict[str, _Record] = {}
        for snapshot in initial:
            status = JobStatus.INTERRUPTED if not snapshot.status.terminal else snapshot.status
            recovered = JobSnapshot(
                snapshot.identifier,
                snapshot.submission,
                status,
                snapshot.progress,
                self.clock(),
                snapshot.result,
                "process_restarted" if status is JobStatus.INTERRUPTED else snapshot.error_code,
            )
            self._records[snapshot.identifier] = _Record(
                recovered, deque(maxlen=maximum_events), CancellationToken()
            )

    def submit(self, operation: str, parameters: Mapping[str, object]) -> JobSnapshot:
        now = self.clock()
        identifier = self.identifier_factory()
        snapshot = JobSnapshot(
            identifier,
            JobSubmission(operation, parameters, now),
            JobStatus.QUEUED,
            JobProgress(),
            now,
        )
        with self._lock:
            self._prune(incoming=1)
            if sum(not record.snapshot.status.terminal for record in self._records.values()) >= self.maximum_history:
                raise ApplicationError(ErrorKind.POLICY, "job_capacity_exceeded", "Job history capacity is full.", retryable=True)
            if identifier in self._records:
                raise ValueError("identifier factory returned a duplicate")
            record = _Record(snapshot, deque(maxlen=self.maximum_events), CancellationToken())
            self._records[identifier] = record
            self._append(record, "submitted", "Job accepted.")
        return snapshot

    @property
    def identifiers(self) -> tuple[str, ...]:
        with self._lock:
            return tuple(self._records)

    def hold(self, identifier: str) -> None:
        with self._lock:
            self._record(identifier)
            self._held.add(identifier)

    def release(self, identifier: str) -> None:
        with self._lock:
            self._held.discard(identifier)
            self._prune()

    def _prune(self, incoming: int = 0) -> None:
        expired = self.clock() - timedelta(seconds=self.history_ttl_seconds)
        candidates = sorted((record.snapshot.updated_at, identifier)
                            for identifier, record in self._records.items()
                            if record.snapshot.status.terminal and identifier not in self._held)
        for updated, identifier in candidates:
            if updated < expired or len(self._records) + incoming > self.maximum_history:
                del self._records[identifier]

    def get(self, identifier: str) -> JobSnapshot:
        with self._lock:
            return self._record(identifier).snapshot

    def token(self, identifier: str) -> CancellationToken:
        with self._lock:
            return self._record(identifier).token

    def start(self, identifier: str) -> JobSnapshot:
        return self._transition(identifier, JobStatus.RUNNING, "started", "Job started.")

    def progress(self, identifier: str, progress: JobProgress) -> JobSnapshot:
        with self._lock:
            record = self._record(identifier)
            if record.snapshot.status is not JobStatus.RUNNING:
                self._invalid(record.snapshot.status, JobStatus.RUNNING)
            record.snapshot = JobSnapshot(
                record.snapshot.identifier,
                record.snapshot.submission,
                record.snapshot.status,
                progress,
                self.clock(),
                record.snapshot.result,
                record.snapshot.error_code,
            )
            self._append(record, "progress", progress.message, {"completed": progress.completed, "total": progress.total})
            return record.snapshot

    def succeed(self, identifier: str, result: JobResultReference | None = None) -> JobSnapshot:
        return self._transition(identifier, JobStatus.SUCCEEDED, "succeeded", "Job succeeded.", result=result)

    def fail(self, identifier: str, error_code: str) -> JobSnapshot:
        return self._transition(identifier, JobStatus.FAILED, "failed", "Job failed.", error_code=error_code)

    def cancel(self, identifier: str) -> JobSnapshot:
        with self._lock:
            record = self._record(identifier)
            if record.snapshot.status.terminal:
                self._append(
                    record,
                    "late_transition",
                    "Ignored a late terminal transition.",
                    {"source": record.snapshot.status.value, "target": JobStatus.CANCELLED.value},
                )
                return record.snapshot
            record.token.cancel()
            return self._transition(identifier, JobStatus.CANCELLED, "cancelled", "Cancellation accepted.")

    def interrupt_non_terminal(self) -> int:
        with self._lock:
            identifiers = [key for key, value in self._records.items() if not value.snapshot.status.terminal]
        for identifier in identifiers:
            self._transition(
                identifier,
                JobStatus.INTERRUPTED,
                "interrupted",
                "Job interrupted during process recovery.",
                error_code="process_restarted",
            )
        return len(identifiers)

    def events(self, identifier: str, *, after_sequence: int = 0) -> tuple[JobEvent, ...]:
        with self._lock:
            return tuple(event for event in self._record(identifier).events if event.sequence > after_sequence)

    def note(
        self,
        identifier: str,
        kind: str,
        message: str,
        metadata: Mapping[str, object] | None = None,
    ) -> None:
        with self._lock:
            self._append(self._record(identifier), kind, message, metadata)

    def _transition(
        self,
        identifier: str,
        target: JobStatus,
        kind: str,
        message: str,
        *,
        result: JobResultReference | None = None,
        error_code: str | None = None,
    ) -> JobSnapshot:
        with self._lock:
            record = self._record(identifier)
            source = record.snapshot.status
            if source.terminal:
                self._append(
                    record,
                    "late_transition",
                    "Ignored a late terminal transition.",
                    {"source": source.value, "target": target.value},
                )
                return record.snapshot
            if target not in ALLOWED_TRANSITIONS[source]:
                self._invalid(source, target)
            record.snapshot = JobSnapshot(
                record.snapshot.identifier,
                record.snapshot.submission,
                target,
                record.snapshot.progress,
                self.clock(),
                result,
                error_code,
            )
            self._append(record, kind, message)
            return record.snapshot

    def _append(
        self,
        record: _Record,
        kind: str,
        message: str,
        metadata: Mapping[str, object] | None = None,
    ) -> None:
        record.events.append(
            JobEvent(record.next_sequence, self.clock(), kind, message, metadata or {})
        )
        record.next_sequence += 1

    def _record(self, identifier: str) -> _Record:
        try:
            return self._records[identifier]
        except KeyError as error:
            raise ApplicationError(
                ErrorKind.VALIDATION,
                "job_not_found",
                "The requested job does not exist.",
                retryable=False,
            ) from error

    @staticmethod
    def _invalid(source: JobStatus, target: JobStatus) -> None:
        raise ApplicationError(
            ErrorKind.VALIDATION,
            "invalid_job_transition",
            "The requested job transition is not allowed.",
            retryable=False,
            metadata={"source": source.value, "target": target.value},
        )
