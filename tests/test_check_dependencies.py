from __future__ import annotations

from pathlib import Path

import pytest

from scripts.check_dependencies import normalized_bytes, uv_command


@pytest.mark.unit
def test_normalized_bytes_ignores_checkout_line_endings(tmp_path: Path):
    left = tmp_path / "left.txt"
    right = tmp_path / "right.txt"
    left.write_bytes(b"one\r\ntwo\r\n")
    right.write_bytes(b"one\ntwo\n")
    assert normalized_bytes(left) == normalized_bytes(right)


@pytest.mark.unit
def test_uv_command_has_requested_arguments():
    command = uv_command("lock", "--check")
    assert Path(command[0]).name.lower().startswith("uv")
    assert command[-2:] == ["lock", "--check"]


@pytest.mark.integration
def test_dependency_exports_are_current():
    from scripts.check_dependencies import main

    assert main() == 0
