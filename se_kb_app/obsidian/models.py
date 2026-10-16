from __future__ import annotations

from collections import Counter
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from types import MappingProxyType
from typing import Any, Mapping


class VaultAvailability(str, Enum):
    NOT_CONFIGURED = "not_configured"
    UNAVAILABLE = "unavailable"
    READY = "ready"
    READ_ONLY = "read_only"


class RelationshipKind(str, Enum):
    EXPLICIT = "explicit"
    SEMANTIC = "semantic"


class ExportAction(str, Enum):
    CREATE = "create"
    UPDATE = "update"
    RENAME = "rename"
    UNCHANGED = "unchanged"
    CONFLICT = "conflict"
    SKIPPED = "skipped"
    STALE = "stale"


@dataclass(frozen=True)
class VaultStatus:
    availability: VaultAvailability
    configured: bool
    available: bool
    vault_name: str | None
    managed_directory: str
    managed_notes: int = 0
    conflicts: int = 0
    stale: int = 0
    last_exported_at: datetime | None = None
    corpus_fingerprint: str | None = None
    diagnostic: str | None = None


@dataclass(frozen=True, order=True)
class NoteIdentity:
    identifier: str
    title: str
    kind: str

    def __post_init__(self) -> None:
        if not self.identifier.strip() or not self.title.strip() or not self.kind.strip():
            raise ValueError("note identity fields must be non-empty")


@dataclass(frozen=True)
class RelationshipEdge:
    source_id: str
    target_id: str
    relation: str
    kind: RelationshipKind
    score: float | None = None
    method: str | None = None
    index_version: str | None = None
    metadata: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.source_id or not self.target_id or not self.relation:
            raise ValueError("relationship identifiers and relation must be non-empty")
        if self.kind is RelationshipKind.SEMANTIC:
            if self.score is None or not 0 <= self.score <= 1 or not self.method:
                raise ValueError("semantic relationships require score and method")
        object.__setattr__(self, "metadata", MappingProxyType(dict(self.metadata)))


@dataclass(frozen=True)
class ProjectedNote:
    identity: NoteIdentity
    logical_path: str
    source_id: str
    source_url: str
    source_hash: str
    content_hash: str
    markdown: str
    quality: float | None = None
    trace_version: str | None = None
    aliases: tuple[str, ...] = ()
    explicit_links: tuple[str, ...] = ()
    semantic_links: tuple[str, ...] = ()
    metadata: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.logical_path.endswith((".md", ".canvas")):
            raise ValueError("projected Vault files require a Markdown or Canvas logical path")
        if not self.source_id or not self.source_hash or not self.content_hash:
            raise ValueError("projected note identity hashes must be non-empty")
        if self.quality is not None and not 0 <= self.quality <= 1:
            raise ValueError("projected note quality must be between 0 and 1")
        object.__setattr__(self, "metadata", MappingProxyType(dict(self.metadata)))


@dataclass(frozen=True)
class PlannedNote:
    action: ExportAction
    identifier: str
    logical_path: str
    reason: str
    previous_path: str | None = None
    note: ProjectedNote | None = None


@dataclass(frozen=True)
class ExportPlan:
    corpus_fingerprint: str
    actions: tuple[PlannedNote, ...]
    total_actions: int
    offset: int = 0
    limit: int = 100
    partial: bool = False
    diagnostics: tuple[str, ...] = ()
    action_counts: Mapping[str, int] = field(default_factory=dict)

    def __post_init__(self) -> None:
        object.__setattr__(self, "action_counts", MappingProxyType(dict(self.action_counts)))

    @property
    def counts(self) -> Mapping[str, int]:
        if self.action_counts:
            return self.action_counts
        return MappingProxyType(dict(Counter(item.action.value for item in self.actions)))


@dataclass(frozen=True)
class ExportResult:
    corpus_fingerprint: str
    published_at: datetime
    counts: Mapping[str, int]
    logical_paths: tuple[str, ...] = ()
    conflicts: tuple[str, ...] = ()
    skipped: tuple[str, ...] = ()
    diagnostics: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        object.__setattr__(self, "counts", MappingProxyType(dict(self.counts)))
