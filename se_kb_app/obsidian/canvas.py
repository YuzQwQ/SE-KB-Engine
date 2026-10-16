from __future__ import annotations

import hashlib
import json
import math
from typing import Mapping, Sequence

from se_kb_app.obsidian.models import NoteIdentity, ProjectedNote, RelationshipEdge, RelationshipKind
from se_kb_app.obsidian.source import KnowledgeRecord


CANVAS_IDENTIFIER = "canvas_knowledge_map"
CANVAS_LOGICAL_PATH = "Knowledge Map.canvas"


def generate_canvas(
    records: Sequence[KnowledgeRecord],
    path_map: Mapping[str, str],
    relationships: Sequence[RelationshipEdge],
    *,
    maximum_nodes: int,
) -> ProjectedNote:
    if maximum_nodes < 1:
        raise ValueError("Canvas node limit must be positive")
    selected = [record for record in sorted(records, key=lambda item: item.identity.identifier) if record.identity.identifier in path_map]
    selected = selected[:maximum_nodes]
    selected_ids = {record.identity.identifier for record in selected}
    columns = max(1, min(4, math.ceil(math.sqrt(len(selected) or 1))))
    nodes: list[dict[str, object]] = []
    node_ids: dict[str, str] = {}
    for index, record in enumerate(selected):
        node_id = _stable_canvas_id("node", record.identity.identifier)
        node_ids[record.identity.identifier] = node_id
        nodes.append(
            {
                "id": node_id,
                "type": "file",
                "file": path_map[record.identity.identifier],
                "x": (index % columns) * 380,
                "y": (index // columns) * 260,
                "width": 320,
                "height": 180,
                "color": "5" if record.identity.kind == "source" else "4",
            }
        )
    edges: list[dict[str, object]] = []
    seen: set[str] = set()
    for edge in sorted(
        relationships,
        key=lambda item: (item.source_id, item.target_id, item.kind.value, item.relation, -(item.score or 0)),
    ):
        if edge.source_id not in selected_ids or edge.target_id not in selected_ids:
            continue
        key = f"{edge.source_id}\0{edge.target_id}\0{edge.kind.value}\0{edge.relation}"
        edge_id = _stable_canvas_id("edge", key)
        if edge_id in seen:
            continue
        seen.add(edge_id)
        label = edge.relation
        if edge.kind is RelationshipKind.SEMANTIC and edge.score is not None:
            label = f"suggested {edge.score:.3f} · {edge.method or 'unknown'}"
        edges.append(
            {
                "id": edge_id,
                "fromNode": node_ids[edge.source_id],
                "fromSide": "right",
                "toNode": node_ids[edge.target_id],
                "toSide": "left",
                "toEnd": "arrow",
                "color": "5" if edge.kind is RelationshipKind.SEMANTIC else "4",
                "label": label,
            }
        )
    value = {"nodes": nodes, "edges": edges}
    content = json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2) + "\n"
    content_hash = hashlib.sha256(content.encode("utf-8")).hexdigest()
    source_payload = json.dumps(
        {
            "nodes": [record.identity.identifier for record in selected],
            "edges": [edge["id"] for edge in edges],
        },
        sort_keys=True,
        separators=(",", ":"),
    )
    source_hash = hashlib.sha256(source_payload.encode("utf-8")).hexdigest()
    return ProjectedNote(
        NoteIdentity(CANVAS_IDENTIFIER, "Knowledge Map", "canvas"),
        CANVAS_LOGICAL_PATH,
        source_id="obsidian_relationship_graph",
        source_url="",
        source_hash=source_hash,
        content_hash=content_hash,
        markdown=content,
        metadata={"format": "json-canvas-1.0", "partial": len(records) > len(selected)},
    )


def _stable_canvas_id(prefix: str, value: str) -> str:
    return f"{prefix}-{hashlib.sha256(value.encode('utf-8')).hexdigest()[:16]}"

