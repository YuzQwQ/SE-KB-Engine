from __future__ import annotations

import shutil
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Mapping

from se_kb_app.observability import EventContext, METRICS, emit_event


@dataclass(frozen=True)
class RuntimeBudgets:
    max_concurrency: int = 16
    max_response_bytes: int = 4 * 1024 * 1024
    max_tokens_per_task: int = 100_000
    max_task_seconds: float = 600.0
    max_queue_depth: int = 100
    memory_warning_bytes: int = 1024 * 1024 * 1024
    disk_warning_free_bytes: int = 2 * 1024 * 1024 * 1024

    @classmethod
    def from_environment(cls, environ: Mapping[str, str] | None = None) -> "RuntimeBudgets":
        values = os.environ if environ is None else environ
        defaults = cls()
        return cls(
            max_concurrency=_positive_int(values.get("MAX_REQUEST_CONCURRENCY"), defaults.max_concurrency),
            max_response_bytes=_positive_int(values.get("MAX_RESPONSE_BYTES"), defaults.max_response_bytes),
            max_tokens_per_task=_positive_int(values.get("MAX_TOKENS_PER_TASK"), defaults.max_tokens_per_task),
            max_task_seconds=_positive_float(values.get("MAX_TASK_SECONDS"), defaults.max_task_seconds),
            max_queue_depth=_positive_int(values.get("MAX_QUEUE_DEPTH"), defaults.max_queue_depth),
            memory_warning_bytes=_positive_int(values.get("MEMORY_WARNING_BYTES"), defaults.memory_warning_bytes),
            disk_warning_free_bytes=_positive_int(values.get("DISK_WARNING_FREE_BYTES"), defaults.disk_warning_free_bytes),
        )


class BudgetExceeded(RuntimeError):
    def __init__(self, budget: str) -> None:
        super().__init__(f"runtime budget exceeded: {budget}")
        self.budget = budget


class BudgetEnforcer:
    def __init__(self, budgets: RuntimeBudgets, logger, *, free_space: Callable[[Path], int] | None = None) -> None:
        self.budgets = budgets
        self.logger = logger
        self.free_space = free_space or (lambda path: shutil.disk_usage(path).free)

    def require(self, *, correlation_id: str, name: str, observed: float, limit: float) -> None:
        if observed <= limit:
            return
        METRICS.increment("budget_events_total", budget=name, outcome="exhausted")
        emit_event(
            self.logger,
            "budget_exhausted",
            EventContext(correlation_id=correlation_id, outcome="policy_failed"),
            budget=name,
            observed=observed,
            limit=limit,
        )
        raise BudgetExceeded(name)

    def check_disk(self, path: Path, *, correlation_id: str) -> None:
        free = self.free_space(path)
        if free < self.budgets.disk_warning_free_bytes:
            self.require(
                correlation_id=correlation_id,
                name="disk_free_bytes",
                observed=self.budgets.disk_warning_free_bytes - free,
                limit=0,
            )

    def check_task(
        self,
        *,
        correlation_id: str,
        tokens: int = 0,
        elapsed_seconds: float = 0,
        response_bytes: int = 0,
        queue_depth: int = 0,
        memory_bytes: int = 0,
    ) -> None:
        for name, observed, limit in (
            ("tokens", tokens, self.budgets.max_tokens_per_task),
            ("task_seconds", elapsed_seconds, self.budgets.max_task_seconds),
            ("response_bytes", response_bytes, self.budgets.max_response_bytes),
            ("queue_depth", queue_depth, self.budgets.max_queue_depth),
            ("memory_bytes", memory_bytes, self.budgets.memory_warning_bytes),
        ):
            self.require(correlation_id=correlation_id, name=name, observed=observed, limit=limit)


def _positive_int(value: str | None, default: int) -> int:
    parsed = default if value is None else int(value)
    if parsed <= 0:
        raise ValueError("runtime budget must be positive")
    return parsed


def _positive_float(value: str | None, default: float) -> float:
    parsed = default if value is None else float(value)
    if parsed <= 0:
        raise ValueError("runtime budget must be positive")
    return parsed
