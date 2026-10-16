from __future__ import annotations

import json
from pathlib import Path

import jsonschema
import pytest

from se_kb_app.retrieval.benchmark import BenchmarkConfig, BenchmarkRunner
from se_kb_app.retrieval.engines import BM25Retriever, HashVectorRetriever, HybridRetriever
from se_kb_app.retrieval.experiments import (
    DeterministicReranker,
    PromotionBudgets,
    calibrate_no_answer_threshold,
    chunk_documents,
    evaluate_promotion,
)
from se_kb_app.retrieval.metrics import ndcg_at_k, percentile, recall_at_k, reciprocal_rank
from se_kb_app.retrieval.models import EvaluationDataset

ROOT = Path(__file__).parent.parent
FIXTURE = Path(__file__).parent / "fixtures" / "retrieval"


def dataset() -> EvaluationDataset:
    return EvaluationDataset.load(FIXTURE / "documents.jsonl", FIXTURE / "queries.jsonl")


@pytest.mark.unit
def test_jsonl_rows_follow_reviewable_schemas():
    for name, schema_name in (
        ("documents.jsonl", "retrieval-document-v1.schema.json"),
        ("queries.jsonl", "retrieval-query-v1.schema.json"),
    ):
        schema = json.loads((ROOT / "schemas" / schema_name).read_text(encoding="utf-8"))
        for line in (FIXTURE / name).read_text(encoding="utf-8").splitlines():
            jsonschema.validate(json.loads(line), schema, format_checker=jsonschema.FormatChecker())
    loaded = dataset()
    assert loaded.version == "1.0.0"
    assert {query.split for query in loaded.queries} == {"dev", "holdout"}
    assert any(query.no_answer for query in loaded.queries)
    assert any(query.hard_negatives for query in loaded.queries)


@pytest.mark.unit
def test_ranking_metrics_are_deterministic_and_graded():
    relevance = {"a": 3, "b": 1}
    assert recall_at_k(["x", "a"], relevance, 2) == 0.5
    assert reciprocal_rank(["x", "a"], relevance) == 0.5
    assert ndcg_at_k(["a", "b"], relevance, 2) == pytest.approx(1.0)
    assert percentile([1.0, 2.0, 10.0], 0.95) == pytest.approx(9.2)


@pytest.mark.integration
def test_offline_candidates_share_contract_and_filters_never_expand_results():
    loaded = dataset()
    lexical = BM25Retriever(loaded.documents)
    vector = HashVectorRetriever(loaded.documents)
    hybrid = HybridRetriever(lexical, vector)
    for retriever in (lexical, vector, hybrid, DeterministicReranker(hybrid)):
        unfiltered = retriever.search("DFD process rule", top_k=10)
        filtered = retriever.search("DFD process rule", top_k=10, filters={"kind": "rule"})
        assert {item.id for item in filtered}.issubset({item.id for item in unfiltered})
        assert all(item.document.kind == "rule" for item in filtered)
    with pytest.raises(ValueError, match="unsupported filters"):
        lexical.search("DFD", top_k=5, filters={"invented": True})


@pytest.mark.unit
def test_chunk_experiment_preserves_stable_parent_and_source_relationships():
    loaded = dataset()
    first = chunk_documents(loaded.documents, size=40, overlap=10)
    second = chunk_documents(loaded.documents, size=40, overlap=10)
    assert [(item.id, item.parent_id) for item in first] == [(item.id, item.parent_id) for item in second]
    assert all(item.source for item in first)


@pytest.mark.integration
def test_benchmark_emits_complete_reproducibility_and_all_resource_metrics():
    loaded = dataset()
    report = BenchmarkRunner(ROOT).run(
        loaded,
        HashVectorRetriever(loaded.documents),
        BenchmarkConfig("vector-baseline"),
        index_fingerprint="fixture-vector-v1",
    )
    assert report.status == "complete"
    expected_metrics = {
        "recall_at_k", "mrr", "ndcg_at_k", "no_answer_accuracy", "p50_latency_ms",
        "p95_latency_ms", "peak_memory_bytes", "input_tokens", "estimated_cost",
    }
    assert expected_metrics.issubset(report.metrics)
    assert {"commit", "dirty", "environment", "dependencies", "dataset", "dataset_version", "configuration", "chunker", "embedding", "index", "query_planner", "seed"}.issubset(report.fingerprints)


@pytest.mark.unit
def test_threshold_calibration_and_promotion_gates_reject_quality_regression():
    threshold = calibrate_no_answer_threshold([(0.8, False), (0.6, False), (0.0, True)])
    assert 0.0 < threshold <= 0.6
    baseline = {
        "recall_at_k": 1.0, "mrr": 1.0, "ndcg_at_k": 1.0, "no_answer_accuracy": 1.0,
        "p95_latency_ms": 10.0, "peak_memory_bytes": 1024, "estimated_cost": 0.0,
    }
    candidate = {**baseline, "recall_at_k": 0.8, "p95_latency_ms": 1.0}
    passed, failures = evaluate_promotion(baseline, candidate, PromotionBudgets())
    assert passed is False
    assert "recall_at_k regression exceeds budget" in failures
