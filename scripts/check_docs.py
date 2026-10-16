from __future__ import annotations

import argparse
import os
import re
import subprocess
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
LINK = re.compile(r"(?<!!)\[[^]]+\]\(([^)]+)\)")
IGNORED_PREFIXES = ("http://", "https://", "mailto:", "#", "codex:")


def broken_links(root: Path) -> list[str]:
    failures: list[str] = []
    files = [root / "README.md", *sorted((root / "docs").glob("*.md"))]
    for document in files:
        if not document.is_file():
            continue
        for target in LINK.findall(document.read_text(encoding="utf-8")):
            clean = target.strip().strip("<>").split("#", 1)[0]
            if not clean or clean.startswith(IGNORED_PREFIXES):
                continue
            if not (document.parent / clean).resolve().exists():
                failures.append(f"{document.relative_to(root)} -> {target}")
    return failures


def run_smoke(root: Path) -> list[str]:
    commands = (
        [sys.executable, "scripts/check_encodings.py"],
        [sys.executable, "-m", "pytest", "tests/test_smoke.py", "-q"],
        [sys.executable, "scripts/run_retrieval_benchmark.py", "--candidate", "hybrid", "--quiet"],
    )
    failures = []
    environment = {**os.environ, "PYTHONIOENCODING": "utf-8", "SE_KB_SKIP_DOTENV": "1"}
    for command in commands:
        result = subprocess.run(command, cwd=root, timeout=120, env=environment)
        if result.returncode:
            failures.append(" ".join(command[1:]))
    return failures


def main() -> int:
    parser = argparse.ArgumentParser(description="Verify local documentation links and offline smoke commands")
    parser.add_argument("--execute-smoke", action="store_true")
    args = parser.parse_args()
    failures = broken_links(PROJECT_ROOT)
    if args.execute_smoke:
        failures.extend(f"smoke: {item}" for item in run_smoke(PROJECT_ROOT))
    if failures:
        print("documentation verification failed:", file=sys.stderr)
        for failure in failures:
            print(f"- {failure}", file=sys.stderr)
        return 1
    print("documentation links and offline smoke commands are valid")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
