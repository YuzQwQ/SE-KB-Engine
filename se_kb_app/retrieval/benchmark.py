from __future__ import annotations

import hashlib
import json
import os
import platform
import subprocess
import sys
import time
import tracemalloc
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Mapping

from .engines import Retriever
from .metrics import aggregate_rankings, percentile
from .models import EvaluationDataset
from se_kb_app.observability import METRICS


@dataclass(frozen=True)
class BenchmarkConfig:
    name: str
    top_k: int = 5
    no_answer_threshold: float = 0.01
    random_seed: int = 20260915
    estimated_cost_per_million_tokens: float = 0.0
    split: str = "dev"
    chunk_size: int = 0
    chunk_overlap: int = 0


@dataclass(frozen=True)
class BenchmarkReport:
    status: str
    candidate: str
    metrics: Mapping[str, float | int]
    fingerprints: Mapping[str, Any]
    queries: tuple[Mapping[str, Any], ...]

    def to_dict(self) -> dict[str, Any]:
        return {
            "status": self.status,
            "candidate": self.candidate,
            "metrics": dict(self.metrics),
            "fingerprints": dict(self.fingerprints),
            "queries": [dict(item) for item in self.queries],
        }


class BenchmarkRunner:
    def __init__(self, project_root: Path) -> None:
        self.project_root = project_root.resolve()

    def run(
        self,
        dataset: EvaluationDataset,
        retriever: Retriever,
        config: BenchmarkConfig,
        *,
        index_fingerprint: str,
    ) -> BenchmarkReport:
        rows: list[dict[str, Any]] = []
        rankings = []
        latencies: list[float] = []
        token_count = 0
        tracemalloc.start()
        try:
            for query in dataset.queries:
                if query.split != config.split:
                    continue
                started = time.perf_counter()
                hits = retriever.search(query.text, top_k=config.top_k)
                elapsed_ms = (time.perf_counter() - started) * 1000
                latencies.append(elapsed_ms)
                token_count += len(query.text.split())
                predicted_empty = not hits or hits[0].score < config.no_answer_threshold
                ranked = (
                    list(dict.fromkeys(hit.document.parent_id or hit.id for hit in hits))
                    if not predicted_empty
                    else []
                )
                rankings.append((ranked, query.relevance, query.no_answer, predicted_empty))
                rows.append(
                    {
                        "query_id": query.id,
                        "ranked_ids": ranked,
                        "top_score": hits[0].score if hits else 0.0,
                        "expected_no_answer": query.no_answer,
                        "predicted_no_answer": predicted_empty,
                        "latency_ms": elapsed_ms,
                    }
                )
            _, peak_memory = tracemalloc.get_traced_memory()
        finally:
            tracemalloc.stop()
        ranking = aggregate_rankings(rankings, k=config.top_k)
        fingerprints = self._fingerprints(dataset, config, index_fingerprint)
        required = ("commit", "dependencies", "dataset", "configuration", "index", "seed")
        complete = all(fingerprints.get(key) not in (None, "", "unknown") for key in required)
        metrics: dict[str, float | int] = {
            **asdict(ranking),
            "p50_latency_ms": percentile(latencies, 0.50),
            "p95_latency_ms": percentile(latencies, 0.95),
            "peak_memory_bytes": peak_memory,
            "input_tokens": token_count,
            "estimated_cost": token_count / 1_000_000 * config.estimated_cost_per_million_tokens,
        }
        METRICS.observe("retrieval_quality", ranking.recall_at_k, metric="recall_at_k", split=config.split)
        METRICS.observe("retrieval_quality", ranking.ndcg_at_k, metric="ndcg_at_k", split=config.split)
        METRICS.observe("retrieval_latency_ms", float(metrics["p95_latency_ms"]), candidate=config.name)
        METRICS.increment(
            "retrieval_no_answer_total",
            value=sum(1 for row in rows if row["predicted_no_answer"]),
            candidate=config.name,
        )
        return BenchmarkReport("complete" if complete else "incomplete", config.name, metrics, fingerprints, tuple(rows))

    def _fingerprints(
        self, dataset: EvaluationDataset, config: BenchmarkConfig, index_fingerprint: str
    ) -> dict[str, Any]:
        commit = _git(self.project_root, "rev-parse", "HEAD")
        dirty = bool(_git(self.project_root, "status", "--porcelain"))
        lock = self.project_root / "uv.lock"
        dependencies = hashlib.sha256(lock.read_bytes()).hexdigest() if lock.is_file() else "unknown"
        configuration = hashlib.sha256(
            json.dumps(asdict(config), sort_keys=True, separators=(",", ":")).encode()
        ).hexdigest()
        return {
            "commit": commit,
            "dirty": dirty,
            "environment": {
                "python": sys.version.split()[0],
                "platform": platform.platform(),
                "implementation": platform.python_implementation(),
                "offline": os.getenv("SE_KB_OFFLINE_BENCHMARK", "1") == "1",
            },
            "dependencies": dependencies,
            "dataset": dataset.fingerprint,
            "dataset_version": dataset.version,
            "configuration": configuration,
            "chunker": f"document-v1:size={config.chunk_size}:overlap={config.chunk_overlap}",
            "embedding": "hash-vector-v1",
            "index": index_fingerprint,
            "query_planner": "direct-v1",
            "seed": config.random_seed,
        }


def _git(root: Path, *arguments: str) -> str:
    try:
        result = subprocess.run(
            ["git", *arguments], cwd=root, text=True, capture_output=True, check=True, timeout=5
        )
        return result.stdout.strip() or "unknown"
    except (OSError, subprocess.SubprocessError):
        return "unknown"
