from __future__ import annotations

import hashlib
import json
from collections import Counter
from pathlib import Path
from typing import Iterable, Mapping

from se_kb_app.obsidian.models import ExportAction, ExportPlan, PlannedNote, ProjectedNote
from se_kb_app.obsidian.paths import VaultPathPolicy
from se_kb_app.obsidian.state import ExportState, ExportedNoteState


def hash_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        while chunk := stream.read(1024 * 1024):
            digest.update(chunk)
    return digest.hexdigest()


def corpus_fingerprint(notes: Iterable[ProjectedNote], configuration: Mapping[str, object] | None = None) -> str:
    canonical = {
        "configuration": dict(configuration or {}),
        "notes": [
            {
                "identifier": note.identity.identifier,
                "logical_path": note.logical_path,
                "source_hash": note.source_hash,
                "content_hash": note.content_hash,
            }
            for note in sorted(notes, key=lambda item: item.identity.identifier)
        ],
    }
    payload = json.dumps(canonical, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


class ExportPlanner:
    def __init__(self, policy: VaultPathPolicy) -> None:
        self.policy = policy

    def plan(
        self,
        notes: Iterable[ProjectedNote],
        previous: ExportState | None,
        *,
        configuration: Mapping[str, object] | None = None,
        offset: int = 0,
        limit: int | None = None,
    ) -> ExportPlan:
        if offset < 0 or (limit is not None and limit < 1):
            raise ValueError("preview page is outside allowed bounds")
        ordered = tuple(sorted(notes, key=lambda item: item.identity.identifier))
        fingerprint = corpus_fingerprint(ordered, configuration)
        previous_by_id = {item.identifier: item for item in previous.notes} if previous else {}
        actions: list[PlannedNote] = []
        current_ids: set[str] = set()
        for note in ordered:
            current_ids.add(note.identity.identifier)
            old = previous_by_id.get(note.identity.identifier)
            actions.append(self._classify(note, old))
        for identifier, old in sorted(previous_by_id.items()):
            if identifier not in current_ids:
                actions.append(
                    PlannedNote(
                        ExportAction.STALE,
                        identifier,
                        old.logical_path,
                        "source_not_selected",
                        previous_path=old.logical_path,
                    )
                )
        actions.sort(key=lambda item: (item.action.value, item.logical_path.casefold(), item.identifier))
        counts = dict(Counter(item.action.value for item in actions))
        total = len(actions)
        end = total if limit is None else min(total, offset + limit)
        page = tuple(actions[offset:end])
        return ExportPlan(
            fingerprint,
            page,
            total,
            offset=offset,
            limit=total if limit is None else limit,
            partial=offset > 0 or end < total,
            action_counts=counts,
        )

    def _classify(self, note: ProjectedNote, old: ExportedNoteState | None) -> PlannedNote:
        try:
            destination = self.policy.destination(note.logical_path)
        except ValueError:
            return PlannedNote(
                ExportAction.SKIPPED,
                note.identity.identifier,
                note.logical_path,
                "unsafe_destination",
                note=note,
            )
        if old is None:
            if destination.exists():
                return PlannedNote(
                    ExportAction.CONFLICT,
                    note.identity.identifier,
                    note.logical_path,
                    "unowned_destination_exists",
                    note=note,
                )
            return PlannedNote(
                ExportAction.CREATE,
                note.identity.identifier,
                note.logical_path,
                "new_note",
                note=note,
            )
        try:
            previous_destination = self.policy.destination(old.logical_path)
        except ValueError:
            return PlannedNote(
                ExportAction.CONFLICT,
                note.identity.identifier,
                note.logical_path,
                "previous_path_is_unsafe",
                previous_path=old.logical_path,
                note=note,
            )
        if previous_destination.exists() and hash_file(previous_destination) != old.published_hash:
            return PlannedNote(
                ExportAction.CONFLICT,
                note.identity.identifier,
                note.logical_path,
                "managed_note_modified",
                previous_path=old.logical_path,
                note=note,
            )
        if not previous_destination.exists():
            return PlannedNote(
                ExportAction.CONFLICT,
                note.identity.identifier,
                note.logical_path,
                "managed_note_missing",
                previous_path=old.logical_path,
                note=note,
            )
        if note.logical_path != old.logical_path:
            if destination.exists() and destination != previous_destination:
                return PlannedNote(
                    ExportAction.CONFLICT,
                    note.identity.identifier,
                    note.logical_path,
                    "rename_destination_exists",
                    previous_path=old.logical_path,
                    note=note,
                )
            return PlannedNote(
                ExportAction.RENAME,
                note.identity.identifier,
                note.logical_path,
                "title_or_layout_changed",
                previous_path=old.logical_path,
                note=note,
            )
        if note.content_hash == old.published_hash:
            return PlannedNote(
                ExportAction.UNCHANGED,
                note.identity.identifier,
                note.logical_path,
                "content_unchanged",
                previous_path=old.logical_path,
                note=note,
            )
        return PlannedNote(
            ExportAction.UPDATE,
            note.identity.identifier,
            note.logical_path,
            "source_or_rendered_content_changed",
            previous_path=old.logical_path,
            note=note,
        )
