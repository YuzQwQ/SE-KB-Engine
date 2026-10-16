from __future__ import annotations

from typing import Any, Protocol

from se_kb_app.domain import RetrievalRequest, RetrievalResult
from se_kb_app.settings import AppSettings


class LegacyRetriever(Protocol):
    def retrieve(self, query: str, top_k: int, intent: Any | None) -> Any: ...


class VectorRetrieverAdapter:
    def __init__(self, retriever: LegacyRetriever) -> None:
        self._retriever = retriever

    def retrieve(self, request: RetrievalRequest) -> RetrievalResult:
        from vectorizer import QueryIntent

        intent = QueryIntent(request.intent) if request.intent else None
        response = self._retriever.retrieve(request.query, request.top_k, intent)
        items = tuple(
            {
                "content": result.text,
                "score": round(result.score, 4),
                "source": result.metadata.get("source"),
                "type": result.metadata.get("type"),
                "collection": result.collection,
                "metadata": result.metadata,
            }
            for result in response.results
        )
        return RetrievalResult(response.query, response.intent.value, items)

    def close(self) -> None:
        closer = getattr(self._retriever, "close", None)
        if callable(closer):
            closer()


def create_vector_retrieval(settings: AppSettings):
    from se_kb_app.factories import _create_vector_store
    from se_kb_app.services.retrieval import RetrievalService

    return RetrievalService(VectorRetrieverAdapter(_create_vector_store(settings)))
