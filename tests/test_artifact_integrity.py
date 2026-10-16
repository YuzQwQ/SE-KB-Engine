from __future__ import annotations

from pathlib import Path

import pytest

from se_kb_app.artifacts.reader import ArtifactReader
from se_kb_app.artifacts.scanner import IntegrityScanner


FIXTURES = Path(__file__).parent / "fixtures" / "artifacts"


@pytest.mark.unit
def test_dual_reader_supports_current_and_observed_legacy_without_writes():
    current = ArtifactReader().read(FIXTURES / "current")
    legacy = ArtifactReader().read(FIXTURES / "legacy")
    assert current.format_version == "1.0" and current.manifest is not None
    assert legacy.format_version == "legacy-0" and legacy.manifest is None
    assert legacy.source_url == "https://example.com/legacy"


@pytest.mark.integration
def test_scanner_continues_after_corruption_and_reports_relationships_and_duplicates():
    report = IntegrityScanner().scan(FIXTURES)
    kinds = {issue.kind for issue in report.issues}
    assert {"corrupt_json", "missing_file", "orphan_candidate"}.issubset(kinds)
    assert report.versions == {"1.0": 4, "legacy-0": 2}
    assert any(len(group) == 2 for group in report.duplicate_groups)
    assert "Issues:" in report.to_text()
    assert report.to_dict()["valid"] is False
