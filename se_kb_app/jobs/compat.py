from __future__ import annotations

from collections import defaultdict, deque
from contextvars import ContextVar
from contextlib import contextmanager
import atexit
from threading import RLock
from typing import Any, Mapping

from se_kb_app.jobs.context import current_cancellation
from se_kb_app.jobs.executor import BoundedExecutor
from se_kb_app.errors import ApplicationError, ErrorKind
from service_boundary.audit import redact

from se_kb_app.jobs.models import JobProgress, JobStatus
from se_kb_app.jobs.store import JobStore


class LegacyTaskView:
    """Temporary Web compatibility view backed by isolated job records."""

    def __init__(self, *, log_limit: int = 200, result_limit: int = 100) -> None:
        self.store = JobStore(maximum_events=log_limit)
        self.log_limit = log_limit
        self.result_limit = result_limit
        self._latest_job_id: str | None = None
        self._bound: ContextVar[str | None] = ContextVar("legacy_job", default=None)
        self._executor = BoundedExecutor(4, 16, name="se-kb-web-job")
        self._pending: set[str] = set()
        atexit.register(self.close)
        self._logs: dict[str, deque[dict[str, Any]]] = defaultdict(
            lambda: deque(maxlen=self.log_limit)
        )
        self._results: dict[str, deque[Any]] = defaultdict(
            lambda: deque(maxlen=self.result_limit)
        )
        self._stats: dict[str, dict[str, Any]] = defaultdict(dict)
        self.lock = RLock()

    @property
    def current_job_id(self) -> str | None:
        return self._bound.get() or self._latest_job_id

    @current_job_id.setter
    def current_job_id(self, value: str | None) -> None:
        if self._bound.get() is None:
            self._latest_job_id = value

    @contextmanager
    def bind(self, identifier: str):
        binding = self._bound.set(identifier)
        cancellation = current_cancellation.set(self.store.token(identifier))
        try:
            yield
        finally:
            current_cancellation.reset(cancellation)
            self._bound.reset(binding)

    def submit(self, operation: str, parameters: Mapping[str, object], function, *args) -> str:
        with self.lock:
            if self.status == "running":
                raise ApplicationError(ErrorKind.POLICY, "job_conflict", "A task is already running.")
            identifier = self.create_job(operation, parameters)
            self.store.hold(identifier)
            self._pending.add(identifier)
            try:
                future = self._executor.submit(self._run, identifier, function, *args)
            except BaseException:
                self._pending.discard(identifier)
                self.store.cancel(identifier)
                self.store.release(identifier)
                raise
            future.add_done_callback(lambda _: self._finished(identifier))
            return identifier

    def _run(self, identifier: str, function, *args) -> None:
        with self.bind(identifier):
            try:
                self.checkpoint()
                function(*args, job_id=identifier)
            except ApplicationError as error:
                if error.kind is not ErrorKind.CANCELLATION:
                    if self.store.get(identifier).status is JobStatus.QUEUED:
                        self.store.start(identifier)
                    self.store.fail(identifier, error.public_code)
            except Exception:
                if self.store.get(identifier).status is JobStatus.QUEUED:
                    self.store.start(identifier)
                self.store.fail(identifier, "job_failed")

    def _finished(self, identifier: str) -> None:
        with self.lock:
            self._pending.discard(identifier)
        self.store.release(identifier)
        self._prune_views()

    def _prune_views(self) -> None:
        with self.lock:
            retained = set(self.store.identifiers)
            if self._latest_job_id not in retained:
                self._latest_job_id = None
            for values in (self._logs, self._results, self._stats):
                for key in list(values):
                    if key not in retained:
                        del values[key]

    def checkpoint(self) -> None:
        identifier = self._bound.get()
        if identifier:
            self.store.token(identifier).checkpoint()

    def close(self) -> None:
        with self.lock:
            identifiers = list(self._pending)
        for identifier in identifiers:
            self.store.cancel(identifier)
        self._executor.close()

    def create_job(self, operation: str, parameters: Mapping[str, object]) -> str:
        snapshot = self.store.submit(operation, parameters)
        self._prune_views()
        with self.lock:
            self.current_job_id = snapshot.identifier
        return snapshot.identifier

    def clear(self, job_id: str | None = None, *, operation: str = "legacy-web-task") -> None:
        identifier = job_id or self.create_job(operation, {})
        with self.lock:
            self.current_job_id = identifier
            self._logs[identifier].clear()
            self._results[identifier].clear()
            self._stats[identifier] = {}

    @property
    def status(self) -> str:
        if self.current_job_id is None:
            return "idle"
        status = self.store.get(self.current_job_id).status
        return {
            JobStatus.QUEUED: "running",
            JobStatus.RUNNING: "running",
            JobStatus.SUCCEEDED: "completed",
            JobStatus.FAILED: "error",
            JobStatus.CANCELLED: "cancelled",
            JobStatus.INTERRUPTED: "interrupted",
        }[status]

    @status.setter
    def status(self, value: str) -> None:
        if value == "idle":
            self.current_job_id = None
            return
        identifier = self._ensure_current()
        snapshot = self.store.get(identifier)
        if value == "running" and snapshot.status is JobStatus.QUEUED:
            self.store.start(identifier)
        elif value == "completed" and not snapshot.status.terminal:
            self.store.succeed(identifier)
        elif value == "error" and not snapshot.status.terminal:
            self.store.fail(identifier, "legacy_task_failed")

    @property
    def progress(self) -> int:
        if self.current_job_id is None:
            return 0
        snapshot = self.store.get(self.current_job_id)
        return round(snapshot.progress.completed * 100 / snapshot.progress.total)

    @property
    def logs(self) -> deque[dict[str, Any]]:
        return self._logs[self._require_current()]

    @property
    def results(self) -> deque[Any]:
        self.checkpoint()
        return self._results[self._require_current()]

    @property
    def stats(self) -> dict[str, Any]:
        return self._stats[self._require_current()]

    @stats.setter
    def stats(self, value: Mapping[str, Any]) -> None:
        self._stats[self._require_current()] = dict(value)

    def log(self, message: str, level: str = "info") -> None:
        from datetime import datetime

        identifier = self._ensure_current()
        entry = {"time": datetime.now().strftime("%H:%M:%S"), "level": level, "message": redact(message)}
        with self.lock:
            self._logs[identifier].append(entry)
            self.store.note(identifier, "log", redact(message), {"level": level})

    def set_status(self, status: str, progress: int | None = None) -> None:
        identifier = self._ensure_current()
        snapshot = self.store.get(identifier)
        if status == "running" and snapshot.status is JobStatus.QUEUED:
            snapshot = self.store.start(identifier)
        if progress is not None and snapshot.status is JobStatus.RUNNING:
            self.store.progress(identifier, JobProgress(progress, 100, status))
        if status == "completed" and not self.store.get(identifier).status.terminal:
            self.store.succeed(identifier)
        elif status == "error" and not self.store.get(identifier).status.terminal:
            self.store.fail(identifier, "legacy_task_failed")

    def cancel(self, identifier: str) -> dict[str, Any]:
        self.store.cancel(identifier)
        return self.get_state(identifier)

    def get_state(self, identifier: str | None = None) -> dict[str, Any]:
        selected = identifier or self.current_job_id
        if selected is None:
            return {"job_id": None, "status": "idle", "progress": 0, "logs": [], "results": []}
        snapshot = self.store.get(selected)
        legacy_status = {
            JobStatus.QUEUED: "queued",
            JobStatus.RUNNING: "running",
            JobStatus.SUCCEEDED: "completed",
            JobStatus.FAILED: "error",
            JobStatus.CANCELLED: "cancelled",
            JobStatus.INTERRUPTED: "interrupted",
        }[snapshot.status]
        return {
            "job_id": selected,
            "status": legacy_status,
            "progress": round(snapshot.progress.completed * 100 / snapshot.progress.total),
            "logs": list(self._logs[selected])[-50:],
            "results": list(self._results[selected]),
            "stats": dict(self._stats[selected]),
            "error_code": snapshot.error_code,
        }

    def _ensure_current(self) -> str:
        return self.current_job_id or self.create_job("implicit-legacy-task", {})

    def _require_current(self) -> str:
        if self.current_job_id is None:
            self.current_job_id = self.create_job("implicit-legacy-task", {})
        return self.current_job_id
