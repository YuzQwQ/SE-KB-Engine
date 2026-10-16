from __future__ import annotations

import math
from dataclasses import dataclass
from statistics import mean
from typing import Iterable, Mapping, Sequence


@dataclass(frozen=True)
class RankingMetrics:
    recall_at_k: float
    mrr: float
    ndcg_at_k: float
    no_answer_accuracy: float


def recall_at_k(ranked: Sequence[str], relevance: Mapping[str, int], k: int) -> float:
    relevant = {item for item, grade in relevance.items() if grade > 0}
    if not relevant:
        return 1.0 if not ranked[:k] else 0.0
    return len(relevant.intersection(ranked[:k])) / len(relevant)


def reciprocal_rank(ranked: Sequence[str], relevance: Mapping[str, int]) -> float:
    for rank, item in enumerate(ranked, 1):
        if relevance.get(item, 0) > 0:
            return 1.0 / rank
    return 0.0


def ndcg_at_k(ranked: Sequence[str], relevance: Mapping[str, int], k: int) -> float:
    def dcg(grades: Sequence[int]) -> float:
        return sum((2**grade - 1) / math.log2(position + 2) for position, grade in enumerate(grades))

    actual = dcg([relevance.get(item, 0) for item in ranked[:k]])
    ideal = dcg(sorted(relevance.values(), reverse=True)[:k])
    return actual / ideal if ideal else (1.0 if not ranked[:k] else 0.0)


def aggregate_rankings(
    rankings: Iterable[tuple[Sequence[str], Mapping[str, int], bool, bool]], *, k: int
) -> RankingMetrics:
    rows = list(rankings)
    if not rows:
        raise ValueError("at least one ranking is required")
    answerable = [(ranked, relevance) for ranked, relevance, expected_empty, _ in rows if not expected_empty]
    recalls = [recall_at_k(ranked, relevance, k) for ranked, relevance in answerable]
    reciprocal = [reciprocal_rank(ranked, relevance) for ranked, relevance in answerable]
    ndcgs = [ndcg_at_k(ranked, relevance, k) for ranked, relevance in answerable]
    no_answer = [predicted == expected for _, _, expected, predicted in rows]
    return RankingMetrics(
        mean(recalls) if recalls else 1.0,
        mean(reciprocal) if reciprocal else 1.0,
        mean(ndcgs) if ndcgs else 1.0,
        mean(no_answer),
    )


def percentile(values: Sequence[float], quantile: float) -> float:
    if not values:
        return 0.0
    ordered = sorted(values)
    position = (len(ordered) - 1) * quantile
    lower = math.floor(position)
    upper = math.ceil(position)
    if lower == upper:
        return ordered[lower]
    return ordered[lower] + (ordered[upper] - ordered[lower]) * (position - lower)
