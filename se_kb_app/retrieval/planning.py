from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor, TimeoutError
from dataclasses import dataclass
from time import monotonic
from typing import Callable, Sequence


@dataclass(frozen=True)
class QueryBounds:
    max_top_k: int = 20
    max_subqueries: int = 4
    max_concurrency: int = 2
    timeout_seconds: float = 2.0
    max_input_tokens: int = 512
    max_rerank_items: int = 20

    def clamp_top_k(self, requested: int) -> int:
        if requested <= 0:
            raise ValueError("top_k must be positive")
        return min(requested, self.max_top_k)


@dataclass(frozen=True)
class PlanExecution:
    subqueries: tuple[str, ...]
    results: tuple[str, ...]
    fallback_used: bool
    elapsed_seconds: float


class BoundedQueryPlanner:
    def __init__(self, bounds: QueryBounds | None = None) -> None:
        self.bounds = bounds or QueryBounds()

    def execute(
        self,
        query: str,
        subqueries: Sequence[str],
        search: Callable[[str, int], Sequence[str]],
        *,
        top_k: int,
    ) -> PlanExecution:
        started = monotonic()
        bounded_top_k = self.bounds.clamp_top_k(top_k)
        if len(query.split()) > self.bounds.max_input_tokens:
            raise ValueError("query exceeds the configured token budget")
        planned = tuple(item.strip() for item in subqueries if item.strip())[: self.bounds.max_subqueries]
        planned = planned or (query,)
        collected: list[str] = []
        fallback = False
        try:
            with ThreadPoolExecutor(max_workers=self.bounds.max_concurrency) as executor:
                futures = [executor.submit(search, item, bounded_top_k) for item in planned]
                for future in futures:
                    remaining = self.bounds.timeout_seconds - (monotonic() - started)
                    if remaining <= 0:
                        raise TimeoutError
                    collected.extend(future.result(timeout=remaining))
        except (TimeoutError, OSError, RuntimeError):
            fallback = True
            collected = list(search(query, bounded_top_k))
        unique = tuple(dict.fromkeys(collected))[:bounded_top_k]
        return PlanExecution(planned, unique, fallback, monotonic() - started)
