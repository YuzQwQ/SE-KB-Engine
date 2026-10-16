from __future__ import annotations

from dataclasses import dataclass
from types import MappingProxyType
from typing import Any, Iterable, Mapping, Sequence

from se_kb_app.domain import RetrievalResult
from se_kb_app.obsidian.models import RelationshipEdge, RelationshipKind
from se_kb_app.obsidian.source import KnowledgeRecord


@dataclass(frozen=True)
class RelationshipNode:
    identifier: str
    title: str
    kind: str
    source_url: str
    logical_path: str | None = None


@dataclass(frozen=True)
class RelationshipPage:
    nodes: tuple[RelationshipNode, ...]
    edges: tuple[RelationshipEdge, ...]
    total: int
    offset: int
    limit: int
    partial: bool


def explicit_edges(records: Iterable[KnowledgeRecord]) -> tuple[RelationshipEdge, ...]:
    edges: list[RelationshipEdge] = []
    known: set[tuple[str, str, str]] = set()
    for record in sorted(records, key=lambda item: item.identity.identifier):
        if record.identity.kind != "source" and record.source_id != record.identity.identifier:
            _append_unique(
                edges,
                known,
                RelationshipEdge(
                    record.identity.identifier,
                    record.source_id,
                    "derived_from",
                    RelationshipKind.EXPLICIT,
                    metadata={"provenance": "artifact_source"},
                ),
            )
        for target in sorted(set(record.explicit_targets)):
            if target != record.identity.identifier:
                _append_unique(
                    edges,
                    known,
                    RelationshipEdge(
                        record.identity.identifier,
                        target,
                        "related_to",
                        RelationshipKind.EXPLICIT,
                        metadata={"provenance": "artifact_relationship"},
                    ),
                )
    return tuple(edges)


def semantic_edges_from_results(
    results: Mapping[str, RetrievalResult | Sequence[Mapping[str, Any]]],
    *,
    minimum_score: float,
    maximum_neighbors: int,
    method: str = "vector_similarity",
    index_version: str | None = None,
) -> tuple[RelationshipEdge, ...]:
    if not 0 <= minimum_score <= 1:
        raise ValueError("minimum semantic score must be between 0 and 1")
    if maximum_neighbors < 0:
        raise ValueError("maximum neighbors cannot be negative")
    candidates: list[RelationshipEdge] = []
    for source_id, result in sorted(results.items()):
        items = result.items if isinstance(result, RetrievalResult) else tuple(result)
        per_source: list[RelationshipEdge] = []
        for item in items:
            target = _item_identifier(item)
            score = _item_score(item)
            if target is None or target == source_id or score is None or score < minimum_score:
                continue
            per_source.append(
                RelationshipEdge(
                    source_id,
                    target,
                    "similar_to",
                    RelationshipKind.SEMANTIC,
                    score=score,
                    method=str(item.get("method") or method),
                    index_version=str(item.get("index_version") or index_version or "unknown"),
                    metadata={"provenance": "retrieval_similarity"},
                )
            )
        per_source.sort(key=lambda edge: (-(edge.score or 0), edge.target_id, edge.method or ""))
        candidates.extend(per_source[:maximum_neighbors])
    return _deduplicate_semantic(candidates)


class RelationshipQueryService:
    def __init__(
        self,
        records: Iterable[KnowledgeRecord],
        edges: Iterable[RelationshipEdge],
        *,
        path_map: Mapping[str, str] | None = None,
        maximum_limit: int = 1000,
    ) -> None:
        self.records = MappingProxyType({item.identity.identifier: item for item in records})
        self.edges = tuple(sorted(edges, key=_edge_sort_key))
        self.path_map = MappingProxyType(dict(path_map or {}))
        self.maximum_limit = maximum_limit

    def query(
        self,
        *,
        node: str | None = None,
        kind: RelationshipKind | None = None,
        source: str | None = None,
        minimum_score: float = 0.0,
        offset: int = 0,
        limit: int = 100,
    ) -> RelationshipPage:
        if offset < 0 or limit < 1 or limit > self.maximum_limit:
            raise ValueError("relationship page is outside allowed bounds")
        if not 0 <= minimum_score <= 1:
            raise ValueError("minimum score must be between 0 and 1")
        filtered = [
            edge
            for edge in self.edges
            if (node is None or node in {edge.source_id, edge.target_id})
            and (kind is None or edge.kind is kind)
            and (edge.score is None or edge.score >= minimum_score)
            and self._matches_source(edge, source)
        ]
        selected = tuple(filtered[offset : offset + limit])
        identifiers = sorted({identifier for edge in selected for identifier in (edge.source_id, edge.target_id)})
        nodes = tuple(self._node(identifier) for identifier in identifiers)
        return RelationshipPage(nodes, selected, len(filtered), offset, limit, offset + len(selected) < len(filtered))

    def _matches_source(self, edge: RelationshipEdge, source: str | None) -> bool:
        if source is None:
            return True
        return any(
            source in record.source_url
            for identifier in (edge.source_id, edge.target_id)
            if (record := self.records.get(identifier)) is not None
        )

    def _node(self, identifier: str) -> RelationshipNode:
        record = self.records.get(identifier)
        if record is None:
            return RelationshipNode(identifier, identifier, "unknown", "", self.path_map.get(identifier))
        return RelationshipNode(
            identifier,
            record.identity.title,
            record.identity.kind,
            record.source_url,
            self.path_map.get(identifier),
        )


def _append_unique(
    edges: list[RelationshipEdge],
    known: set[tuple[str, str, str]],
    edge: RelationshipEdge,
) -> None:
    key = (edge.source_id, edge.target_id, edge.relation)
    if key not in known:
        known.add(key)
        edges.append(edge)


def _deduplicate_semantic(edges: Iterable[RelationshipEdge]) -> tuple[RelationshipEdge, ...]:
    best: dict[tuple[str, str], RelationshipEdge] = {}
    for edge in edges:
        pair = (
            (edge.source_id, edge.target_id)
            if edge.source_id <= edge.target_id
            else (edge.target_id, edge.source_id)
        )
        current = best.get(pair)
        if current is None or (edge.score or 0) > (current.score or 0) or (
            edge.score == current.score and _edge_sort_key(edge) < _edge_sort_key(current)
        ):
            best[pair] = edge
    return tuple(sorted(best.values(), key=_edge_sort_key))


def _item_identifier(item: Mapping[str, Any]) -> str | None:
    for key in ("id", "identifier", "document_id", "artifact_id", "parent_id"):
        value = item.get(key)
        if isinstance(value, str) and value:
            return value
    metadata = item.get("metadata")
    if isinstance(metadata, Mapping):
        return _item_identifier(metadata)
    return None


def _item_score(item: Mapping[str, Any]) -> float | None:
    for key in ("score", "similarity", "relevance"):
        value = item.get(key)
        if isinstance(value, (int, float)) and not isinstance(value, bool):
            score = float(value)
            return score if 0 <= score <= 1 else None
    distance = item.get("distance")
    if isinstance(distance, (int, float)) and not isinstance(distance, bool):
        return max(0.0, min(1.0, 1.0 - float(distance)))
    return None


def _edge_sort_key(edge: RelationshipEdge) -> tuple[str, str, str, str, float]:
    return (
        edge.source_id,
        edge.target_id,
        edge.kind.value,
        edge.relation,
        -(edge.score or 0),
    )
