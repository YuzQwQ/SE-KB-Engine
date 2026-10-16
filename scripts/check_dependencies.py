#!/usr/bin/env python
"""Verify that uv.lock and generated requirements files match pyproject.toml."""

from __future__ import annotations

import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
EXPORTS = {
    "requirements.txt": ("--all-extras",),
    "requirements-prod.txt": ("--extra", "api"),
}


def normalized_bytes(path: Path) -> bytes:
    return path.read_bytes().replace(b"\r\n", b"\n")


def uv_command(*args: str) -> list[str]:
    uv = shutil.which("uv")
    if not uv:
        raise RuntimeError("uv executable not found; install uv to validate dependencies")
    return [uv, *args]


def run(command: list[str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        command,
        cwd=PROJECT_ROOT,
        capture_output=True,
        encoding="utf-8",
        errors="replace",
        timeout=120,
    )


def main() -> int:
    lock_check = run(uv_command("lock", "--check"))
    if lock_check.returncode:
        print("uv.lock does not match pyproject.toml", file=sys.stderr)
        print(lock_check.stderr.strip(), file=sys.stderr)
        return 1

    with tempfile.TemporaryDirectory(prefix="se-kb-deps-") as temp_dir:
        temp_root = Path(temp_dir)
        for output_name, selection in EXPORTS.items():
            generated = temp_root / output_name
            command = uv_command(
                "export",
                "--locked",
                "--no-dev",
                *selection,
                "--no-emit-project",
                "--no-header",
                "--quiet",
                "--output-file",
                str(generated),
            )
            result = run(command)
            if result.returncode:
                print(f"failed to regenerate {output_name}", file=sys.stderr)
                print(result.stderr.strip(), file=sys.stderr)
                return 1
            committed = PROJECT_ROOT / output_name
            if not committed.exists() or normalized_bytes(committed) != normalized_bytes(generated):
                display_command = command[:-1] + [output_name]
                print(
                    f"{output_name} is stale; regenerate it with:\n  "
                    + " ".join(display_command),
                    file=sys.stderr,
                )
                return 1

    print("dependency lock and generated requirements: consistent")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
