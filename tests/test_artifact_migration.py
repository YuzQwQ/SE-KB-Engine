from __future__ import annotations

import shutil
from datetime import datetime, timezone
from pathlib import Path

import pytest

from se_kb_app.artifacts.migration import ArtifactMigrator
from se_kb_app.artifacts.scanner import IntegrityScanner


FIXTURE = Path(__file__).parent / "fixtures" / "artifacts" / "legacy"


def snapshot(root: Path) -> dict[str, bytes]:
    return {path.relative_to(root).as_posix(): path.read_bytes() for path in root.rglob("*") if path.is_file()}


@pytest.mark.integration
def test_dry_run_reports_plan_and_writes_nothing(tmp_path: Path):
    source = tmp_path / "source"
    target = tmp_path / "target"
    shutil.copytree(FIXTURE, source / "one")
    before = snapshot(source)
    report = ArtifactMigrator().migrate(source, target, dry_run=True)
    assert [item.status for item in report.items] == ["planned"]
    assert report.backup_mapping
    assert not target.exists()
    assert snapshot(source) == before


@pytest.mark.integration
def test_copy_migration_validates_target_and_preserves_source(tmp_path: Path):
    source = tmp_path / "source"
    target = tmp_path / "target"
    shutil.copytree(FIXTURE, source / "one")
    before = snapshot(source)
    now = datetime(2026, 9, 15, tzinfo=timezone.utc)
    report = ArtifactMigrator(clock=lambda: now).migrate(source, target, dry_run=False)
    assert [item.status for item in report.items] == ["migrated"]
    assert report.post_validation_valid is True
    assert IntegrityScanner().scan(target).valid is True
    assert snapshot(source) == before
    assert "source remains authoritative" in report.rollback_instructions


@pytest.mark.unit
def test_preflight_rejects_in_place_or_nested_migration(tmp_path: Path):
    source = tmp_path / "source"
    shutil.copytree(FIXTURE, source / "one")
    report = ArtifactMigrator().migrate(source, source / "new", dry_run=True)
    assert report.preflight_errors == ("target must not be the source or nested inside it",)
    assert all(item.status == "blocked" for item in report.items)
