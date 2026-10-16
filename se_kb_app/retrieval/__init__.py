"""Offline retrieval evaluation and safe index lifecycle primitives."""

from .benchmark import BenchmarkConfig, BenchmarkReport, BenchmarkRunner
from .engines import BM25Retriever, HashVectorRetriever, HybridRetriever, RetrievalHit
from .indexing import BuildMode, IndexCompatibilityError, IndexManager, IndexManifest
from .models import EvaluationDataset, EvaluationDocument, EvaluationQuery

__all__ = [
    "BM25Retriever",
    "BenchmarkConfig",
    "BenchmarkReport",
    "BenchmarkRunner",
    "BuildMode",
    "EvaluationDataset",
    "EvaluationDocument",
    "EvaluationQuery",
    "HashVectorRetriever",
    "HybridRetriever",
    "IndexCompatibilityError",
    "IndexManager",
    "IndexManifest",
    "RetrievalHit",
]
