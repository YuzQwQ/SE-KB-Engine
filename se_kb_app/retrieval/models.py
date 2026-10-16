from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Mapping


@dataclass(frozen=True)
class EvaluationDocument:
    id: str
    text: str
    source: str
    kind: str
    date: str
    quality: float
    parent_id: str | None = None
    metadata: Mapping[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class EvaluationQuery:
    id: str
    text: str
    intent: str
    relevance: Mapping[str, int]
    hard_negatives: tuple[str, ...]
    no_answer: bool
    split: str


@dataclass(frozen=True)
class EvaluationDataset:
    version: str
    documents: tuple[EvaluationDocument, ...]
    queries: tuple[EvaluationQuery, ...]
    fingerprint: str

    @classmethod
    def load(cls, documents_path: Path, queries_path: Path) -> "EvaluationDataset":
        document_rows = _read_jsonl(documents_path)
        query_rows = _read_jsonl(queries_path)
        if not document_rows or not query_rows:
            raise ValueError("evaluation dataset must contain documents and queries")
        versions = {str(row.get("dataset_version", "")) for row in [*document_rows, *query_rows]}
        if len(versions) != 1 or "" in versions:
            raise ValueError("all rows must declare one non-empty dataset_version")
        documents = tuple(
            EvaluationDocument(
                id=_required_string(row, "id"),
                text=_required_string(row, "text"),
                source=_required_string(row, "source"),
                kind=_required_string(row, "kind"),
                date=_required_string(row, "date"),
                quality=float(row["quality"]),
                parent_id=str(row["parent_id"]) if row.get("parent_id") else None,
                metadata=dict(row.get("metadata", {})),
            )
            for row in document_rows
        )
        queries = tuple(
            EvaluationQuery(
                id=_required_string(row, "id"),
                text=_required_string(row, "text"),
                intent=_required_string(row, "intent"),
                relevance={str(key): int(value) for key, value in dict(row["relevance"]).items()},
                hard_negatives=tuple(str(value) for value in row.get("hard_negatives", ())),
                no_answer=bool(row["no_answer"]),
                split=_required_string(row, "split"),
            )
            for row in query_rows
        )
        document_ids = [item.id for item in documents]
        query_ids = [item.id for item in queries]
        if len(document_ids) != len(set(document_ids)) or len(query_ids) != len(set(query_ids)):
            raise ValueError("document and query IDs must be unique")
        known = set(document_ids)
        for query in queries:
            if set(query.relevance).difference(known) or set(query.hard_negatives).difference(known):
                raise ValueError(f"query {query.id} references unknown documents")
            if query.no_answer and query.relevance:
                raise ValueError(f"no-answer query {query.id} cannot have relevance judgments")
            if query.split not in {"dev", "holdout"}:
                raise ValueError(f"query {query.id} has unsupported split")
        digest = hashlib.sha256(documents_path.read_bytes() + b"\0" + queries_path.read_bytes()).hexdigest()
        return cls(versions.pop(), documents, queries, digest)


def _read_jsonl(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for line_number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        if not line.strip():
            continue
        value = json.loads(line)
        if not isinstance(value, dict):
            raise ValueError(f"{path}:{line_number} must contain a JSON object")
        rows.append(value)
    return rows


def _required_string(row: Mapping[str, Any], key: str) -> str:
    value = row.get(key)
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{key} must be a non-empty string")
    return value
