from __future__ import annotations

import hashlib
import json
import os
import shutil
import threading
from dataclasses import asdict, dataclass
from enum import Enum
from pathlib import Path
from typing import Any, Mapping, Sequence

from .models import EvaluationDocument
from se_kb_app.observability import METRICS

INDEX_SCHEMA_VERSION = "1.0"


class BuildMode(str, Enum):
    FULL = "full"
    INCREMENTAL = "incremental"
    VALIDATE_ONLY = "validate-only"
    DRY_RUN = "dry-run"


class IndexCompatibilityError(ValueError):
    pass


@dataclass(frozen=True)
class IndexManifest:
    index_id: str
    source_manifest: str
    chunker_version: str
    embedding_model: str
    embedding_dimension: int
    normalization: str
    distance_metric: str
    collection_mapping: Mapping[str, str]
    schema_version: str = INDEX_SCHEMA_VERSION

    @property
    def fingerprint(self) -> str:
        payload = json.dumps(asdict(self), sort_keys=True, separators=(",", ":"))
        return hashlib.sha256(payload.encode()).hexdigest()

    def ensure_compatible(self, expected: "IndexManifest") -> None:
        fields = (
            "source_manifest",
            "chunker_version",
            "embedding_model",
            "embedding_dimension",
            "normalization",
            "distance_metric",
            "collection_mapping",
            "schema_version",
        )
        mismatches = [field for field in fields if getattr(self, field) != getattr(expected, field)]
        if mismatches:
            raise IndexCompatibilityError(
                "incompatible index fields: " + ", ".join(mismatches) + "; rebuild into a new target"
            )

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> "IndexManifest":
        return cls(
            index_id=str(value["index_id"]),
            source_manifest=str(value["source_manifest"]),
            chunker_version=str(value["chunker_version"]),
            embedding_model=str(value["embedding_model"]),
            embedding_dimension=int(value["embedding_dimension"]),
            normalization=str(value["normalization"]),
            distance_metric=str(value["distance_metric"]),
            collection_mapping={str(key): str(item) for key, item in dict(value["collection_mapping"]).items()},
            schema_version=str(value["schema_version"]),
        )


@dataclass(frozen=True)
class BuildReport:
    mode: BuildMode
    target: str
    planned_records: int
    stale_removed: tuple[str, ...]
    valid: bool | None
    switched: bool
    previous_index: str | None


class IndexManager:
    def __init__(self, root: Path) -> None:
        self.root = root.resolve()
        self.pointer = self.root / "active-index.json"
        self._lock = threading.RLock()

    def build(
        self,
        manifest: IndexManifest,
        documents: Sequence[EvaluationDocument],
        *,
        mode: BuildMode,
        switch: bool = False,
        minimum_free_bytes: int = 0,
        fail_after_records: int | None = None,
    ) -> BuildReport:
        target = self.root / manifest.index_id
        previous = self.active_index_id()
        old_ids = set(self._read_records(previous)) if previous else set()
        new_records = {document.id: _document_record(document) for document in documents}
        stale = tuple(sorted(old_ids.difference(new_records)))
        if mode is BuildMode.DRY_RUN:
            METRICS.increment("index_builds_total", mode=mode.value, outcome="planned")
            return BuildReport(mode, str(target), len(new_records), stale, None, False, previous)
        if mode is BuildMode.VALIDATE_ONLY:
            valid = self.validate(target, expected=manifest)
            METRICS.increment("index_builds_total", mode=mode.value, outcome="valid" if valid else "invalid")
            return BuildReport(mode, str(target), len(new_records), stale, valid, False, previous)
        if target.exists() and any(target.iterdir()):
            raise ValueError("build target must be absent or empty")
        estimated = len(json.dumps(new_records, ensure_ascii=False).encode("utf-8")) * 2
        probe = self.root if self.root.exists() else self.root.parent
        if shutil.disk_usage(probe).free < max(minimum_free_bytes, estimated):
            raise OSError("insufficient disk space for isolated index build")
        target.mkdir(parents=True, exist_ok=True)
        invalid = target / "INVALID"
        _atomic_write(invalid, b"build incomplete")
        try:
            serializable: dict[str, Any] = {}
            for position, (item_id, record) in enumerate(sorted(new_records.items()), 1):
                if fail_after_records is not None and position > fail_after_records:
                    raise OSError("injected index build failure")
                serializable[item_id] = record
            _atomic_write(
                target / "records.json",
                json.dumps(serializable, ensure_ascii=False, sort_keys=True).encode("utf-8"),
            )
            _atomic_write(
                target / "manifest.json",
                json.dumps(asdict(manifest), ensure_ascii=False, sort_keys=True).encode("utf-8"),
            )
            invalid.unlink()
            if not self.validate(target, expected=manifest):
                raise ValueError("post-build index validation failed")
            switched = False
            if switch:
                self.switch(manifest.index_id, expected=manifest)
                switched = True
            METRICS.increment("index_builds_total", mode=mode.value, outcome="succeeded")
            METRICS.gauge("index_records", len(new_records), schema=manifest.schema_version)
            return BuildReport(mode, str(target), len(new_records), stale, True, switched, previous)
        except Exception:
            METRICS.increment("index_builds_total", mode=mode.value, outcome="failed")
            if not invalid.exists():
                _atomic_write(invalid, b"build invalidated after failure")
            raise

    def validate(self, target: Path, *, expected: IndexManifest | None = None) -> bool:
        if (target / "INVALID").exists():
            return False
        try:
            value = json.loads((target / "manifest.json").read_text(encoding="utf-8"))
            manifest = IndexManifest.from_dict(value)
            if manifest.schema_version != INDEX_SCHEMA_VERSION:
                return False
            if expected:
                manifest.ensure_compatible(expected)
            records = json.loads((target / "records.json").read_text(encoding="utf-8"))
            return isinstance(records, dict)
        except (OSError, ValueError, KeyError, json.JSONDecodeError, IndexCompatibilityError):
            return False

    def switch(self, index_id: str, *, expected: IndexManifest | None = None) -> None:
        target = self.root / index_id
        if not self.validate(target, expected=expected):
            raise ValueError("cannot activate an invalid or incompatible index")
        with self._lock:
            self.root.mkdir(parents=True, exist_ok=True)
            _atomic_write(self.pointer, json.dumps({"index_id": index_id}).encode("utf-8"))

    def active_index_id(self) -> str | None:
        with self._lock:
            try:
                return str(json.loads(self.pointer.read_text(encoding="utf-8"))["index_id"])
            except (OSError, KeyError, ValueError, json.JSONDecodeError):
                return None

    def load_active(self, *, expected: IndexManifest | None = None) -> dict[str, Any]:
        with self._lock:
            index_id = self.active_index_id()
            if not index_id:
                raise ValueError("no active index")
            target = self.root / index_id
            if not self.validate(target, expected=expected):
                raise IndexCompatibilityError("active index is invalid or incompatible; rebuild and switch")
            return json.loads((target / "records.json").read_text(encoding="utf-8"))

    def _read_records(self, index_id: str) -> dict[str, Any]:
        if not index_id:
            return {}
        try:
            value = json.loads((self.root / index_id / "records.json").read_text(encoding="utf-8"))
            return value if isinstance(value, dict) else {}
        except (OSError, json.JSONDecodeError):
            return {}


def _document_record(document: EvaluationDocument) -> dict[str, Any]:
    return {
        "source_id": document.id,
        "parent_id": document.parent_id,
        "text": document.text,
        "metadata": {
            "source": document.source,
            "kind": document.kind,
            "date": document.date,
            "quality": document.quality,
            **dict(document.metadata),
        },
    }


def _atomic_write(path: Path, payload: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.{os.getpid()}.tmp")
    try:
        with temporary.open("wb") as stream:
            stream.write(payload)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, path)
    finally:
        if temporary.exists():
            temporary.unlink()
