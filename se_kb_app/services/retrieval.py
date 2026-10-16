from __future__ import annotations

from collections.abc import Callable
from datetime import datetime
from types import MappingProxyType
from typing import Mapping

from se_kb_app.domain import Cancellation, DomainEvent, EventPublisher, RetrievalRequest, RetrievalResult, Retriever
from se_kb_app.errors import ApplicationError, ErrorKind, wrap_error


class RetrievalService:
    def __init__(
        self,
        retriever: Retriever,
        *,
        events: EventPublisher | None = None,
        clock: Callable[[], datetime] | None = None,
        cancellation: Cancellation | None = None,
    ) -> None:
        self.retriever = retriever
        self.events = events
        self.clock = clock or datetime.now
        self.cancellation = cancellation

    def retrieve(self, request: RetrievalRequest) -> RetrievalResult:
        try:
            if self.cancellation is not None:
                self.cancellation.checkpoint()
            result = self.retriever.retrieve(request)
            if self.cancellation is not None:
                self.cancellation.checkpoint()
        except ApplicationError:
            raise
        except Exception as error:
            raise wrap_error(
                ErrorKind.RETRIEVAL,
                "retrieval_failed",
                "Knowledge retrieval could not be completed.",
                retryable=False,
                cause=error,
            ) from error
        if self.events is not None:
            if self.cancellation is not None:
                self.cancellation.checkpoint()
            self.events.publish(
                DomainEvent(
                    name="retrieval.completed",
                    occurred_at=self.clock(),
                    payload={"query": request.query, "items": len(result.items)},
                )
            )
        return result

    def close(self) -> None:
        self.retriever.close()


class DfdContextService:
    """Builds stable DFD context sections through the shared retrieval boundary."""

    def __init__(self, retrieval: RetrievalService) -> None:
        self.retrieval = retrieval

    def build(self, query: str, *, top_k: int = 3) -> Mapping[str, RetrievalResult]:
        sections = {
            name: self.retrieval.retrieve(RetrievalRequest(query, top_k, intent))
            for name, intent in (
                ("concepts", "concept"),
                ("rules", "rule"),
                ("examples", "example"),
            )
        }
        return MappingProxyType(sections)
