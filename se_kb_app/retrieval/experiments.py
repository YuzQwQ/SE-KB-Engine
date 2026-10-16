from __future__ import annotations

import hashlib
from dataclasses import dataclass
from typing import Mapping, Sequence

from .engines import RetrievalHit, Retriever, tokenize
from .models import EvaluationDocument


def chunk_documents(
    documents: Sequence[EvaluationDocument], *, size: int, overlap: int
) -> tuple[EvaluationDocument, ...]:
    if size <= 0 or overlap < 0 or overlap >= size:
        raise ValueError("chunk size must be positive and overlap smaller than size")
    chunks: list[EvaluationDocument] = []
    for document in documents:
        if len(document.text) <= size:
            chunks.append(document)
            continue
        start = 0
        while start < len(document.text):
            text = document.text[start : start + size]
            suffix = hashlib.sha256(f"{document.id}:{start}:{text}".encode()).hexdigest()[:12]
            chunks.append(
                EvaluationDocument(
                    id=f"{document.id}--{suffix}",
                    text=text,
                    source=document.source,
                    kind=document.kind,
                    date=document.date,
                    quality=document.quality,
                    parent_id=document.parent_id or document.id,
                    metadata={**dict(document.metadata), "offset": start},
                )
            )
            if start + size >= len(document.text):
                break
            start += size - overlap
    return tuple(chunks)


class DeterministicReranker:
    def __init__(self, base: Retriever, *, candidate_width: int = 20) -> None:
        self.base = base
        self.candidate_width = candidate_width

    def search(self, query: str, *, top_k: int, filters=None) -> list[RetrievalHit]:
        query_tokens = set(tokenize(query))
        candidates = self.base.search(query, top_k=max(top_k, self.candidate_width), filters=filters)
        reranked = []
        for hit in candidates:
            overlap = len(query_tokens.intersection(tokenize(hit.document.text))) / max(1, len(query_tokens))
            # Quality may break a ranking tie, but it must never create confidence when
            # neither retrieval nor query evidence exists.
            score = hit.score * (0.80 + hit.document.quality * 0.10) + overlap * 0.10
            reranked.append(RetrievalHit(hit.id, score, hit.document, "bounded deterministic rerank"))
        return sorted(reranked, key=lambda item: (-item.score, item.id))[:top_k]


def calibrate_no_answer_threshold(top_scores: Sequence[tuple[float, bool]]) -> float:
    candidates = sorted({0.0, *(score for score, _ in top_scores)})
    best_threshold = 0.0
    best_accuracy = -1.0
    for threshold in candidates:
        correct = sum((score < threshold) == expected_empty for score, expected_empty in top_scores)
        accuracy = correct / len(top_scores) if top_scores else 1.0
        if accuracy > best_accuracy:
            best_accuracy = accuracy
            best_threshold = threshold
    return best_threshold


@dataclass(frozen=True)
class PromotionBudgets:
    max_recall_regression: float = 0.0
    max_mrr_regression: float = 0.0
    max_ndcg_regression: float = 0.0
    min_no_answer_accuracy: float = 0.8
    max_p95_latency_ms: float = 50.0
    max_peak_memory_bytes: int = 32 * 1024 * 1024
    max_estimated_cost: float = 0.0


def evaluate_promotion(
    baseline: Mapping[str, float | int],
    candidate: Mapping[str, float | int],
    budgets: PromotionBudgets,
) -> tuple[bool, tuple[str, ...]]:
    failures: list[str] = []
    for metric, allowance in (
        ("recall_at_k", budgets.max_recall_regression),
        ("mrr", budgets.max_mrr_regression),
        ("ndcg_at_k", budgets.max_ndcg_regression),
    ):
        if float(candidate[metric]) < float(baseline[metric]) - allowance:
            failures.append(f"{metric} regression exceeds budget")
    for metric, limit in (
        ("no_answer_accuracy", budgets.min_no_answer_accuracy),
    ):
        if float(candidate[metric]) < limit:
            failures.append(f"{metric} is below minimum")
    for metric, limit in (
        ("p95_latency_ms", budgets.max_p95_latency_ms),
        ("peak_memory_bytes", budgets.max_peak_memory_bytes),
        ("estimated_cost", budgets.max_estimated_cost),
    ):
        if float(candidate[metric]) > limit:
            failures.append(f"{metric} exceeds budget")
    return not failures, tuple(failures)
