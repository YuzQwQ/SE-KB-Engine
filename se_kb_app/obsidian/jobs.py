from __future__ import annotations

from threading import RLock
from typing import Any

from se_kb_app.jobs.models import JobProgress, JobResultReference, JobStatus
from se_kb_app.jobs.runner import ManagedJobRunner
from se_kb_app.jobs.store import JobStore
from se_kb_app.obsidian.models import ExportResult
from se_kb_app.obsidian.service import ObsidianVaultService
from se_kb_app.obsidian.source import KnowledgeSelection


class ObsidianJobManager:
    def __init__(self, service: ObsidianVaultService, *, store: JobStore | None = None) -> None:
        self.service = service
        self.store = store or JobStore()
        self.runner = ManagedJobRunner(self.store, maximum_workers=1)
        self._results: dict[str, ExportResult] = {}
        self._lock = RLock()

    def submit(self, selection: KnowledgeSelection) -> str:
        parameters = {
            "sources": selection.sources,
            "kinds": selection.kinds,
            "entity_kinds": selection.entity_kinds,
            "minimum_quality": selection.minimum_quality,
        }

        def run(token, report):
            result = self.service.export(
                selection,
                cancellation=token,
                progress=lambda completed, total, message: report(JobProgress(completed, total, message)),
            )
            with self._lock:
                self._results[result.corpus_fingerprint] = result
            return JobResultReference(result.corpus_fingerprint, "obsidian-vault")

        snapshot = self.runner.submit("obsidian-export", parameters, run)
        return snapshot.identifier

    def get_state(self, identifier: str) -> dict[str, Any]:
        snapshot = self.store.get(identifier)
        status = {
            JobStatus.QUEUED: "queued",
            JobStatus.RUNNING: "running",
            JobStatus.SUCCEEDED: "completed",
            JobStatus.FAILED: "error",
            JobStatus.CANCELLED: "cancelled",
            JobStatus.INTERRUPTED: "interrupted",
        }[snapshot.status]
        events = self.store.events(identifier)
        result = None
        if snapshot.result is not None:
            with self._lock:
                result = self._results.get(snapshot.result.identifier)
        return {
            "job_id": identifier,
            "operation": snapshot.submission.operation,
            "status": status,
            "progress": round(snapshot.progress.completed * 100 / snapshot.progress.total),
            "logs": [
                {
                    "time": event.occurred_at.isoformat(),
                    "level": "error" if event.kind == "failed" else "info",
                    "message": event.message,
                }
                for event in events[-50:]
            ],
            "results": [] if result is None else [result_payload(result)],
            "error_code": snapshot.error_code,
        }

    def cancel(self, identifier: str) -> dict[str, Any]:
        self.runner.cancel(identifier)
        return self.get_state(identifier)

    def close(self) -> None:
        self.runner.close()
        self.service.close()


def result_payload(result: ExportResult) -> dict[str, Any]:
    return {
        "corpus_fingerprint": result.corpus_fingerprint,
        "published_at": result.published_at.isoformat(),
        "counts": dict(result.counts),
        "logical_paths": list(result.logical_paths),
        "conflicts": list(result.conflicts),
        "skipped": list(result.skipped),
        "diagnostics": list(result.diagnostics),
    }

