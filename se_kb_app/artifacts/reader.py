from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

from se_kb_app.artifacts.models import ArtifactManifest


@dataclass(frozen=True)
class ReadBatch:
    path: Path
    format_version: str
    manifest: ArtifactManifest | None
    source_url: str
    files: tuple[Path, ...]


class ArtifactReader:
    def read(self, path: Path) -> ReadBatch:
        directory = path if path.is_dir() else path.parent
        manifest_path = directory / "manifest.json"
        if manifest_path.is_file():
            value = json.loads(manifest_path.read_text(encoding="utf-8"))
            manifest = ArtifactManifest.from_dict(value)
            return ReadBatch(
                directory,
                manifest.schema_version,
                manifest,
                manifest.source_url,
                tuple(directory / item.path for item in manifest.derived_files),
            )
        metadata_path = directory / "metadata.json"
        parsed_path = directory / "parsed.json"
        if metadata_path.is_file() or parsed_path.is_file():
            source = metadata_path if metadata_path.is_file() else parsed_path
            value = json.loads(source.read_text(encoding="utf-8"))
            source_url = str(value.get("source_url") or value.get("url") or "")
            files = tuple(sorted(directory.glob("*.json")))
            return ReadBatch(directory, "legacy-0", None, source_url, files)
        raise ValueError("unsupported artifact directory")
