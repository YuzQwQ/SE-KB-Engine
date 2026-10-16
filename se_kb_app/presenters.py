from __future__ import annotations

from typing import Any

from se_kb_app.domain import RetrievalResult


def retrieval_payload(result: RetrievalResult) -> dict[str, Any]:
    return {
        "query": result.query,
        "intent": result.intent,
        "total_found": len(result.items),
        "results": [dict(item) for item in result.items],
    }
