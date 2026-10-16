from __future__ import annotations

import sys

import pytest

from scripts.quality import commands


@pytest.mark.unit
def test_quality_command_contains_required_offline_checks():
    configured = commands()
    names = [name for name, _ in configured]
    assert names == [
        "encoding and compile",
        "dependency drift",
        "offline security scan",
        "delivery configuration",
        "documentation links",
        "Ruff",
        "mypy",
        "offline retrieval benchmark",
        "offline pytest",
    ]
    assert all(command[0] == sys.executable for _, command in configured)
