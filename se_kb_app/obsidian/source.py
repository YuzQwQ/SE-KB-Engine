from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from datetime import date, datetime
from pathlib import Path
from types import MappingProxyType
from typing import Any, Iterable, Mapping
from urllib.parse import urlsplit

from se_kb_app.artifacts.reader import ArtifactReader, ReadBatch
from se_kb_app.obsidian.models import NoteIdentity


SYSTEM_JSON_FILES = {
    "manifest.json",
    "metadata.json",
    "parsed.json",
    "trace.json",
    "metrics.json",
    "errors.json",
}
ENTITY_LIST_KINDS = {
    "concepts": "concept",
    "rules": "rule",
    "patterns": "pattern",
    "templates": "pattern",
    "examples": "example",
    "criteria": "criterion",
    "checklist": "check",
    "transformations": "transformation",
}


@dataclass(frozen=True)
class KnowledgeSelection:
    sources: tuple[str, ...] = ()
    kinds: tuple[str, ...] = ()
    entity_kinds: tuple[str, ...] = ()
    minimum_quality: float = 0.0
    date_from: date | None = None
    date_to: date | None = None

    def matches(self, record: "KnowledgeRecord") -> bool:
        if record.quality is not None and record.quality < self.minimum_quality:
            return False
        if self.kinds and record.artifact_kind not in self.kinds:
            return False
        if record.identity.kind != "source" and self.entity_kinds and record.identity.kind not in self.entity_kinds:
            return False
        if self.sources:
            host = urlsplit(record.source_url).hostname or ""
            if not any(value == host or value in record.source_url for value in self.sources):
                return False
        if record.created_at is not None:
            day = record.created_at.date()
            if self.date_from is not None and day < self.date_from:
                return False
            if self.date_to is not None and day > self.date_to:
                return False
        return True


@dataclass(frozen=True)
class KnowledgeRecord:
    identity: NoteIdentity
    source_id: str
    source_url: str
    source_hash: str
    body: str
    artifact_kind: str
    quality: float | None = None
    trace_version: str | None = None
    created_at: datetime | None = None
    chunks: tuple[str, ...] = ()
    explicit_targets: tuple[str, ...] = ()
    metadata: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        object.__setattr__(self, "metadata", MappingProxyType(dict(self.metadata)))


@dataclass(frozen=True)
class KnowledgeReadResult:
    records: tuple[KnowledgeRecord, ...]
    diagnostics: tuple[str, ...] = ()


class ArtifactKnowledgeSource:
    def __init__(self, root: Path, *, reader: ArtifactReader | None = None) -> None:
        self.root = root.resolve()
        self.reader = reader or ArtifactReader()

    def read(self, selection: KnowledgeSelection | None = None) -> KnowledgeReadResult:
        if not self.root.is_dir():
            return KnowledgeReadResult((), ("artifact_root_unavailable",))
        selected = selection or KnowledgeSelection()
        records: list[KnowledgeRecord] = []
        diagnostics: list[str] = []
        directories = {path.parent for path in self.root.rglob("manifest.json")}
        directories.update(
            path.parent
            for path in self.root.rglob("metadata.json")
            if not (path.parent / "manifest.json").is_file()
        )
        for directory in sorted(directories):
            try:
                batch = self.reader.read(directory)
                batch_records = self._records_for_batch(batch)
                records.extend(record for record in batch_records if selected.matches(record))
            except (OSError, UnicodeError, ValueError, json.JSONDecodeError):
                diagnostics.append(f"unreadable_batch:{directory.relative_to(self.root).as_posix()}")
        records.sort(key=lambda item: (item.identity.kind, item.identity.identifier))
        return KnowledgeReadResult(tuple(records), tuple(diagnostics))

    def _records_for_batch(self, batch: ReadBatch) -> tuple[KnowledgeRecord, ...]:
        metadata = _read_object(batch.path / "metadata.json")
        parsed = _read_object(batch.path / "parsed.json")
        manifest = batch.manifest
        source_url = batch.source_url or str(parsed.get("source_url") or parsed.get("url") or "")
        document_path = batch.path / "document.md"
        body = document_path.read_text(encoding="utf-8") if document_path.is_file() else _document_text(parsed)
        title = str(metadata.get("title") or parsed.get("title") or batch.path.name)
        document_id = manifest.document_id if manifest else _stable_id("doc", source_url, body)
        source_hash = manifest.content_hash if manifest else _sha256_text(body)
        created_at = manifest.created_at if manifest else _path_datetime(batch.path)
        quality = _quality(metadata, parsed)
        trace_version = manifest.trace.schema_version if manifest else None
        chunks = _extract_chunks(parsed)
        records: list[KnowledgeRecord] = []
        if body.strip():
            records.append(
                KnowledgeRecord(
                    NoteIdentity(document_id, title, "source"),
                    source_id=document_id,
                    source_url=source_url,
                    source_hash=source_hash,
                    body=body,
                    artifact_kind="source",
                    quality=quality,
                    trace_version=trace_version,
                    created_at=created_at,
                    chunks=chunks,
                    metadata={"format_version": batch.format_version},
                )
            )
        for path in self._artifact_files(batch):
            try:
                value = json.loads(path.read_text(encoding="utf-8"))
            except (OSError, UnicodeError, json.JSONDecodeError):
                continue
            if isinstance(value, dict):
                records.extend(
                    _entity_records(
                        value,
                        path,
                        document_id=document_id,
                        source_url=source_url,
                        source_hash=source_hash,
                        created_at=created_at,
                        trace_version=trace_version,
                    )
                )
        return tuple(records)

    def _artifact_files(self, batch: ReadBatch) -> tuple[Path, ...]:
        if batch.manifest is not None:
            return tuple(
                path
                for path in batch.files
                if path.suffix.lower() == ".json" and path.name not in SYSTEM_JSON_FILES
            )
        return tuple(
            path
            for path in sorted(batch.path.glob("*.json"))
            if path.name not in SYSTEM_JSON_FILES
        )


def _entity_records(
    artifact: Mapping[str, Any],
    path: Path,
    *,
    document_id: str,
    source_url: str,
    source_hash: str,
    created_at: datetime | None,
    trace_version: str | None,
) -> Iterable[KnowledgeRecord]:
    yielded = False
    for list_name, kind in ENTITY_LIST_KINDS.items():
        values = artifact.get(list_name)
        if not isinstance(values, list):
            continue
        for index, value in enumerate(values):
            if not isinstance(value, dict):
                continue
            yielded = True
            yield _entity_record(
                value,
                kind,
                path,
                document_id=document_id,
                source_url=source_url,
                source_hash=source_hash,
                created_at=created_at,
                trace_version=trace_version,
                index=index,
            )
    if not yielded:
        kind = _kind_from_filename(path.name)
        if kind != "chunk":
            yield _entity_record(
                artifact,
                kind,
                path,
                document_id=document_id,
                source_url=source_url,
                source_hash=source_hash,
                created_at=created_at,
                trace_version=trace_version,
                index=0,
            )


def _entity_record(
    value: Mapping[str, Any],
    kind: str,
    path: Path,
    *,
    document_id: str,
    source_url: str,
    source_hash: str,
    created_at: datetime | None,
    trace_version: str | None,
    index: int,
) -> KnowledgeRecord:
    canonical = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    identifier = str(
        value.get("id")
        or value.get(f"{kind}_id")
        or value.get("knowledge_id")
        or _stable_id("ent", f"{path.name}:{index}", canonical)
    )
    title = str(
        value.get("title")
        or value.get("name")
        or value.get("content_slug")
        or value.get("description")
        or f"{kind} {index + 1}"
    )
    body = _entity_body(value)
    quality = _quality(value)
    targets = _relationship_targets(value.get("relationships"))
    return KnowledgeRecord(
        NoteIdentity(identifier, title, kind),
        source_id=document_id,
        source_url=source_url,
        source_hash=_sha256_text(source_hash + canonical),
        body=body,
        artifact_kind=kind,
        quality=quality,
        trace_version=trace_version,
        created_at=created_at,
        explicit_targets=targets,
        metadata={"artifact_file": path.name},
    )


def _read_object(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {}
    value = json.loads(path.read_text(encoding="utf-8"))
    return dict(value) if isinstance(value, dict) else {}


def _document_text(parsed: Mapping[str, Any]) -> str:
    for key in ("document_text", "clean_text", "content", "text"):
        value = parsed.get(key)
        if isinstance(value, str):
            return value
    return ""


def _extract_chunks(parsed: Mapping[str, Any]) -> tuple[str, ...]:
    chunks = parsed.get("chunks", ())
    if not isinstance(chunks, list):
        return ()
    result: list[str] = []
    for value in chunks:
        text = value.get("text") if isinstance(value, dict) else value
        if isinstance(text, str) and text.strip():
            result.append(text.strip())
    return tuple(result)


def _entity_body(value: Mapping[str, Any]) -> str:
    preferred = ("definition", "description", "content", "template", "action")
    sections: list[str] = []
    for key in preferred:
        item = value.get(key)
        if isinstance(item, str) and item.strip():
            sections.append(item.strip())
    if sections:
        return "\n\n".join(dict.fromkeys(sections))
    return "```json\n" + json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2) + "\n```"


def _quality(*values: Mapping[str, Any]) -> float | None:
    for value in values:
        for key in ("quality", "quality_score", "reliability_score", "confidence"):
            candidate = value.get(key)
            if isinstance(candidate, (int, float)) and not isinstance(candidate, bool):
                return max(0.0, min(1.0, float(candidate)))
    return None


def _relationship_targets(value: Any) -> tuple[str, ...]:
    if not isinstance(value, list):
        return ()
    targets: list[str] = []
    for item in value:
        target = item.get("target_id") if isinstance(item, dict) else item
        if isinstance(target, str) and target and target not in targets:
            targets.append(target)
    return tuple(targets)


def _kind_from_filename(name: str) -> str:
    lowered = name.lower()
    if "chunk" in lowered:
        return "chunk"
    for plural, kind in ENTITY_LIST_KINDS.items():
        if plural in lowered:
            return kind
    return "knowledge"


def _stable_id(prefix: str, first: str, second: str) -> str:
    digest = hashlib.sha256(first.encode("utf-8") + b"\0" + second.encode("utf-8")).hexdigest()
    return f"{prefix}_{digest}"


def _sha256_text(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def _path_datetime(path: Path) -> datetime | None:
    try:
        return datetime.fromtimestamp(path.stat().st_mtime).astimezone()
    except OSError:
        return None
