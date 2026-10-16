from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any, Mapping


EXPORT_STATE_SCHEMA_VERSION = "1.0"


@dataclass(frozen=True)
class ExportedNoteState:
    identifier: str
    logical_path: str
    source_hash: str
    published_hash: str
    title: str
    aliases: tuple[str, ...] = ()

    def to_dict(self) -> dict[str, Any]:
        return {
            "identifier": self.identifier,
            "logical_path": self.logical_path,
            "source_hash": self.source_hash,
            "published_hash": self.published_hash,
            "title": self.title,
            "aliases": list(self.aliases),
        }

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> "ExportedNoteState":
        required = {"identifier", "logical_path", "source_hash", "published_hash", "title"}
        missing = required.difference(value)
        if missing:
            raise ValueError(f"exported note state missing fields: {', '.join(sorted(missing))}")
        aliases = value.get("aliases", ())
        if not isinstance(aliases, list) or not all(isinstance(item, str) for item in aliases):
            raise ValueError("exported note aliases must be a string array")
        return cls(
            identifier=_required_string(value["identifier"], "identifier"),
            logical_path=_required_string(value["logical_path"], "logical_path"),
            source_hash=_required_string(value["source_hash"], "source_hash"),
            published_hash=_required_string(value["published_hash"], "published_hash"),
            title=_required_string(value["title"], "title"),
            aliases=tuple(aliases),
        )


@dataclass(frozen=True)
class ExportState:
    vault_name: str
    managed_directory: str
    exported_at: datetime
    corpus_fingerprint: str
    notes: tuple[ExportedNoteState, ...]
    schema_version: str = EXPORT_STATE_SCHEMA_VERSION

    def __post_init__(self) -> None:
        if self.schema_version != EXPORT_STATE_SCHEMA_VERSION:
            raise ValueError("unsupported exporter state schema version")
        identifiers = [note.identifier for note in self.notes]
        if len(identifiers) != len(set(identifiers)):
            raise ValueError("exporter state contains duplicate note identities")

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "vault_name": self.vault_name,
            "managed_directory": self.managed_directory,
            "exported_at": self.exported_at.isoformat(),
            "corpus_fingerprint": self.corpus_fingerprint,
            "notes": [note.to_dict() for note in self.notes],
        }

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> "ExportState":
        required = {
            "schema_version",
            "vault_name",
            "managed_directory",
            "exported_at",
            "corpus_fingerprint",
            "notes",
        }
        missing = required.difference(value)
        if missing:
            raise ValueError(f"exporter state missing fields: {', '.join(sorted(missing))}")
        version = _required_string(value["schema_version"], "schema_version")
        if version != EXPORT_STATE_SCHEMA_VERSION:
            raise ValueError("unsupported exporter state schema version")
        notes = value["notes"]
        if not isinstance(notes, list):
            raise ValueError("exporter state notes must be an array")
        try:
            exported_at = datetime.fromisoformat(_required_string(value["exported_at"], "exported_at"))
        except ValueError as error:
            raise ValueError("exported_at must be an ISO-8601 datetime") from error
        return cls(
            schema_version=version,
            vault_name=_required_string(value["vault_name"], "vault_name"),
            managed_directory=_required_string(value["managed_directory"], "managed_directory"),
            exported_at=exported_at,
            corpus_fingerprint=_required_string(value["corpus_fingerprint"], "corpus_fingerprint"),
            notes=tuple(ExportedNoteState.from_dict(item) for item in notes),
        )


def _required_string(value: Any, name: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{name} must be a non-empty string")
    return value

