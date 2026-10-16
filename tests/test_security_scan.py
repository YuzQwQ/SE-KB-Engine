from __future__ import annotations

from pathlib import Path

import pytest

from scripts.check_security import scan


@pytest.mark.security
def test_security_scan_detects_secret_and_unsafe_boundary_patterns(tmp_path: Path):
    api = tmp_path / "api"
    api.mkdir()
    (api / "bad.py").write_text(
        'TOKEN = "sk-abcdefghijklmnopqrstuvwxyz"\napp.run(debug=True)\nCORS(app)\n',
        encoding="utf-8",
    )
    rules = {finding.rule for finding in scan(tmp_path)}
    assert rules == {"OpenAI-style token", "Flask debug enabled", "unrestricted Flask CORS"}


@pytest.mark.security
def test_repository_security_scan_is_clean():
    assert scan() == []
