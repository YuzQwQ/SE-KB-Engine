from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from se_kb_app.retrieval.benchmark import BenchmarkConfig, BenchmarkRunner
from se_kb_app.retrieval.config import DEFAULT_RETRIEVAL_CONFIG
from se_kb_app.retrieval.engines import BM25Retriever, HashVectorRetriever, HybridRetriever, Retriever
from se_kb_app.retrieval.experiments import DeterministicReranker, chunk_documents
from se_kb_app.retrieval.models import EvaluationDataset


def main() -> int:
    parser = argparse.ArgumentParser(description="Deterministic offline retrieval benchmark")
    parser.add_argument("--documents", type=Path, default=Path("tests/fixtures/retrieval/documents.jsonl"))
    parser.add_argument("--queries", type=Path, default=Path("tests/fixtures/retrieval/queries.jsonl"))
    parser.add_argument(
        "--candidate",
        choices=("vector", "lexical", "hybrid", "hybrid-rerank"),
        default=DEFAULT_RETRIEVAL_CONFIG.default_candidate,
    )
    parser.add_argument("--split", choices=("dev", "holdout"), default="dev")
    parser.add_argument("--top-k", type=int, default=5)
    parser.add_argument("--no-answer-threshold", type=float, default=0.01)
    parser.add_argument("--chunk-size", type=int, default=0)
    parser.add_argument("--chunk-overlap", type=int, default=0)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--quiet", action="store_true")
    args = parser.parse_args()
    dataset = EvaluationDataset.load(args.documents, args.queries)
    indexed_documents = (
        chunk_documents(dataset.documents, size=args.chunk_size, overlap=args.chunk_overlap)
        if args.chunk_size
        else dataset.documents
    )
    lexical = BM25Retriever(indexed_documents)
    vector = HashVectorRetriever(indexed_documents)
    candidates: dict[str, Retriever] = {
        "vector": vector,
        "lexical": lexical,
        "hybrid": HybridRetriever(lexical, vector),
        "hybrid-rerank": DeterministicReranker(HybridRetriever(lexical, vector)),
    }
    report = BenchmarkRunner(PROJECT_ROOT).run(
        dataset,
        candidates[args.candidate],
        BenchmarkConfig(
            name=args.candidate,
            top_k=args.top_k,
            no_answer_threshold=args.no_answer_threshold,
            split=args.split,
            chunk_size=args.chunk_size,
            chunk_overlap=args.chunk_overlap,
        ),
        index_fingerprint=f"fixture-{args.candidate}-size-{args.chunk_size}-overlap-{args.chunk_overlap}-v1",
    )
    payload = json.dumps(report.to_dict(), ensure_ascii=False, indent=2)
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(payload + "\n", encoding="utf-8")
    if args.quiet:
        print(
            f"{report.candidate}: recall@{args.top_k}={report.metrics['recall_at_k']:.3f}; "
            f"mrr={report.metrics['mrr']:.3f}; ndcg={report.metrics['ndcg_at_k']:.3f}; "
            f"no-answer={report.metrics['no_answer_accuracy']:.3f}"
        )
    else:
        print(payload)
    return 0 if report.status == "complete" else 2


if __name__ == "__main__":
    raise SystemExit(main())
