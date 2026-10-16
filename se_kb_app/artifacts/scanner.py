from __future__ import annotations

import hashlib
import json
from collections import Counter, defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from se_kb_app.artifacts.models import ArtifactManifest


@dataclass(frozen=True)
class IntegrityIssue:
    kind: str
    path: str
    relationship: str
    message: str


@dataclass(frozen=True)
class IntegrityReport:
    root: str
    files_scanned: int
    json_files: int
    versions: dict[str, int]
    issues: tuple[IntegrityIssue, ...]
    duplicate_groups: tuple[tuple[str, ...], ...]

    @property
    def valid(self) -> bool:
        return not self.issues

    def to_dict(self) -> dict[str, Any]:
        return {
            "root": self.root,
            "files_scanned": self.files_scanned,
            "json_files": self.json_files,
            "versions": dict(self.versions),
            "valid": self.valid,
            "issues": [
                {
                    "kind": issue.kind,
                    "path": issue.path,
                    "relationship": issue.relationship,
                    "message": issue.message,
                }
                for issue in self.issues
            ],
            "duplicate_groups": [list(group) for group in self.duplicate_groups],
        }

    def to_text(self) -> str:
        lines = [
            f"Artifact integrity scan: {self.root}",
            f"Files: {self.files_scanned}; JSON: {self.json_files}; valid: {self.valid}",
            "Versions: " + ", ".join(f"{key}={value}" for key, value in sorted(self.versions.items())),
            f"Issues: {len(self.issues)}; duplicate groups: {len(self.duplicate_groups)}",
        ]
        lines.extend(f"- [{issue.kind}] {issue.path}: {issue.message}" for issue in self.issues)
        return "\n".join(lines)


class IntegrityScanner:
    def scan(self, root: Path) -> IntegrityReport:
        resolved = root.resolve()
        files = sorted(path for path in resolved.rglob("*") if path.is_file())
        issues: list[IntegrityIssue] = []
        versions: Counter[str] = Counter()
        hashes: dict[str, list[str]] = defaultdict(list)
        content_ids: dict[str, list[str]] = defaultdict(list)
        json_count = 0
        for path in files:
            relative = path.relative_to(resolved).as_posix()
            if path.suffix.lower() == ".json":
                json_count += 1
                digest = _hash_file(path)
                hashes[digest].append(relative)
                try:
                    value = json.loads(path.read_text(encoding="utf-8"))
                except (OSError, UnicodeError, json.JSONDecodeError) as error:
                    issues.append(IntegrityIssue("corrupt_json", relative, "standalone", type(error).__name__))
                    continue
                if path.name == "manifest.json":
                    content_hash = self._scan_manifest(path, relative, value, issues, versions)
                    if content_hash:
                        content_ids[content_hash].append(relative)
                elif path.name in {"metadata.json", "parsed.json"}:
                    versions["legacy-0"] += 1
            if path.suffix.lower() == ".tmp" or "orphan" in path.parts:
                issues.append(IntegrityIssue("orphan_candidate", relative, "unreferenced", "File has no committed manifest relationship."))
        duplicate_groups = tuple(
            tuple(paths)
            for paths in sorted([*hashes.values(), *content_ids.values()])
            if len(paths) > 1
        )
        return IntegrityReport(
            str(resolved),
            len(files),
            json_count,
            dict(versions),
            tuple(issues),
            duplicate_groups,
        )

    def _scan_manifest(self, path, relative, value, issues, versions) -> str | None:
        try:
            manifest = ArtifactManifest.from_dict(value)
        except (TypeError, ValueError, KeyError) as error:
            issues.append(IntegrityIssue("invalid_manifest", relative, "manifest", str(error)))
            return None
        versions[manifest.schema_version] += 1
        for derived in manifest.derived_files:
            target = path.parent / derived.path
            relationship = f"manifest:{relative}"
            if not target.is_file():
                issues.append(IntegrityIssue("missing_file", target.as_posix(), relationship, "Referenced derived file is missing."))
                continue
            actual_bytes = target.stat().st_size
            actual_hash = _hash_file(target)
            if actual_bytes != derived.bytes:
                issues.append(IntegrityIssue("size_mismatch", target.as_posix(), relationship, "Recorded byte length does not match."))
            if actual_hash != derived.sha256:
                issues.append(IntegrityIssue("hash_mismatch", target.as_posix(), relationship, "Recorded SHA-256 does not match."))
        return manifest.content_hash


def _hash_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        while chunk := stream.read(1024 * 1024):
            digest.update(chunk)
    return digest.hexdigest()
