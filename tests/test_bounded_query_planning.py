from __future__ import annotations

import time

import pytest

from se_kb_app.retrieval.planning import BoundedQueryPlanner, QueryBounds


@pytest.mark.unit
def test_planner_clamps_top_k_subqueries_and_deduplicates():
    planner = BoundedQueryPlanner(QueryBounds(max_top_k=2, max_subqueries=2, max_concurrency=1))
    calls = []

    def search(query: str, top_k: int):
        calls.append((query, top_k))
        return [query, "shared"]

    result = planner.execute("complex query", ["one", "two", "three"], search, top_k=99)
    assert result.subqueries == ("one", "two")
    assert all(top_k == 2 for _, top_k in calls)
    assert len(result.results) <= 2


@pytest.mark.unit
def test_planner_falls_back_on_bounded_timeout():
    planner = BoundedQueryPlanner(QueryBounds(timeout_seconds=0.01, max_concurrency=1))

    def search(query: str, top_k: int):
        if query == "slow":
            time.sleep(0.2)
        return [query]

    result = planner.execute("original", ["slow"], search, top_k=3)
    assert result.fallback_used is True
    assert result.results == ("original",)


@pytest.mark.unit
def test_planner_rejects_non_positive_top_k():
    with pytest.raises(ValueError, match="positive"):
        BoundedQueryPlanner().execute("query", [], lambda query, top_k: [], top_k=0)
