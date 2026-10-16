from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from types import MappingProxyType
from typing import Any, Mapping


class JobStatus(str, Enum):
    QUEUED = "queued"
    RUNNING = "running"
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    CANCELLED = "cancelled"
    INTERRUPTED = "interrupted"

    @property
    def terminal(self) -> bool:
        return self in {self.SUCCEEDED, self.FAILED, self.CANCELLED, self.INTERRUPTED}


ALLOWED_TRANSITIONS = {
    JobStatus.QUEUED: frozenset({JobStatus.RUNNING, JobStatus.CANCELLED, JobStatus.INTERRUPTED}),
    JobStatus.RUNNING: frozenset(
        {JobStatus.SUCCEEDED, JobStatus.FAILED, JobStatus.CANCELLED, JobStatus.INTERRUPTED}
    ),
    JobStatus.SUCCEEDED: frozenset(),
    JobStatus.FAILED: frozenset(),
    JobStatus.CANCELLED: frozenset(),
    JobStatus.INTERRUPTED: frozenset(),
}


@dataclass(frozen=True)
class JobSubmission:
    operation: str
    parameters: Mapping[str, Any]
    submitted_at: datetime

    def __post_init__(self) -> None:
        object.__setattr__(self, "parameters", MappingProxyType(dict(self.parameters)))


@dataclass(frozen=True)
class JobProgress:
    completed: int = 0
    total: int = 100
    message: str = ""

    def __post_init__(self) -> None:
        if self.total < 1 or not 0 <= self.completed <= self.total:
            raise ValueError("job progress is outside its bounds")


@dataclass(frozen=True)
class JobResultReference:
    identifier: str
    location: str | None = None


@dataclass(frozen=True)
class JobEvent:
    sequence: int
    occurred_at: datetime
    kind: str
    message: str
    metadata: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        object.__setattr__(self, "metadata", MappingProxyType(dict(self.metadata)))


@dataclass(frozen=True)
class JobSnapshot:
    identifier: str
    submission: JobSubmission
    status: JobStatus
    progress: JobProgress
    updated_at: datetime
    result: JobResultReference | None = None
    error_code: str | None = None
