from __future__ import annotations

import pytest

from se_kb_app.domain import RetrievalResult
from se_kb_app.obsidian.models import NoteIdentity, RelationshipKind
from se_kb_app.obsidian.relationships import (
    RelationshipQueryService,
    explicit_edges,
    semantic_edges_from_results,
)
from se_kb_app.obsidian.source import KnowledgeRecord


def _record(identifier: str, title: str, kind: str = "concept", source: str = "https://example.com"):
    return KnowledgeRecord(
        NoteIdentity(identifier, title, kind),
        source_id="doc_source",
        source_url=source,
        source_hash="a" * 64,
        body=title,
        artifact_kind=kind,
        explicit_targets=("concept_b",) if identifier == "concept_a" else (),
    )


@pytest.mark.unit
def test_explicit_relationships_keep_artifact_and_source_provenance():
    edges = explicit_edges((_record("concept_a", "A"), _record("concept_b", "B")))
    assert any(edge.relation == "related_to" and edge.target_id == "concept_b" for edge in edges)
    assert all(edge.kind is RelationshipKind.EXPLICIT for edge in edges)
    assert {edge.metadata["provenance"] for edge in edges} == {
        "artifact_source",
        "artifact_relationship",
    }


@pytest.mark.unit
def test_semantic_relationships_apply_threshold_neighbor_bound_and_deduplication():
    results = {
        "concept_a": RetrievalResult(
            "a",
            "concept",
            (
                {"id": "concept_b", "score": 0.92},
                {"id": "concept_c", "score": 0.88},
                {"id": "concept_d", "score": 0.2},
            ),
        ),
        "concept_b": RetrievalResult("b", "concept", ({"id": "concept_a", "score": 0.95},)),
    }
    edges = semantic_edges_from_results(results, minimum_score=0.8, maximum_neighbors=2)
    assert [(edge.source_id, edge.target_id, edge.score) for edge in edges] == [
        ("concept_a", "concept_c", 0.88),
        ("concept_b", "concept_a", 0.95),
    ]
    assert all(edge.kind is RelationshipKind.SEMANTIC for edge in edges)
    assert all(edge.method == "vector_similarity" for edge in edges)


@pytest.mark.unit
def test_relationship_query_is_bounded_filterable_and_reports_partial_page():
    records = tuple(_record(f"concept_{letter}", letter) for letter in "abcd")
    results = {
        "concept_a": [
            {"id": "concept_b", "score": 0.95},
            {"id": "concept_c", "score": 0.90},
            {"id": "concept_d", "score": 0.85},
        ]
    }
    edges = (*explicit_edges(records), *semantic_edges_from_results(results, minimum_score=0.0, maximum_neighbors=3))
    service = RelationshipQueryService(records, edges, maximum_limit=2)
    page = service.query(kind=RelationshipKind.SEMANTIC, minimum_score=0.89, limit=1)
    assert page.total == 2
    assert page.partial is True
    assert len(page.edges) == 1
    assert {node.identifier for node in page.nodes} == {"concept_a", "concept_b"}
    with pytest.raises(ValueError, match="bounds"):
        service.query(limit=3)


@pytest.mark.unit
def test_semantic_edges_are_never_reclassified_as_explicit_facts():
    edges = semantic_edges_from_results(
        {"a": [{"id": "b", "similarity": 0.9}]},
        minimum_score=0.5,
        maximum_neighbors=5,
        method="cosine",
        index_version="v1",
    )
    assert edges[0].kind is RelationshipKind.SEMANTIC
    assert edges[0].metadata == {"provenance": "retrieval_similarity"}
    assert edges[0].index_version == "v1"
