#!/usr/bin/env python
"""Run the deterministic offline quality gate and preserve each tool's output."""

from __future__ import annotations

import os
import shutil
import subprocess
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent


def commands() -> list[tuple[str, list[str]]]:
    python = sys.executable
    uv = shutil.which("uv")
    if not uv:
        raise RuntimeError("uv executable not found; install uv before running the quality gate")
    return [
        ("encoding and compile", [python, "scripts/check_encodings.py"]),
        ("dependency drift", [python, "scripts/check_dependencies.py"]),
        ("offline security scan", [python, "scripts/check_security.py"]),
        ("delivery configuration", [python, "scripts/check_delivery.py"]),
        ("documentation links", [python, "scripts/check_docs.py"]),
        ("Ruff", [python, "-m", "ruff", "check", "."]),
        ("mypy", [python, "-m", "mypy", ".", "--no-error-summary"]),
        (
            "offline retrieval benchmark",
            [python, "scripts/run_retrieval_benchmark.py", "--candidate", "hybrid", "--quiet"],
        ),
        ("offline pytest", [python, "-m", "pytest", "-q"]),
    ]


def main() -> int:
    environment = {
        **os.environ,
        "PYTHONIOENCODING": "utf-8",
        "PYTHONDONTWRITEBYTECODE": "1",
        "SE_KB_SKIP_DOTENV": "1",
    }
    failures: list[str] = []
    for name, command in commands():
        print(f"\n== {name} ==", flush=True)
        result = subprocess.run(command, cwd=PROJECT_ROOT, env=environment, timeout=300)
        if result.returncode:
            failures.append(name)
    if failures:
        print("\nquality gate failed: " + ", ".join(failures), file=sys.stderr)
        return 1
    print("\nquality gate passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
