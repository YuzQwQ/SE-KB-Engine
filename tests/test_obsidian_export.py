from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest

from se_kb_app.obsidian.models import ExportAction, NoteIdentity, ProjectedNote
from se_kb_app.obsidian.paths import VaultPathPolicy
from se_kb_app.obsidian.planning import ExportPlanner, corpus_fingerprint
from se_kb_app.obsidian.projection import KnowledgeProjector
from se_kb_app.obsidian.publishing import VaultBusyError, VaultPublisher
from se_kb_app.obsidian.source import KnowledgeRecord
from se_kb_app.obsidian.state import ExportState, ExportedNoteState
from se_kb_app.obsidian.state_store import ExportStateStore
from se_kb_app.settings import AppSettings


def _policy(tmp_path: Path) -> VaultPathPolicy:
    vault = tmp_path / "vault"
    vault.mkdir(exist_ok=True)
    settings = AppSettings.from_sources(
        environ={},
        overrides={"project_root": tmp_path, "obsidian_vault_root": vault},
    )
    return VaultPathPolicy.from_settings(settings.obsidian)


def _note(identifier: str = "note_a", title: str = "A", body: str = "Body") -> ProjectedNote:
    logical_path = f"Knowledge/concept/{title}--{identifier[-1]}.md"
    markdown = f"---\nse_kb_id: \"{identifier}\"\n---\n# {title}\n\n{body}\n"
    digest = hashlib.sha256(markdown.encode("utf-8")).hexdigest()
    return ProjectedNote(
        NoteIdentity(identifier, title, "concept"),
        logical_path,
        source_id="doc_source",
        source_url="https://example.com",
        source_hash=hashlib.sha256((identifier + body).encode()).hexdigest(),
        content_hash=digest,
        markdown=markdown,
    )


def _state(note: ProjectedNote, *, path: str | None = None, published_hash: str | None = None) -> ExportState:
    return ExportState(
        "Vault",
        "SE-KB",
        __import__("datetime").datetime.fromisoformat("2026-09-18T10:00:00+00:00"),
        "f" * 64,
        (
            ExportedNoteState(
                note.identity.identifier,
                path or note.logical_path,
                note.source_hash,
                published_hash or note.content_hash,
                note.identity.title,
            ),
        ),
    )


def _write_note(policy: VaultPathPolicy, note: ProjectedNote, *, path: str | None = None, content: str | None = None):
    destination = policy.destination(path or note.logical_path)
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_bytes((content or note.markdown).encode("utf-8"))
    return destination


@pytest.mark.unit
def test_corpus_fingerprint_is_stable_and_configuration_sensitive():
    notes = (_note("note_a", "A"), _note("note_b", "B"))
    first = corpus_fingerprint(notes, {"semantic": True})
    assert first == corpus_fingerprint(reversed(notes), {"semantic": True})
    assert first != corpus_fingerprint(notes, {"semantic": False})


@pytest.mark.integration
def test_planner_classifies_create_unchanged_update_rename_conflict_and_stale(tmp_path: Path):
    policy = _policy(tmp_path)
    planner = ExportPlanner(policy)
    original = _note("note_a", "A", "old")

    assert planner.plan((original,), None).actions[0].action is ExportAction.CREATE
    _write_note(policy, original)
    previous = _state(original)
    assert planner.plan((original,), previous).actions[0].action is ExportAction.UNCHANGED

    updated = _note("note_a", "A", "new")
    assert planner.plan((updated,), previous).actions[0].action is ExportAction.UPDATE

    renamed = _note("note_a", "Renamed", "new")
    assert planner.plan((renamed,), previous).actions[0].action is ExportAction.RENAME

    _write_note(policy, original, content="user edit")
    conflict = planner.plan((updated,), previous).actions[0]
    assert (conflict.action, conflict.reason) == (ExportAction.CONFLICT, "managed_note_modified")

    stale = planner.plan((), previous).actions[0]
    assert (stale.action, stale.reason) == (ExportAction.STALE, "source_not_selected")
    assert policy.destination(original.logical_path).read_text(encoding="utf-8") == "user edit"


@pytest.mark.security
def test_planner_preserves_unknown_destination_and_bounds_preview(tmp_path: Path):
    policy = _policy(tmp_path)
    notes = tuple(_note(f"note_{index}", f"N{index}") for index in range(4))
    unknown = _write_note(policy, notes[0], content="unowned")
    plan = ExportPlanner(policy).plan(notes, None, offset=1, limit=2)
    assert plan.total_actions == 4
    assert len(plan.actions) == 2
    assert plan.partial is True
    assert plan.counts == {"conflict": 1, "create": 3}
    assert unknown.read_text(encoding="utf-8") == "unowned"


@pytest.mark.unit
def test_state_store_accepts_current_and_fails_read_only_for_invalid_or_newer(tmp_path: Path):
    policy = _policy(tmp_path)
    store = ExportStateStore(policy)
    note = _note()
    store.save(_state(note))
    loaded = store.load()
    assert loaded.state is not None and loaded.read_only is False

    value = json.loads(store.path.read_text(encoding="utf-8"))
    value["schema_version"] = "2.0"
    store.path.write_text(json.dumps(value), encoding="utf-8")
    newer = store.load()
    assert newer.state is None and newer.read_only is True
    assert newer.diagnostic == "export_state_newer_version"

    store.path.write_text('{"schema_version":', encoding="utf-8")
    corrupt = store.load()
    assert corrupt.state is None and corrupt.diagnostic == "export_state_corrupt"


@pytest.mark.integration
def test_publisher_writes_verified_notes_commits_state_last_and_repeats_unchanged(tmp_path: Path):
    policy = _policy(tmp_path)
    store = ExportStateStore(policy)
    planner = ExportPlanner(policy)
    publisher = VaultPublisher(policy, store)
    note = _note()
    plan = planner.plan((note,), None)
    result = publisher.publish(plan, vault_name="Vault")
    destination = policy.destination(note.logical_path)
    assert destination.read_text(encoding="utf-8") == note.markdown
    assert result.counts == {"create": 1}
    loaded = store.load().state
    assert loaded is not None and loaded.notes[0].published_hash == note.content_hash

    unchanged = planner.plan((note,), loaded)
    before = destination.stat().st_mtime_ns
    second = publisher.publish(unchanged, vault_name="Vault", previous=loaded)
    assert second.counts == {"unchanged": 1}
    assert destination.stat().st_mtime_ns == before


@pytest.mark.integration
def test_publisher_renames_only_an_owned_unchanged_previous_note(tmp_path: Path):
    policy = _policy(tmp_path)
    store = ExportStateStore(policy)
    planner = ExportPlanner(policy)
    publisher = VaultPublisher(policy, store)
    original = _note("note_a", "A", "old")
    publisher.publish(planner.plan((original,), None), vault_name="Vault")
    previous = store.load().state
    assert previous is not None
    renamed = _note("note_a", "Renamed", "new")
    plan = planner.plan((renamed,), previous)
    assert plan.actions[0].action is ExportAction.RENAME
    publisher.publish(plan, vault_name="Vault", previous=previous)
    assert not policy.destination(original.logical_path).exists()
    assert policy.destination(renamed.logical_path).is_file()


@pytest.mark.integration
def test_failure_and_cancellation_do_not_commit_success_state_or_touch_unowned_files(tmp_path: Path):
    policy = _policy(tmp_path)
    store = ExportStateStore(policy)
    note = _note()
    unknown = policy.managed_root / "user.txt"
    policy.managed_root.mkdir(parents=True)
    unknown.write_text("preserve", encoding="utf-8")

    def fail(stage, _item):
        if stage == "before_state_commit":
            raise OSError("injected")

    with pytest.raises(OSError, match="injected"):
        VaultPublisher(policy, store, stage_hook=fail).publish(
            ExportPlanner(policy).plan((note,), None),
            vault_name="Vault",
        )
    assert store.load().state is None
    assert unknown.read_text(encoding="utf-8") == "preserve"

    class Cancelled:
        def __init__(self):
            self.calls = 0

        @property
        def cancelled(self):
            return self.calls > 0

        def checkpoint(self):
            self.calls += 1
            raise RuntimeError("cancelled")

    destination = policy.destination(note.logical_path)
    destination.unlink(missing_ok=True)
    with pytest.raises(RuntimeError, match="cancelled"):
        VaultPublisher(policy, store).publish(
            ExportPlanner(policy).plan((note,), None),
            vault_name="Vault",
            cancellation=Cancelled(),
        )
    assert not destination.exists()
    assert store.load().state is None
    assert unknown.read_text(encoding="utf-8") == "preserve"


@pytest.mark.integration
def test_publisher_rejects_concurrent_writer_and_cleans_only_owned_temporaries(tmp_path: Path):
    policy = _policy(tmp_path)
    store = ExportStateStore(policy)
    publisher = VaultPublisher(policy, store)
    policy.managed_root.mkdir(parents=True)
    owned = policy.managed_root / ".se-kb-abandoned.tmp"
    unknown = policy.managed_root / "other.tmp"
    owned.write_text("temporary", encoding="utf-8")
    unknown.write_text("keep", encoding="utf-8")
    assert publisher.cleanup_temporary_files() == (".se-kb-abandoned.tmp",)
    assert unknown.read_text(encoding="utf-8") == "keep"

    lock = publisher._lock_for_root()
    lock.acquire()
    try:
        with pytest.raises(VaultBusyError):
            publisher.publish(ExportPlanner(policy).plan((_note(),), None), vault_name="Vault")
    finally:
        lock.release()


@pytest.mark.integration
@pytest.mark.parametrize("failure_mode", ["render", "before_write", "replace"])
def test_fault_injection_never_commits_state_or_changes_unowned_file(tmp_path: Path, failure_mode: str):
    policy = _policy(tmp_path)
    store = ExportStateStore(policy)
    unowned = policy.managed_root / "keep.md"
    policy.managed_root.mkdir(parents=True)
    unowned.write_bytes(b"keep")

    if failure_mode == "render":
        class FailingRenderer:
            def render(self, *args, **kwargs):
                raise RuntimeError("render failure")

        record = KnowledgeRecord(
            NoteIdentity("note_a", "A", "concept"),
            "doc",
            "https://example.com",
            "a" * 64,
            "body",
            "concept",
        )
        with pytest.raises(RuntimeError, match="render failure"):
            KnowledgeProjector(renderer=FailingRenderer()).project((record,))  # type: ignore[arg-type]
    else:
        def hook(stage, _item):
            if failure_mode == "before_write" and stage == "before_write":
                raise OSError("temporary write failure")

        def replace(_source, _destination):
            raise OSError("replacement failure")

        publisher = VaultPublisher(
            policy,
            store,
            stage_hook=hook,
            replace=replace if failure_mode == "replace" else __import__("os").replace,
        )
        with pytest.raises(OSError):
            publisher.publish(ExportPlanner(policy).plan((_note(),), None), vault_name="Vault")
    assert store.load().state is None
    assert unowned.read_bytes() == b"keep"
