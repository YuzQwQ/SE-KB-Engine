from __future__ import annotations

import hashlib
import math
import re
from collections import Counter, defaultdict
from dataclasses import dataclass
from typing import Iterable, Mapping, Protocol, Sequence

from .models import EvaluationDocument

_WORD = re.compile(r"[a-zA-Z0-9_]+|[\u4e00-\u9fff]+")
_STOPWORDS = {"a", "an", "and", "in", "is", "it", "of", "the", "to", "what", "的", "了", "和", "是", "中"}


@dataclass(frozen=True)
class RetrievalHit:
    id: str
    score: float
    document: EvaluationDocument
    explanation: str


class Retriever(Protocol):
    def search(
        self, query: str, *, top_k: int, filters: Mapping[str, object] | None = None
    ) -> list[RetrievalHit]: ...


def tokenize(text: str) -> tuple[str, ...]:
    tokens: list[str] = []
    for match in _WORD.findall(text.lower()):
        if "\u4e00" <= match[0] <= "\u9fff":
            tokens.extend(
                match[index : index + 2]
                for index in range(len(match) - 1)
                if match[index : index + 2] not in _STOPWORDS
            )
        elif match not in _STOPWORDS:
            tokens.append(match)
    return tuple(tokens)


def apply_filters(
    documents: Iterable[EvaluationDocument], filters: Mapping[str, object] | None
) -> list[EvaluationDocument]:
    if not filters:
        return list(documents)
    supported = {"kind", "source", "date_from", "date_to", "min_quality"}
    unknown = set(filters).difference(supported)
    if unknown:
        raise ValueError(f"unsupported filters: {', '.join(sorted(unknown))}")
    minimum_quality = filters.get("min_quality")
    if minimum_quality is not None and not isinstance(minimum_quality, (int, float)):
        raise ValueError("min_quality must be numeric")
    result = []
    for document in documents:
        if filters.get("kind") is not None and document.kind != filters["kind"]:
            continue
        if filters.get("source") is not None and document.source != filters["source"]:
            continue
        if filters.get("date_from") is not None and document.date < str(filters["date_from"]):
            continue
        if filters.get("date_to") is not None and document.date > str(filters["date_to"]):
            continue
        if minimum_quality is not None and document.quality < minimum_quality:
            continue
        result.append(document)
    return result


class BM25Retriever:
    def __init__(self, documents: Sequence[EvaluationDocument], *, k1: float = 1.2, b: float = 0.75):
        self.documents = tuple(documents)
        self.k1 = k1
        self.b = b
        self.tokens = {document.id: Counter(tokenize(document.text)) for document in documents}
        self.average_length = (
            sum(sum(counts.values()) for counts in self.tokens.values()) / len(documents)
            if documents
            else 1.0
        )
        self.document_frequency: Counter[str] = Counter()
        for counts in self.tokens.values():
            self.document_frequency.update(counts.keys())

    def search(self, query: str, *, top_k: int, filters=None) -> list[RetrievalHit]:
        candidates = apply_filters(self.documents, filters)
        query_tokens = Counter(tokenize(query))
        scored: list[RetrievalHit] = []
        total = len(self.documents)
        for document in candidates:
            counts = self.tokens[document.id]
            length = sum(counts.values())
            score = 0.0
            for token, query_frequency in query_tokens.items():
                frequency = counts[token]
                if not frequency:
                    continue
                document_frequency = self.document_frequency[token]
                inverse = math.log(1 + (total - document_frequency + 0.5) / (document_frequency + 0.5))
                denominator = frequency + self.k1 * (1 - self.b + self.b * length / self.average_length)
                score += query_frequency * inverse * frequency * (self.k1 + 1) / denominator
            if score > 0:
                scored.append(RetrievalHit(document.id, score, document, "bm25 lexical match"))
        return sorted(scored, key=lambda item: (-item.score, item.id))[:top_k]


class HashVectorRetriever:
    def __init__(self, documents: Sequence[EvaluationDocument], *, dimension: int = 256):
        self.documents = tuple(documents)
        self.dimension = dimension
        self.vectors = {document.id: self._embed(document.text) for document in documents}

    def _embed(self, text: str) -> tuple[float, ...]:
        vector = [0.0] * self.dimension
        for token in tokenize(text):
            bucket = int.from_bytes(hashlib.sha256(token.encode()).digest()[:8], "big") % self.dimension
            vector[bucket] += 1.0
        norm = math.sqrt(sum(value * value for value in vector)) or 1.0
        return tuple(value / norm for value in vector)

    def search(self, query: str, *, top_k: int, filters=None) -> list[RetrievalHit]:
        query_vector = self._embed(query)
        scored = []
        for document in apply_filters(self.documents, filters):
            score = sum(left * right for left, right in zip(query_vector, self.vectors[document.id]))
            if score > 0:
                scored.append(RetrievalHit(document.id, score, document, "deterministic hash-vector cosine"))
        return sorted(scored, key=lambda item: (-item.score, item.id))[:top_k]


class HybridRetriever:
    def __init__(self, lexical: Retriever, vector: Retriever, *, lexical_weight: float = 0.55):
        if not 0 <= lexical_weight <= 1:
            raise ValueError("lexical_weight must be between zero and one")
        self.lexical = lexical
        self.vector = vector
        self.lexical_weight = lexical_weight

    def search(self, query: str, *, top_k: int, filters=None) -> list[RetrievalHit]:
        width = max(top_k * 3, 10)
        lexical = self.lexical.search(query, top_k=width, filters=filters)
        vector = self.vector.search(query, top_k=width, filters=filters)
        scores: defaultdict[str, float] = defaultdict(float)
        hits: dict[str, RetrievalHit] = {}
        for weight, group in ((self.lexical_weight, lexical), (1 - self.lexical_weight, vector)):
            for rank, hit in enumerate(group, 1):
                scores[hit.id] += weight / (60 + rank)
                hits[hit.id] = hit
        combined = [
            RetrievalHit(item_id, score, hits[item_id].document, "weighted reciprocal-rank fusion")
            for item_id, score in scores.items()
        ]
        ordered = sorted(combined, key=lambda item: (-item.score, item.id))
        selected = ordered[:top_k]
        # Preserve a small amount of modality diversity. Pure RRF can otherwise evict a
        # strong vector-only hit merely because mediocre documents occurred in both lists.
        protected = [*lexical[:2], *vector[:2]]
        protected_ids = {item.id for item in protected}
        for candidate in protected:
            if candidate.id in {item.id for item in selected}:
                continue
            replace_at = next(
                (index for index in range(len(selected) - 1, -1, -1) if selected[index].id not in protected_ids),
                None,
            )
            if replace_at is None:
                break
            selected[replace_at] = RetrievalHit(
                candidate.id,
                scores[candidate.id],
                candidate.document,
                "weighted reciprocal-rank fusion; modality-diversity rescue",
            )
        return selected
