from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Mapping

from se_kb_app.domain import FetchedDocument


class FetchState(str, Enum):
    VALIDATING = "validating"
    STATIC = "static"
    CLASSIFYING = "classifying"
    BACKOFF = "backoff"
    RENDERED = "rendered"
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    CANCELLED = "cancelled"


class AttemptMode(str, Enum):
    STATIC = "static"
    RENDERED = "rendered"


class ContentClassification(str, Enum):
    ACCEPTABLE = "acceptable"
    CHALLENGE = "challenge"
    NO_CONTENT = "no_content"
    UNSUPPORTED = "unsupported"


class OutcomeKind(str, Enum):
    SUCCESS = "success"
    CHALLENGE = "challenge"
    NO_CONTENT = "no_content"
    POLICY_FAILURE = "policy"
    TRANSIENT_FAILURE = "transient"
    PERMANENT_FAILURE = "permanent"
    CANCELLED = "cancelled"


@dataclass(frozen=True)
class FetchPolicy:
    maximum_static_attempts: int = 3
    allow_rendered_fallback: bool = True
    minimum_content_chars: int = 20
    connect_timeout_seconds: float = 5.0
    read_timeout_seconds: float = 20.0
    total_timeout_seconds: float = 45.0
    maximum_body_bytes: int = 4 * 1024 * 1024

    def __post_init__(self) -> None:
        if not 1 <= self.maximum_static_attempts <= 10:
            raise ValueError("maximum_static_attempts must be between 1 and 10")
        if self.minimum_content_chars < 0 or self.maximum_body_bytes < 1:
            raise ValueError("content bounds must be non-negative")
        if min(self.connect_timeout_seconds, self.read_timeout_seconds, self.total_timeout_seconds) <= 0:
            raise ValueError("timeouts must be positive")


@dataclass(frozen=True)
class FetchAttempt:
    number: int
    mode: AttemptMode
    start_seconds: float
    elapsed_seconds: float
    state: FetchState
    reason: str
    public_code: str | None = None
    retryable: bool = False


@dataclass(frozen=True)
class FetchTransition:
    source: FetchState
    target: FetchState
    reason: str


@dataclass(frozen=True)
class FetchOutcome:
    kind: OutcomeKind
    final_url: str
    elapsed_seconds: float
    attempts: tuple[FetchAttempt, ...]
    transitions: tuple[FetchTransition, ...]
    document: FetchedDocument | None = None
    status_code: int | None = None
    media_type: str | None = None
    metadata: Mapping[str, str] | None = None
