from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, Mapping, Sequence

from se_kb_app.obsidian.models import ProjectedNote, RelationshipEdge
from se_kb_app.obsidian.paths import build_note_path_map
from se_kb_app.obsidian.rendering import MarkdownRenderer
from se_kb_app.obsidian.source import KnowledgeRecord


@dataclass(frozen=True)
class ProjectionResult:
    notes: tuple[ProjectedNote, ...]
    path_map: Mapping[str, str]
    diagnostics: tuple[str, ...] = ()


class KnowledgeProjector:
    def __init__(self, renderer: MarkdownRenderer | None = None) -> None:
        self.renderer = renderer or MarkdownRenderer()

    def project(
        self,
        records: Iterable[KnowledgeRecord],
        *,
        relationships: Sequence[RelationshipEdge] = (),
        previous_titles: Mapping[str, str] | None = None,
    ) -> ProjectionResult:
        ordered = tuple(sorted(records, key=lambda item: item.identity.identifier))
        path_map = build_note_path_map(record.identity for record in ordered)
        edge_map: dict[str, list[RelationshipEdge]] = {}
        for edge in relationships:
            edge_map.setdefault(edge.source_id, []).append(edge)
            edge_map.setdefault(edge.target_id, []).append(edge)
        diagnostics: list[str] = []
        notes: list[ProjectedNote] = []
        old_titles = previous_titles or {}
        occupied_aliases = {record.identity.title.casefold() for record in ordered}
        for record in ordered:
            aliases: tuple[str, ...] = ()
            previous = old_titles.get(record.identity.identifier)
            if previous and previous != record.identity.title and previous.casefold() not in occupied_aliases:
                aliases = (previous,)
                occupied_aliases.add(previous.casefold())
            note, note_diagnostics = self.renderer.render(
                record,
                path_map[record.identity.identifier],
                path_map,
                relationships=edge_map.get(record.identity.identifier, ()),
                aliases=aliases,
            )
            notes.append(note)
            diagnostics.extend(note_diagnostics)
        return ProjectionResult(tuple(notes), path_map, tuple(sorted(set(diagnostics))))
