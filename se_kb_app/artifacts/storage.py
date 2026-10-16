from __future__ import annotations

import hashlib
import json
import os
import re
import tempfile
from collections.abc import Callable, Mapping
from pathlib import Path
from typing import Any

from se_kb_app.artifacts.models import ArtifactManifest, DerivedFile


def safe_component(value: str, *, maximum: int = 80) -> str:
    normalized = re.sub(r"[^\w.-]+", "-", value.strip(), flags=re.UNICODE).strip(" .-")
    normalized = normalized[:maximum].rstrip(" .-")
    return normalized or "untitled"


def atomic_write_bytes(
    destination: Path,
    payload: bytes,
    *,
    replace: Callable[[str, str], None] = os.replace,
) -> None:
    destination.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary_name = tempfile.mkstemp(
        prefix=f".{destination.name}.", suffix=".tmp", dir=destination.parent
    )
    try:
        with os.fdopen(descriptor, "wb") as stream:
            stream.write(payload)
            stream.flush()
            os.fsync(stream.fileno())
        replace(temporary_name, str(destination))
    except BaseException:
        try:
            Path(temporary_name).unlink(missing_ok=True)
        finally:
            raise


def atomic_write_json(destination: Path, value: Mapping[str, Any], **kwargs: Any) -> None:
    payload = json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2).encode("utf-8") + b"\n"
    atomic_write_bytes(destination, payload, **kwargs)


class ArtifactPublisher:
    def __init__(self, root: Path) -> None:
        self.root = root.resolve()

    def publish(
        self,
        manifest: ArtifactManifest,
        files: Mapping[str, bytes],
        *,
        failure_after_files: int | None = None,
    ) -> Path:
        batch = self.root / safe_component(manifest.batch_id)
        batch.mkdir(parents=True, exist_ok=True)
        expected = {item.path: item for item in manifest.derived_files}
        if set(files) != set(expected):
            raise ValueError("derived files do not match the manifest")
        for index, (relative, payload) in enumerate(sorted(files.items()), 1):
            destination = self._destination(batch, relative)
            recorded = expected[relative]
            if hashlib.sha256(payload).hexdigest() != recorded.sha256 or len(payload) != recorded.bytes:
                raise ValueError(f"derived file integrity mismatch: {relative}")
            atomic_write_bytes(destination, payload)
            if failure_after_files is not None and index >= failure_after_files:
                raise OSError("injected publication failure")
        manifest_path = batch / "manifest.json"
        atomic_write_json(manifest_path, manifest.to_dict())
        return manifest_path

    def _destination(self, batch: Path, relative: str) -> Path:
        parts = Path(relative).parts
        if not parts or Path(relative).is_absolute() or any(part in {"", ".", ".."} for part in parts):
            raise ValueError("derived path must be bounded and relative")
        destination = batch.joinpath(*parts).resolve()
        if batch != destination and batch not in destination.parents:
            raise ValueError("derived path escapes the batch")
        return destination


def derived_file(path: str, payload: bytes, media_type: str = "application/json") -> DerivedFile:
    return DerivedFile(path, hashlib.sha256(payload).hexdigest(), len(payload), media_type)
