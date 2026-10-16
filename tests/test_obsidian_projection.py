from __future__ import annotations

import json
from pathlib import Path

import pytest

from se_kb_app.obsidian.models import RelationshipEdge, RelationshipKind
from se_kb_app.obsidian.projection import KnowledgeProjector
from se_kb_app.obsidian.rendering import MarkdownRenderer, block_identifier
from se_kb_app.obsidian.source import ArtifactKnowledgeSource, KnowledgeSelection


def _legacy_batch(root: Path) -> Path:
    batch = root / "2026" / "09" / "18" / "example"
    batch.mkdir(parents=True)
    (batch / "metadata.json").write_text(
        json.dumps(
            {
                "title": "向量库：[测试]",
                "source_url": "https://example.com/vector",
                "reliability_score": 0.9,
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    (batch / "parsed.json").write_text(
        json.dumps(
            {
                "title": "向量库",
                "source_url": "https://example.com/vector",
                "chunks": [
                    {"text": "第一段 <script>alert(1)</script>"},
                    {"text": "第二段 [[伪造链接]]"},
                ],
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    (batch / "document.md").write_text("正文 <b>不能执行</b>\n", encoding="utf-8")
    (batch / "dfd_concepts_example.json").write_text(
        json.dumps(
            {
                "concepts": [
                    {
                        "concept_id": "concept_vector",
                        "name": "向量数据库",
                        "definition": "用于语义检索。",
                        "confidence": 0.95,
                        "relationships": [{"target_id": "concept_rag"}],
                    },
                    {
                        "concept_id": "concept_rag",
                        "name": "RAG",
                        "definition": "检索增强生成。",
                        "confidence": 0.85,
                    },
                ]
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    (batch / "chunks_example.json").write_text(
        json.dumps({"id": "raw_chunk", "content": "must not become a note"}),
        encoding="utf-8",
    )
    return batch


@pytest.mark.integration
def test_artifact_source_maps_documents_and_entities_but_not_raw_chunks(tmp_path: Path):
    root = tmp_path / "artifacts"
    _legacy_batch(root)
    result = ArtifactKnowledgeSource(root).read()
    assert result.diagnostics == ()
    assert [record.identity.kind for record in result.records] == ["concept", "concept", "source"]
    source = next(record for record in result.records if record.identity.kind == "source")
    assert len(source.chunks) == 2
    assert source.quality == 0.9
    concept = next(record for record in result.records if record.identity.identifier == "concept_vector")
    assert concept.source_url == "https://example.com/vector"
    assert concept.explicit_targets == ("concept_rag",)
    assert all(record.identity.identifier != "raw_chunk" for record in result.records)


@pytest.mark.unit
def test_artifact_selection_filters_source_kind_quality_and_date(tmp_path: Path):
    root = tmp_path / "artifacts"
    _legacy_batch(root)
    result = ArtifactKnowledgeSource(root).read(
        KnowledgeSelection(
            sources=("example.com",),
            kinds=("concept",),
            entity_kinds=("concept",),
            minimum_quality=0.9,
        )
    )
    assert [record.identity.identifier for record in result.records] == ["concept_vector"]


@pytest.mark.unit
def test_projection_renders_stable_safe_frontmatter_chunks_links_and_provenance(tmp_path: Path):
    root = tmp_path / "artifacts"
    _legacy_batch(root)
    records = ArtifactKnowledgeSource(root).read().records
    explicit = RelationshipEdge(
        "concept_vector",
        "concept_rag",
        "depends_on",
        RelationshipKind.EXPLICIT,
    )
    semantic = RelationshipEdge(
        "concept_rag",
        "concept_vector",
        "similar_to",
        RelationshipKind.SEMANTIC,
        score=0.91234,
        method="cosine",
        index_version="index-v1",
    )
    projector = KnowledgeProjector()
    first = projector.project(records, relationships=(explicit, semantic))
    second = projector.project(reversed(records), relationships=(explicit, semantic))
    assert first.path_map == second.path_map
    assert [note.markdown for note in first.notes] == [note.markdown for note in second.notes]

    source = next(note for note in first.notes if note.identity.kind == "source")
    assert "&lt;b&gt;不能执行&lt;/b&gt;" in source.markdown
    assert "&lt;script&gt;alert(1)&lt;/script&gt;" in source.markdown
    assert "\\[\\[伪造链接\\]\\]" in source.markdown
    assert f"^{block_identifier(source.identity.identifier, 1)}" in source.markdown
    vector = next(note for note in first.notes if note.identity.identifier == "concept_vector")
    assert "## Related knowledge" in vector.markdown
    assert "## Semantic suggestions" in vector.markdown
    assert "score 0.912 (cosine)" in vector.markdown
    assert vector.content_hash == second.notes[[item.identity.identifier for item in second.notes].index("concept_vector")].content_hash


@pytest.mark.unit
def test_renderer_reports_unresolved_references_and_quotes_malicious_frontmatter(tmp_path: Path):
    root = tmp_path / "artifacts"
    _legacy_batch(root)
    record = next(
        item
        for item in ArtifactKnowledgeSource(root).read().records
        if item.identity.identifier == "concept_vector"
    )
    edge = RelationshipEdge("concept_vector", "missing", "references", RelationshipKind.EXPLICIT)
    note, diagnostics = MarkdownRenderer().render(
        record,
        "Knowledge/concept/vector.md",
        {"concept_vector": "Knowledge/concept/vector.md"},
        relationships=(edge,),
        aliases=('bad"\nowned: false',),
    )
    assert diagnostics == ("unresolved_reference:missing",)
    assert '  - "bad\\"\\nowned: false"' in note.markdown
    assert "\nowned: false\n" not in note.markdown


@pytest.mark.unit
def test_projection_preserves_noncolliding_previous_title_as_alias(tmp_path: Path):
    root = tmp_path / "artifacts"
    _legacy_batch(root)
    records = ArtifactKnowledgeSource(root).read().records
    result = KnowledgeProjector().project(records, previous_titles={"concept_vector": "旧名称"})
    note = next(item for item in result.notes if item.identity.identifier == "concept_vector")
    assert note.aliases == ("旧名称",)
    assert '  - "旧名称"' in note.markdown
