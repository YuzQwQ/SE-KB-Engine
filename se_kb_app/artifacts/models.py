from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from types import MappingProxyType
from typing import Any, Mapping


MANIFEST_SCHEMA_VERSION = "1.0"


class OutcomeTag(str, Enum):
    SUCCESS = "success"
    NO_KNOWLEDGE = "no_knowledge"
    VALIDATION_FAILED = "validation_failed"
    DEPENDENCY_FAILED = "dependency_failed"
    POLICY_FAILED = "policy_failed"
    CANCELLED = "cancelled"


@dataclass(frozen=True)
class SourceAnchor:
    document_id: str
    start_offset: int
    end_offset: int
    quote_hash: str
    heading_path: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if self.start_offset < 0 or self.end_offset < self.start_offset:
            raise ValueError("source anchor offsets are invalid")


@dataclass(frozen=True)
class ProcessingTrace:
    application_version: str
    cleaner_version: str
    router_version: str
    prompt_version: str
    model_version: str
    parameter_version: str
    schema_version: str


@dataclass(frozen=True)
class DerivedFile:
    path: str
    sha256: str
    bytes: int
    media_type: str = "application/json"


@dataclass(frozen=True)
class ExtractionOutcome:
    tag: OutcomeTag
    artifact_ids: tuple[str, ...] = ()
    diagnostics: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if self.tag is OutcomeTag.SUCCESS and not self.artifact_ids:
            raise ValueError("successful extraction requires at least one artifact")
        if self.tag is not OutcomeTag.SUCCESS and self.artifact_ids:
            raise ValueError("failed or empty outcomes cannot promote artifacts")


@dataclass(frozen=True)
class ArtifactManifest:
    batch_id: str
    document_id: str
    source_url: str
    content_hash: str
    created_at: datetime
    trace: ProcessingTrace
    outcome: ExtractionOutcome
    derived_files: tuple[DerivedFile, ...]
    anchors: tuple[SourceAnchor, ...] = ()
    schema_version: str = MANIFEST_SCHEMA_VERSION
    metadata: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if self.schema_version != MANIFEST_SCHEMA_VERSION:
            raise ValueError("unsupported manifest schema version")
        object.__setattr__(self, "metadata", MappingProxyType(dict(self.metadata)))

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "batch_id": self.batch_id,
            "document_id": self.document_id,
            "source_url": self.source_url,
            "content_hash": self.content_hash,
            "created_at": self.created_at.isoformat(),
            "trace": {
                "application_version": self.trace.application_version,
                "cleaner_version": self.trace.cleaner_version,
                "router_version": self.trace.router_version,
                "prompt_version": self.trace.prompt_version,
                "model_version": self.trace.model_version,
                "parameter_version": self.trace.parameter_version,
                "schema_version": self.trace.schema_version,
            },
            "outcome": {
                "tag": self.outcome.tag.value,
                "artifact_ids": list(self.outcome.artifact_ids),
                "diagnostics": list(self.outcome.diagnostics),
            },
            "derived_files": [
                {
                    "path": item.path,
                    "sha256": item.sha256,
                    "bytes": item.bytes,
                    "media_type": item.media_type,
                }
                for item in self.derived_files
            ],
            "anchors": [
                {
                    "document_id": item.document_id,
                    "start_offset": item.start_offset,
                    "end_offset": item.end_offset,
                    "quote_hash": item.quote_hash,
                    "heading_path": list(item.heading_path),
                }
                for item in self.anchors
            ],
            "metadata": dict(self.metadata),
        }

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> "ArtifactManifest":
        required = {
            "schema_version",
            "batch_id",
            "document_id",
            "source_url",
            "content_hash",
            "created_at",
            "trace",
            "outcome",
            "derived_files",
        }
        missing = required.difference(value)
        if missing:
            raise ValueError(f"manifest missing fields: {', '.join(sorted(missing))}")
        trace = ProcessingTrace(**dict(value["trace"]))
        outcome_value = dict(value["outcome"])
        outcome = ExtractionOutcome(
            OutcomeTag(outcome_value["tag"]),
            tuple(outcome_value.get("artifact_ids", ())),
            tuple(outcome_value.get("diagnostics", ())),
        )
        derived = tuple(DerivedFile(**dict(item)) for item in value["derived_files"])
        anchors = tuple(
            SourceAnchor(
                document_id=item["document_id"],
                start_offset=item["start_offset"],
                end_offset=item["end_offset"],
                quote_hash=item["quote_hash"],
                heading_path=tuple(item.get("heading_path", ())),
            )
            for item in value.get("anchors", ())
        )
        return cls(
            schema_version=str(value["schema_version"]),
            batch_id=str(value["batch_id"]),
            document_id=str(value["document_id"]),
            source_url=str(value["source_url"]),
            content_hash=str(value["content_hash"]),
            created_at=datetime.fromisoformat(str(value["created_at"])),
            trace=trace,
            outcome=outcome,
            derived_files=derived,
            anchors=anchors,
            metadata=dict(value.get("metadata", {})),
        )
