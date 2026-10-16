from __future__ import annotations

import json
from collections import defaultdict
from dataclasses import dataclass
from typing import Any, Iterable, Mapping

from se_kb_app.artifacts.identity import artifact_id


@dataclass(frozen=True)
class RefinedItem:
    identifier: str
    artifact_type: str
    key: str
    content: Mapping[str, Any]
    source_ids: tuple[str, ...]
    conflicts: tuple[str, ...]
    decisions: tuple[str, ...]


def deterministic_refine(items: Iterable[Mapping[str, Any]]) -> tuple[RefinedItem, ...]:
    groups: dict[tuple[str, str], list[Mapping[str, Any]]] = defaultdict(list)
    for item in items:
        artifact_type = str(item.get("type", "unknown"))
        key = str(item.get("key") or item.get("name") or "unknown").strip().casefold()
        groups[(artifact_type, key)].append(item)
    refined: list[RefinedItem] = []
    for (artifact_type, key), candidates in sorted(groups.items()):
        ordered = sorted(candidates, key=_canonical)
        variants = sorted(
            {
                *(_canonical(dict(candidate.get("content", {}))) for candidate in ordered),
                *(
                    str(conflict)
                    for candidate in ordered
                    for conflict in candidate.get("conflicts", ())
                ),
            }
        )
        selected_content = dict(json.loads(variants[0]))
        sources = tuple(
            sorted(
                {
                    str(source)
                    for candidate in ordered
                    for source in candidate.get("source_ids", ())
                }
            )
        )
        conflicts = tuple(variants[1:])
        decisions = (
            "selected lexicographically smallest canonical content",
            f"merged {len(sources)} unique source ids",
            f"preserved {len(conflicts)} conflicting variants",
        )
        identifier = artifact_id(
            "refined",
            artifact_type,
            {"key": key, "content": selected_content, "sources": sources, "conflicts": conflicts},
        )
        refined.append(
            RefinedItem(identifier, artifact_type, key, selected_content, sources, conflicts, decisions)
        )
    return tuple(refined)


def _canonical(value: Mapping[str, Any]) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
