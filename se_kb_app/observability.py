from __future__ import annotations

import contextvars
import json
import logging
import re
import sys
import threading
import time
from collections import Counter, defaultdict
from contextlib import contextmanager
from dataclasses import asdict, dataclass
from typing import Any, Iterator, Mapping

MAX_FIELD_CHARS = 512
MAX_EVENT_FIELDS = 32
MAX_LABEL_VALUES = 64
SENSITIVE_KEYS = {
    "authorization", "cookie", "set-cookie", "api_key", "apikey", "password", "secret",
    "token", "access_token", "refresh_token", "content", "body", "prompt", "response",
}
_SECRET_PATTERNS = (
    re.compile(r"(?i)\bBearer\s+[^\s,;]+"),
    re.compile(r"(?i)(api[_-]?key|password|secret|token)\s*[=:]\s*[^\s,;]+"),
    re.compile(r"\b(?:sk|pk)-[A-Za-z0-9_-]{8,}\b"),
)
_context: contextvars.ContextVar[dict[str, object]] = contextvars.ContextVar(
    "se_kb_telemetry_context", default={}
)
_configured = False
_configure_lock = threading.Lock()


@dataclass(frozen=True)
class EventContext:
    correlation_id: str | None = None
    job_id: str | None = None
    document_id: str | None = None
    stage: str | None = None
    attempt: int | None = None
    outcome: str | None = None
    duration_ms: float | None = None


def redact_text(value: object, secrets: tuple[str, ...] = ()) -> str:
    text = str(value)
    for pattern in _SECRET_PATTERNS:
        text = pattern.sub("[REDACTED]", text)
    for secret in secrets:
        if secret:
            text = text.replace(secret, "[REDACTED]")
    return text[:MAX_FIELD_CHARS] + ("…" if len(text) > MAX_FIELD_CHARS else "")


def safe_fields(values: Mapping[str, object], *, secrets: tuple[str, ...] = ()) -> dict[str, object]:
    output: dict[str, object] = {}
    for key, value in sorted(values.items())[:MAX_EVENT_FIELDS]:
        normalized = key.lower().replace("_", "-")
        if normalized in {item.replace("_", "-") for item in SENSITIVE_KEYS}:
            output[key] = "[REDACTED]"
        elif isinstance(value, (bool, int, float)) or value is None:
            output[key] = value
        elif isinstance(value, Mapping):
            output[key] = safe_fields(
                {str(child_key): child_value for child_key, child_value in value.items()},
                secrets=secrets,
            )
        elif isinstance(value, (list, tuple, set)):
            output[key] = [redact_text(item, secrets) for item in list(value)[:20]]
        else:
            output[key] = redact_text(value, secrets)
    return output


@contextmanager
def event_context(**fields: object) -> Iterator[None]:
    token = _context.set({**_context.get(), **safe_fields(fields)})
    try:
        yield
    finally:
        _context.reset(token)


def push_event_context(**fields: object) -> contextvars.Token[dict[str, object]]:
    return _context.set({**_context.get(), **safe_fields(fields)})


def reset_event_context(token: contextvars.Token[dict[str, object]]) -> None:
    _context.reset(token)


class StructuredFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        reserved = set(logging.makeLogRecord({}).__dict__) | {"message", "asctime"}
        extras = {key: value for key, value in record.__dict__.items() if key not in reserved}
        payload = {
            "timestamp": self.formatTime(record, "%Y-%m-%dT%H:%M:%S"),
            "level": record.levelname.lower(),
            "logger": record.name,
            "event": redact_text(record.getMessage()),
            **safe_fields(_context.get()),
            **safe_fields(extras),
        }
        if record.exc_info:
            payload["error_type"] = record.exc_info[0].__name__ if record.exc_info[0] else "Exception"
        return json.dumps(payload, ensure_ascii=False, separators=(",", ":"))


def configure_logging(*, level: int = logging.INFO, stream: Any = None) -> bool:
    global _configured
    with _configure_lock:
        if _configured:
            return False
        handler = logging.StreamHandler(stream or sys.stderr)
        handler.setFormatter(StructuredFormatter())
        root = logging.getLogger()
        if not root.handlers:
            root.addHandler(handler)
        else:
            for existing in root.handlers:
                existing.setFormatter(StructuredFormatter())
        root.setLevel(level)
        _configured = True
        return True


class MetricsRegistry:
    """Small neutral metrics registry with bounded label cardinality."""

    def __init__(self, *, maximum_label_values: int = MAX_LABEL_VALUES) -> None:
        self.maximum_label_values = maximum_label_values
        self._counters: Counter[tuple[str, tuple[tuple[str, str], ...]]] = Counter()
        self._gauges: dict[tuple[str, tuple[tuple[str, str], ...]], float] = {}
        self._durations: defaultdict[tuple[str, tuple[tuple[str, str], ...]], list[float]] = defaultdict(list)
        self._label_values: defaultdict[tuple[str, str], set[str]] = defaultdict(set)
        self._lock = threading.Lock()

    def increment(self, name: str, value: int = 1, **labels: str) -> None:
        key = (name, self._labels(name, labels))
        with self._lock:
            self._counters[key] += value

    def gauge(self, name: str, value: float, **labels: str) -> None:
        key = (name, self._labels(name, labels))
        with self._lock:
            self._gauges[key] = value

    def observe(self, name: str, value: float, **labels: str) -> None:
        key = (name, self._labels(name, labels))
        with self._lock:
            samples = self._durations[key]
            samples.append(value)
            if len(samples) > 1024:
                del samples[: len(samples) - 1024]

    @contextmanager
    def timer(self, name: str, **labels: str) -> Iterator[None]:
        started = time.perf_counter()
        try:
            yield
        finally:
            self.observe(name, (time.perf_counter() - started) * 1000, **labels)

    def snapshot(self) -> dict[str, object]:
        with self._lock:
            return {
                "counters": {_metric_key(key): value for key, value in self._counters.items()},
                "gauges": {_metric_key(key): value for key, value in self._gauges.items()},
                "histograms": {
                    _metric_key(key): {"count": len(values), "sum": sum(values), "max": max(values)}
                    for key, values in self._durations.items()
                    if values
                },
            }

    def _labels(self, metric: str, labels: Mapping[str, str]) -> tuple[tuple[str, str], ...]:
        if len(labels) > 6:
            raise ValueError("metrics support at most six low-cardinality labels")
        normalized = []
        with self._lock:
            for name, value in sorted(labels.items()):
                if name.lower() in {"url", "title", "document_id", "job_id", "correlation_id"}:
                    raise ValueError(f"high-cardinality metric label is forbidden: {name}")
                safe = redact_text(value)
                observed = self._label_values[(metric, name)]
                if safe not in observed and len(observed) >= self.maximum_label_values:
                    safe = "__overflow__"
                observed.add(safe)
                normalized.append((name, safe))
        return tuple(normalized)


METRICS = MetricsRegistry()


def emit_event(logger: logging.Logger, event: str, context: EventContext, **fields: object) -> None:
    contextual = {key: value for key, value in asdict(context).items() if value is not None}
    logger.info(event, extra={**contextual, **safe_fields(fields)})


def _metric_key(key: tuple[str, tuple[tuple[str, str], ...]]) -> str:
    name, labels = key
    return name + ("{" + ",".join(f"{label}={value}" for label, value in labels) + "}" if labels else "")
