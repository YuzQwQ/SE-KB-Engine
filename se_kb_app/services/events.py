from __future__ import annotations

from threading import Lock

from se_kb_app.domain import DomainEvent


class InMemoryEventPublisher:
    def __init__(self) -> None:
        self._events: list[DomainEvent] = []
        self._lock = Lock()

    def publish(self, event: DomainEvent) -> None:
        with self._lock:
            self._events.append(event)

    def snapshot(self) -> tuple[DomainEvent, ...]:
        with self._lock:
            return tuple(self._events)

    def close(self) -> None:
        with self._lock:
            self._events.clear()
