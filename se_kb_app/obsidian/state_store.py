from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

from se_kb_app.artifacts.storage import atomic_write_json
from se_kb_app.obsidian.paths import VaultPathPolicy
from se_kb_app.obsidian.state import ExportState


STATE_FILE_NAME = ".se-kb-export-state-v1.json"


@dataclass(frozen=True)
class StateLoadResult:
    state: ExportState | None
    diagnostic: str | None = None
    read_only: bool = False


class ExportStateStore:
    def __init__(self, policy: VaultPathPolicy) -> None:
        self.policy = policy

    @property
    def path(self) -> Path:
        return self.policy.managed_root / STATE_FILE_NAME

    def load(self) -> StateLoadResult:
        path = self.path
        if not path.exists():
            return StateLoadResult(None)
        try:
            value = json.loads(path.read_text(encoding="utf-8"))
            if not isinstance(value, dict):
                raise ValueError("exporter state root must be an object")
            return StateLoadResult(ExportState.from_dict(value))
        except json.JSONDecodeError:
            return StateLoadResult(None, "export_state_corrupt", read_only=True)
        except (OSError, UnicodeError):
            return StateLoadResult(None, "export_state_unreadable", read_only=True)
        except ValueError as error:
            diagnostic = (
                "export_state_newer_version"
                if "unsupported exporter state schema version" in str(error)
                else "export_state_invalid"
            )
            return StateLoadResult(None, diagnostic, read_only=True)

    def save(self, state: ExportState) -> None:
        self.policy.managed_root.mkdir(parents=True, exist_ok=True)
        resolved_root = self.policy.managed_root.resolve(strict=True)
        resolved_parent = self.path.parent.resolve(strict=True)
        if resolved_root != resolved_parent:
            raise ValueError("export state destination escapes the managed root")
        atomic_write_json(self.path, state.to_dict())

