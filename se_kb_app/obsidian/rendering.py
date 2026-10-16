from __future__ import annotations

import hashlib
import html
import json
import re
from collections.abc import Mapping, Sequence
from typing import Any

from se_kb_app.obsidian.models import ProjectedNote, RelationshipEdge, RelationshipKind
from se_kb_app.obsidian.source import KnowledgeRecord


BLOCK_ID = re.compile(r"[^a-zA-Z0-9-]+")


class MarkdownRenderer:
    def render(
        self,
        record: KnowledgeRecord,
        logical_path: str,
        path_map: Mapping[str, str],
        *,
        relationships: Sequence[RelationshipEdge] = (),
        aliases: Sequence[str] = (),
    ) -> tuple[ProjectedNote, tuple[str, ...]]:
        diagnostics: list[str] = []
        explicit_edges = [edge for edge in relationships if edge.kind is RelationshipKind.EXPLICIT]
        semantic_edges = [edge for edge in relationships if edge.kind is RelationshipKind.SEMANTIC]
        alias_tuple = tuple(dict.fromkeys(alias for alias in aliases if alias and alias != record.identity.title))
        frontmatter = {
            "se_kb_schema": "obsidian-note-v1",
            "se_kb_id": record.identity.identifier,
            "se_kb_owned": True,
            "kind": record.identity.kind,
            "title": record.identity.title,
            "aliases": alias_tuple,
            "source_id": record.source_id,
            "source_url": record.source_url,
            "source_hash": record.source_hash,
            "quality": record.quality,
            "trace_version": record.trace_version,
        }
        sections = [render_frontmatter(frontmatter), f"# {escape_markdown(record.identity.title)}", ""]
        sections.extend([escape_untrusted_markup(record.body), ""])
        if record.chunks:
            sections.extend(["## Indexed chunks", ""])
            for index, chunk in enumerate(record.chunks, 1):
                sections.extend(
                    [
                        f"### Chunk {index}",
                        "",
                        escape_untrusted_markup(chunk),
                        f"^{block_identifier(record.identity.identifier, index)}",
                        "",
                    ]
                )
        explicit_lines = self._link_lines(record, explicit_edges, path_map, diagnostics)
        if explicit_lines:
            sections.extend(["## Related knowledge", "", *explicit_lines, ""])
        semantic_lines = self._link_lines(record, semantic_edges, path_map, diagnostics)
        if semantic_lines:
            sections.extend(["## Semantic suggestions", "", *semantic_lines, ""])
        if record.source_url:
            safe_url = record.source_url.replace(" ", "%20").replace(")", "%29")
            sections.extend(["## Source", "", f"[{escape_markdown(record.source_url)}]({safe_url})", ""])
        markdown = "\n".join(sections).rstrip() + "\n"
        content_hash = hashlib.sha256(markdown.encode("utf-8")).hexdigest()
        note = ProjectedNote(
            identity=record.identity,
            logical_path=logical_path,
            source_id=record.source_id,
            source_url=record.source_url,
            source_hash=record.source_hash,
            content_hash=content_hash,
            markdown=markdown,
            quality=record.quality,
            trace_version=record.trace_version,
            aliases=alias_tuple,
            explicit_links=tuple(edge.target_id for edge in explicit_edges if edge.target_id in path_map),
            semantic_links=tuple(edge.target_id for edge in semantic_edges if edge.target_id in path_map),
            metadata=record.metadata,
        )
        return note, tuple(diagnostics)

    def _link_lines(
        self,
        record: KnowledgeRecord,
        edges: Sequence[RelationshipEdge],
        path_map: Mapping[str, str],
        diagnostics: list[str],
    ) -> list[str]:
        lines: list[str] = []
        for edge in sorted(edges, key=lambda item: (item.target_id, item.relation, -(item.score or 0))):
            target_id = edge.target_id if edge.source_id == record.identity.identifier else edge.source_id
            target = path_map.get(target_id)
            if target is None:
                diagnostics.append(f"unresolved_reference:{target_id}")
                continue
            note_target = target[:-3] if target.endswith(".md") else target
            relation = escape_markdown(edge.relation)
            if edge.kind is RelationshipKind.SEMANTIC:
                lines.append(f"- [[{escape_wikilink(note_target)}]] — {relation}, score {edge.score:.3f} ({escape_markdown(edge.method or '')})")
            else:
                lines.append(f"- [[{escape_wikilink(note_target)}]] — {relation}")
        return lines


def render_frontmatter(values: Mapping[str, Any]) -> str:
    lines = ["---"]
    for key, value in values.items():
        if value is None or value == () or value == []:
            continue
        if isinstance(value, bool):
            rendered = "true" if value else "false"
            lines.append(f"{key}: {rendered}")
        elif isinstance(value, (int, float)) and not isinstance(value, bool):
            lines.append(f"{key}: {value}")
        elif isinstance(value, (list, tuple)):
            lines.append(f"{key}:")
            lines.extend(f"  - {_yaml_string(str(item))}" for item in value)
        else:
            lines.append(f"{key}: {_yaml_string(str(value))}")
    lines.append("---")
    return "\n".join(lines)


def escape_untrusted_markup(value: str) -> str:
    escaped = html.escape(value, quote=False)
    escaped = escaped.replace("[[", "\\[\\[").replace("]]", "\\]\\]")
    return escaped.replace("\x00", "")


def escape_markdown(value: str) -> str:
    single_line = " ".join(value.replace("\x00", "").splitlines())
    return html.escape(single_line, quote=False).replace("[", "\\[").replace("]", "\\]")


def escape_wikilink(value: str) -> str:
    return value.replace("|", "-").replace("#", "-").replace("[", "-").replace("]", "-")


def block_identifier(identifier: str, index: int) -> str:
    normalized = BLOCK_ID.sub("-", identifier.lower()).strip("-")[:48] or "note"
    suffix = hashlib.sha256(f"{identifier}:{index}".encode("utf-8")).hexdigest()[:8]
    return f"se-kb-{normalized}-{suffix}"


def _yaml_string(value: str) -> str:
    return json.dumps(value.replace("\x00", ""), ensure_ascii=False)
