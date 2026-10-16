from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest

from scripts.check_encodings import check_compile, check_utf8, iter_target_files


@pytest.mark.unit
def test_check_utf8_accepts_plain_utf8(tmp_path: Path):
    target = tmp_path / "ok.md"
    target.write_text("中文 UTF-8", encoding="utf-8")
    assert check_utf8(target) is None


@pytest.mark.unit
@pytest.mark.parametrize(
    ("payload", "message"),
    [
        (b"\xef\xbb\xbftext", "UTF-8 BOM"),
        (b"\xff\xfet\x00e\x00x\x00t\x00", "UTF-16 BOM"),
        (b"\x80\x81", "UTF-8 解码失败"),
    ],
)
def test_check_utf8_reports_noncanonical_bytes(tmp_path: Path, payload: bytes, message: str):
    target = tmp_path / "bad.txt"
    target.write_bytes(payload)
    before = target.read_bytes()
    assert message in (check_utf8(target) or "")
    assert target.read_bytes() == before


@pytest.mark.unit
def test_compile_reports_syntax_without_writing_pyc(tmp_path: Path):
    target = tmp_path / "broken.py"
    target.write_text("def broken(:\n", encoding="utf-8")
    assert "编译失败" in (check_compile(target) or "")
    assert list(tmp_path.rglob("*.pyc")) == []


@pytest.mark.unit
def test_scan_includes_tests_but_excludes_runtime_directories(tmp_path: Path):
    included = tmp_path / "tests" / "test_example.py"
    excluded = tmp_path / ".venv" / "library.py"
    enhanced = tmp_path / "venv_enhanced" / "third_party.py"
    temporary = tmp_path / ".tmp" / "probe.py"
    included.parent.mkdir()
    excluded.parent.mkdir()
    enhanced.parent.mkdir()
    temporary.parent.mkdir()
    included.write_text("assert True\n", encoding="utf-8")
    excluded.write_text("not valid python", encoding="utf-8")
    enhanced.write_text("not valid python", encoding="utf-8")
    temporary.write_text("not valid python", encoding="utf-8")
    assert included in iter_target_files(tmp_path)
    assert excluded not in iter_target_files(tmp_path)
    assert enhanced not in iter_target_files(tmp_path)
    assert temporary not in iter_target_files(tmp_path)


@pytest.mark.integration
def test_cli_fails_read_only_for_invalid_utf8(tmp_path: Path):
    target = tmp_path / "bad.txt"
    target.write_bytes(b"\x80")
    script = Path(__file__).resolve().parents[1] / "scripts" / "check_encodings.py"
    before = target.read_bytes()
    result = subprocess.run(
        [sys.executable, str(script), "--root", str(tmp_path)],
        capture_output=True,
        encoding="utf-8",
        errors="replace",
        timeout=30,
    )
    assert result.returncode == 1
    assert "bad.txt" in result.stdout
    assert target.read_bytes() == before
