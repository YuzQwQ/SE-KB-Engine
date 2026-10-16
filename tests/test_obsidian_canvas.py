from __future__ import annotations

import json

import pytest

from se_kb_app.obsidian.canvas import CANVAS_LOGICAL_PATH, generate_canvas
from se_kb_app.obsidian.models import NoteIdentity, RelationshipEdge, RelationshipKind
from se_kb_app.obsidian.source import KnowledgeRecord


def _record(identifier: str, title: str, kind: str = "concept") -> KnowledgeRecord:
    return KnowledgeRecord(
        NoteIdentity(identifier, title, kind),
        source_id="doc",
        source_url="https://example.com",
        source_hash="a" * 64,
        body=title,
        artifact_kind=kind,
    )


@pytest.mark.unit
def test_canvas_uses_json_canvas_file_nodes_stable_layout_and_relationship_styles():
    records = (_record("a", "A", "source"), _record("b", "B"), _record("c", "C"))
    paths = {"a": "Sources/A.md", "b": "Knowledge/concept/B.md", "c": "Knowledge/concept/C.md"}
    edges = (
        RelationshipEdge("a", "b", "contains", RelationshipKind.EXPLICIT),
        RelationshipEdge("b", "c", "similar_to", RelationshipKind.SEMANTIC, score=0.91, method="cosine"),
    )
    first = generate_canvas(records, paths, edges, maximum_nodes=10)
    second = generate_canvas(tuple(reversed(records)), paths, tuple(reversed(edges)), maximum_nodes=10)
    assert first.logical_path == CANVAS_LOGICAL_PATH
    assert first.markdown == second.markdown
    value = json.loads(first.markdown)
    assert set(value) == {"nodes", "edges"}
    assert [node["file"] for node in value["nodes"]] == ["Sources/A.md", "Knowledge/concept/B.md", "Knowledge/concept/C.md"]
    assert len({(node["x"], node["y"]) for node in value["nodes"]}) == 3
    assert value["edges"][0]["color"] == "4"
    assert value["edges"][1]["color"] == "5"
    assert value["edges"][1]["label"] == "suggested 0.910 · cosine"


@pytest.mark.unit
def test_canvas_is_bounded_and_escapes_untrusted_labels_through_json():
    records = (_record("a", 'A"\n<script>'), _record("b", "B"), _record("c", "C"))
    paths = {item.identity.identifier: f"{item.identity.identifier}.md" for item in records}
    note = generate_canvas(records, paths, (), maximum_nodes=2)
    value = json.loads(note.markdown)
    assert len(value["nodes"]) == 2
    assert note.metadata["partial"] is True
    assert "<script>" not in note.markdown


@pytest.mark.integration
def test_canvas_disabled_by_default_and_enabled_canvas_uses_normal_conflict_planning(tmp_path):
    from se_kb_app.obsidian.paths import VaultPathPolicy
    from se_kb_app.obsidian.planning import ExportPlanner
    from se_kb_app.settings import AppSettings

    vault = tmp_path / "vault"
    vault.mkdir()
    disabled = AppSettings.from_sources(
        environ={}, overrides={"project_root": tmp_path, "obsidian_vault_root": vault}
    )
    assert disabled.obsidian.canvas_enabled is False
    canvas = generate_canvas((_record("a", "A"),), {"a": "a.md"}, (), maximum_nodes=10)
    policy = VaultPathPolicy.from_settings(disabled.obsidian)
    destination = policy.destination(canvas.logical_path)
    destination.parent.mkdir(parents=True)
    destination.write_text("user canvas", encoding="utf-8")
    action = ExportPlanner(policy).plan((canvas,), None).actions[0]
    assert action.action.value == "conflict"
    assert destination.read_text(encoding="utf-8") == "user canvas"
