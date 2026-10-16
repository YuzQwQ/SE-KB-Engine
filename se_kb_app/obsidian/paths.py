from __future__ import annotations

import hashlib
import os
import re
import unicodedata
from dataclasses import dataclass
from pathlib import Path, PurePosixPath
from typing import Iterable

from se_kb_app.obsidian.models import NoteIdentity, VaultAvailability, VaultStatus
from se_kb_app.settings import ObsidianSettings


WINDOWS_RESERVED_NAMES = {
    "CON",
    "PRN",
    "AUX",
    "NUL",
    *(f"COM{number}" for number in range(1, 10)),
    *(f"LPT{number}" for number in range(1, 10)),
}
CONTROL_CHARACTERS = re.compile(r"[\x00-\x1f\x7f]")
INVALID_FILENAME_CHARACTERS = re.compile(r'[<>:"/\\|?*\[\]#^]')
SEPARATOR_RUN = re.compile(r"[-\s_]+")


def sanitize_note_title(value: str, *, maximum: int = 96) -> str:
    normalized = unicodedata.normalize("NFKC", value).strip()
    normalized = CONTROL_CHARACTERS.sub("", normalized)
    normalized = INVALID_FILENAME_CHARACTERS.sub("-", normalized)
    normalized = SEPARATOR_RUN.sub("-", normalized).strip(" .-_")
    if not normalized:
        normalized = "untitled"
    if normalized.split(".", 1)[0].upper() in WINDOWS_RESERVED_NAMES:
        normalized = f"note-{normalized}"
    normalized = normalized[:maximum].rstrip(" .-_") or "untitled"
    return normalized


def stable_note_suffix(identifier: str, *, length: int = 10) -> str:
    if not identifier.strip():
        raise ValueError("note identifier must be non-empty")
    return hashlib.sha256(identifier.encode("utf-8")).hexdigest()[:length]


def build_note_path_map(
    identities: Iterable[NoteIdentity],
    *,
    maximum_component: int = 96,
    maximum_path: int = 220,
) -> dict[str, str]:
    result: dict[str, str] = {}
    folded_paths: set[str] = set()
    for identity in sorted(identities, key=lambda item: item.identifier):
        if identity.identifier in result:
            raise ValueError(f"duplicate note identity: {identity.identifier}")
        category = "Sources" if identity.kind == "source" else f"Knowledge/{sanitize_note_title(identity.kind, maximum=32)}"
        suffix = stable_note_suffix(identity.identifier)
        budget = min(maximum_component, max(8, maximum_path - len(category) - len(suffix) - 7))
        slug = sanitize_note_title(identity.title, maximum=budget)
        logical = f"{category}/{slug}--{suffix}.md"
        folded = unicodedata.normalize("NFKC", logical).casefold()
        if folded in folded_paths:
            extended = stable_note_suffix(identity.identifier, length=16)
            logical = f"{category}/{slug}--{extended}.md"
            folded = unicodedata.normalize("NFKC", logical).casefold()
        if folded in folded_paths or len(logical) > maximum_path:
            raise ValueError(f"unable to create a bounded unique path for {identity.identifier}")
        folded_paths.add(folded)
        result[identity.identifier] = logical
    return result


@dataclass(frozen=True)
class VaultPathPolicy:
    vault_root: Path
    managed_root: Path

    @classmethod
    def from_settings(cls, settings: ObsidianSettings) -> "VaultPathPolicy":
        if settings.vault_root is None:
            raise ValueError("Obsidian Vault is not configured")
        vault_root = settings.vault_root.resolve()
        managed_relative = _validated_relative(settings.managed_directory, allow_markdown=False)
        managed_root = vault_root.joinpath(*managed_relative.parts).resolve()
        _require_contained(vault_root, managed_root, allow_same=False)
        return cls(vault_root, managed_root)

    def destination(self, logical_path: str, *, require_parent: bool = False) -> Path:
        relative = _validated_relative(logical_path, allow_markdown=True)
        candidate = self.managed_root.joinpath(*relative.parts)
        parent = candidate.parent.resolve(strict=False)
        _require_contained(self.managed_root, parent, allow_same=True)
        if require_parent and not parent.is_dir():
            raise ValueError("destination parent is unavailable")
        resolved = candidate.resolve(strict=False)
        _require_contained(self.managed_root, resolved, allow_same=False)
        return candidate

    def revalidate_destination(self, logical_path: str) -> Path:
        destination = self.destination(logical_path, require_parent=True)
        parent = destination.parent.resolve(strict=True)
        _require_contained(self.managed_root.resolve(strict=True), parent, allow_same=True)
        if destination.exists() and destination.is_symlink():
            raise ValueError("destination cannot be a symbolic link")
        return destination


def inspect_vault(settings: ObsidianSettings) -> VaultStatus:
    if not settings.enabled:
        return VaultStatus(
            VaultAvailability.NOT_CONFIGURED,
            configured=False,
            available=False,
            vault_name=settings.vault_name,
            managed_directory=settings.managed_directory,
            diagnostic="vault_not_configured",
        )
    root = settings.vault_root
    assert root is not None
    if not root.exists() or not root.is_dir():
        return VaultStatus(
            VaultAvailability.UNAVAILABLE,
            configured=True,
            available=False,
            vault_name=settings.vault_name or root.name,
            managed_directory=settings.managed_directory,
            diagnostic="vault_unavailable",
        )
    if not os.access(root, os.R_OK):
        availability = VaultAvailability.UNAVAILABLE
        diagnostic = "vault_unreadable"
    elif not os.access(root, os.W_OK):
        availability = VaultAvailability.READ_ONLY
        diagnostic = "vault_read_only"
    else:
        availability = VaultAvailability.READY
        diagnostic = None
    return VaultStatus(
        availability,
        configured=True,
        available=availability is VaultAvailability.READY,
        vault_name=settings.vault_name or root.name,
        managed_directory=settings.managed_directory,
        diagnostic=diagnostic,
    )


def _validated_relative(value: str, *, allow_markdown: bool) -> PurePosixPath:
    if not isinstance(value, str) or not value or CONTROL_CHARACTERS.search(value):
        raise ValueError("path must be a printable relative path")
    normalized = value.replace("\\", "/")
    path = PurePosixPath(normalized)
    if path.is_absolute() or any(part in {"", ".", ".."} for part in path.parts):
        raise ValueError("path must be bounded and relative")
    if ":" in path.parts[0]:
        raise ValueError("drive-qualified paths are not allowed")
    if allow_markdown and path.suffix.lower() not in {".md", ".canvas"}:
        raise ValueError("managed output must be Markdown or Canvas")
    return path


def _require_contained(root: Path, candidate: Path, *, allow_same: bool) -> None:
    if candidate == root:
        if allow_same:
            return
        raise ValueError("destination must be below the managed root")
    if root not in candidate.parents:
        raise ValueError("destination escapes the managed root")

