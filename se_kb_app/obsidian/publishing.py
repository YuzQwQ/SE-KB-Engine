from __future__ import annotations

import hashlib
import os
import tempfile
import threading
from collections import Counter
from collections.abc import Callable
from datetime import datetime, timezone
from pathlib import Path

from se_kb_app.domain import Cancellation
from se_kb_app.obsidian.models import ExportAction, ExportPlan, ExportResult, PlannedNote
from se_kb_app.obsidian.paths import VaultPathPolicy
from se_kb_app.obsidian.planning import hash_file
from se_kb_app.obsidian.state import ExportState, ExportedNoteState
from se_kb_app.obsidian.state_store import ExportStateStore


class VaultBusyError(RuntimeError):
    pass


class VaultPublisher:
    _registry_guard = threading.Lock()
    _locks: dict[str, threading.Lock] = {}

    def __init__(
        self,
        policy: VaultPathPolicy,
        state_store: ExportStateStore,
        *,
        replace: Callable[[str, str], None] = os.replace,
        stage_hook: Callable[[str, PlannedNote | None], None] | None = None,
    ) -> None:
        self.policy = policy
        self.state_store = state_store
        self.replace = replace
        self.stage_hook = stage_hook or (lambda _stage, _item: None)

    def publish(
        self,
        plan: ExportPlan,
        *,
        vault_name: str,
        previous: ExportState | None = None,
        cancellation: Cancellation | None = None,
    ) -> ExportResult:
        if plan.partial:
            raise ValueError("cannot publish a partial export plan")
        lock = self._lock_for_root()
        if not lock.acquire(blocking=False):
            raise VaultBusyError("Vault export is already active")
        try:
            return self._publish_locked(
                plan,
                vault_name=vault_name,
                previous=previous,
                cancellation=cancellation,
            )
        finally:
            lock.release()

    def _publish_locked(
        self,
        plan: ExportPlan,
        *,
        vault_name: str,
        previous: ExportState | None,
        cancellation: Cancellation | None,
    ) -> ExportResult:
        self.policy.managed_root.mkdir(parents=True, exist_ok=True)
        self.cleanup_temporary_files()
        state_by_id = {item.identifier: item for item in previous.notes} if previous else {}
        published_paths: list[str] = []
        conflicts: list[str] = []
        skipped: list[str] = []
        actual_counts: Counter[str] = Counter()
        for item in plan.actions:
            self._checkpoint(cancellation)
            self.stage_hook("before_item", item)
            actual_counts[item.action.value] += 1
            if item.action is ExportAction.CONFLICT:
                conflicts.append(item.logical_path)
                continue
            if item.action in {ExportAction.SKIPPED, ExportAction.STALE}:
                skipped.append(item.logical_path)
                continue
            if item.action is ExportAction.UNCHANGED:
                if item.note is not None:
                    state_by_id[item.identifier] = self._note_state(item.note)
                continue
            if item.note is None:
                raise ValueError("publishable action is missing projected note content")
            destination = self.policy.destination(item.logical_path)
            destination.parent.mkdir(parents=True, exist_ok=True)
            destination = self.policy.revalidate_destination(item.logical_path)
            self._checkpoint(cancellation)
            self.stage_hook("before_write", item)
            temporary = self._write_temporary(destination, item.note.markdown.encode("utf-8"))
            try:
                self._checkpoint(cancellation)
                destination = self.policy.revalidate_destination(item.logical_path)
                self.stage_hook("before_replace", item)
                self.replace(str(temporary), str(destination))
            finally:
                temporary.unlink(missing_ok=True)
            if hash_file(destination) != item.note.content_hash:
                raise OSError("published note hash verification failed")
            if item.action is ExportAction.RENAME and item.previous_path:
                self._remove_previous_owned_path(item, previous)
            state_by_id[item.identifier] = self._note_state(item.note)
            published_paths.append(item.logical_path)
        self._checkpoint(cancellation)
        self.stage_hook("before_state_commit", None)
        exported_at = datetime.now(timezone.utc)
        state = ExportState(
            vault_name=vault_name,
            managed_directory=self.policy.managed_root.relative_to(self.policy.vault_root).as_posix(),
            exported_at=exported_at,
            corpus_fingerprint=plan.corpus_fingerprint,
            notes=tuple(sorted(state_by_id.values(), key=lambda item: item.identifier)),
        )
        self.state_store.save(state)
        return ExportResult(
            plan.corpus_fingerprint,
            exported_at,
            dict(actual_counts),
            tuple(published_paths),
            tuple(conflicts),
            tuple(skipped),
        )

    def cleanup_temporary_files(self) -> tuple[str, ...]:
        if not self.policy.managed_root.is_dir():
            return ()
        removed: list[str] = []
        for path in self.policy.managed_root.rglob(".se-kb-*.tmp"):
            if not path.is_file() or path.is_symlink():
                continue
            resolved = path.resolve(strict=True)
            root = self.policy.managed_root.resolve(strict=True)
            if root not in resolved.parents:
                continue
            path.unlink()
            removed.append(path.relative_to(root).as_posix())
        return tuple(sorted(removed))

    def _write_temporary(self, destination: Path, payload: bytes) -> Path:
        descriptor, name = tempfile.mkstemp(
            prefix=".se-kb-",
            suffix=".tmp",
            dir=destination.parent,
        )
        temporary = Path(name)
        try:
            with os.fdopen(descriptor, "wb") as stream:
                stream.write(payload)
                stream.flush()
                os.fsync(stream.fileno())
            if hashlib.sha256(temporary.read_bytes()).hexdigest() != hashlib.sha256(payload).hexdigest():
                raise OSError("temporary note hash verification failed")
            return temporary
        except BaseException:
            temporary.unlink(missing_ok=True)
            raise

    def _remove_previous_owned_path(self, item: PlannedNote, previous: ExportState | None) -> None:
        if previous is None or item.previous_path is None:
            return
        old_state = next((entry for entry in previous.notes if entry.identifier == item.identifier), None)
        if old_state is None:
            return
        old_path = self.policy.destination(item.previous_path)
        if old_path.exists() and hash_file(old_path) == old_state.published_hash:
            old_path.unlink()

    @classmethod
    def _checkpoint(cls, cancellation: Cancellation | None) -> None:
        if cancellation is not None:
            cancellation.checkpoint()

    def _lock_for_root(self) -> threading.Lock:
        key = os.path.normcase(str(self.policy.managed_root.resolve()))
        with self._registry_guard:
            return self._locks.setdefault(key, threading.Lock())

    @staticmethod
    def _note_state(note) -> ExportedNoteState:
        return ExportedNoteState(
            note.identity.identifier,
            note.logical_path,
            note.source_hash,
            note.content_hash,
            note.identity.title,
            note.aliases,
        )
