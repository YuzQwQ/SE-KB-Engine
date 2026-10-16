from __future__ import annotations

import json
from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from se_kb_app.artifacts.identity import artifact_id, content_id, document_id
from se_kb_app.artifacts.models import ArtifactManifest, ExtractionOutcome, OutcomeTag, ProcessingTrace
from se_kb_app.artifacts.reader import ArtifactReader
from se_kb_app.artifacts.scanner import IntegrityScanner
from se_kb_app.artifacts.storage import ArtifactPublisher, derived_file, safe_component


@dataclass(frozen=True)
class MigrationItem:
    source: str
    target: str
    status: str
    message: str = ""


@dataclass(frozen=True)
class MigrationReport:
    dry_run: bool
    source_root: str
    target_root: str
    preflight_errors: tuple[str, ...]
    items: tuple[MigrationItem, ...]
    backup_mapping: tuple[tuple[str, str], ...]
    post_validation_valid: bool | None
    rollback_instructions: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "dry_run": self.dry_run,
            "source_root": self.source_root,
            "target_root": self.target_root,
            "preflight_errors": list(self.preflight_errors),
            "items": [item.__dict__ for item in self.items],
            "backup_mapping": [
                {"source": source, "target": target} for source, target in self.backup_mapping
            ],
            "post_validation_valid": self.post_validation_valid,
            "rollback_instructions": self.rollback_instructions,
        }


class ArtifactMigrator:
    def __init__(self, *, clock: Callable[[], datetime] | None = None) -> None:
        self.clock = clock or (lambda: datetime.now(timezone.utc))
        self.reader = ArtifactReader()

    def migrate(self, source_root: Path, target_root: Path, *, dry_run: bool = True) -> MigrationReport:
        source = source_root.resolve()
        target = target_root.resolve()
        errors = self._preflight(source, target)
        directories = sorted(
            {path.parent for name in ("metadata.json", "parsed.json") for path in source.rglob(name)}
        ) if source.is_dir() else []
        items: list[MigrationItem] = []
        mappings: list[tuple[str, str]] = []
        for directory in directories:
            try:
                batch = self.reader.read(directory)
                content_payload = (directory / "parsed.json").read_bytes() if (directory / "parsed.json").is_file() else b""
                content_hash = content_id(content_payload)
                doc_id = document_id(batch.source_url, content_hash)
                batch_name = safe_component(f"{directory.name}-{doc_id[4:16]}")
                destination = target / batch_name
                mappings.append((str(directory), str(destination)))
                if errors:
                    items.append(MigrationItem(str(directory), str(destination), "blocked", errors[0]))
                elif dry_run:
                    items.append(MigrationItem(str(directory), str(destination), "planned"))
                else:
                    self._write_batch(batch.files, destination, batch_name, doc_id, batch.source_url, content_hash)
                    items.append(MigrationItem(str(directory), str(destination), "migrated"))
            except (OSError, ValueError, json.JSONDecodeError) as error:
                items.append(MigrationItem(str(directory), "", "unsupported", type(error).__name__))
        post_valid = None
        if not dry_run and not errors:
            post_valid = IntegrityScanner().scan(target).valid
        return MigrationReport(
            dry_run,
            str(source),
            str(target),
            tuple(errors),
            tuple(items),
            tuple(mappings),
            post_valid,
            f"Rollback by removing only the new target '{target}'. The source remains authoritative and unchanged.",
        )

    def _write_batch(self, files, destination, batch_name, doc_id, source_url, content_hash) -> None:
        payloads = {f"legacy/{path.name}": path.read_bytes() for path in files}
        artifact_ids = tuple(
            artifact_id(doc_id, path, {"content_hash": content_id(payload)})
            for path, payload in sorted(payloads.items())
        )
        manifest = ArtifactManifest(
            batch_id=batch_name,
            document_id=doc_id,
            source_url=source_url,
            content_hash=content_hash,
            created_at=self.clock(),
            trace=ProcessingTrace(
                "0.1.0", "legacy-preserved", "legacy-observed", "not-applicable",
                "not-applicable", "migration-v1", "legacy-json",
            ),
            outcome=ExtractionOutcome(OutcomeTag.SUCCESS, artifact_ids),
            derived_files=tuple(derived_file(path, payload) for path, payload in sorted(payloads.items())),
            metadata={"migration": "copy-only", "legacy_source": str(files[0].parent) if files else ""},
        )
        ArtifactPublisher(destination.parent).publish(manifest, payloads)

    @staticmethod
    def _preflight(source: Path, target: Path) -> list[str]:
        errors: list[str] = []
        if not source.is_dir():
            errors.append("source root does not exist")
        if source == target or source in target.parents:
            errors.append("target must not be the source or nested inside it")
        if target.exists() and any(target.iterdir()):
            errors.append("target must be absent or empty")
        return errors
