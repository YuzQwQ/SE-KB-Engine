from __future__ import annotations

import argparse
import json
import re
import subprocess
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
PATTERNS = {
    "basic_config": re.compile(r"logging\.basicConfig"),
    "print": re.compile(r"\bprint\s*\("),
    "logger": re.compile(r"\b(?:logger|logging)\.(?:debug|info|warning|error|exception|critical)\s*\("),
    "sensitive_payload": re.compile(r"(?i)(authorization|api[_-]?key|password|secret|token|response\.text|content)"),
    "health_signal": re.compile(r"(?i)(health|liveness|readiness|ready|degraded)"),
    "metric_source": re.compile(r"(?i)(metric|duration|latency|counter|tokens_used|queue_depth)"),
}
EXCLUDED = {
    ".git", ".mypy_cache", ".pytest_cache", ".ruff_cache", ".tmp", ".venv",
    "archive", "data", "node_modules", "se_kb", "venv",
}


def inventory(root: Path) -> dict[str, object]:
    matches: dict[str, list[dict[str, object]]] = {name: [] for name in PATTERNS}
    tracked = subprocess.run(
        ["git", "ls-files", "--cached", "--others", "--exclude-standard", "--", "*.py"],
        cwd=root,
        check=True,
        capture_output=True,
        text=True,
        timeout=10,
    )
    paths = [root / line for line in tracked.stdout.splitlines() if line]
    for path in sorted(paths):
        if EXCLUDED.intersection(path.relative_to(root).parts):
            continue
        try:
            lines = path.read_text(encoding="utf-8").splitlines()
        except (OSError, UnicodeError):
            continue
        for line_number, line in enumerate(lines, 1):
            for name, pattern in PATTERNS.items():
                if pattern.search(line):
                    matches[name].append(
                        {"path": path.relative_to(root).as_posix(), "line": line_number}
                    )
    return {
        "root": str(root.resolve()),
        "categories": matches,
        "counts": {name: len(items) for name, items in matches.items()},
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Read-only logging and metric source inventory")
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    payload = json.dumps(inventory(PROJECT_ROOT), ensure_ascii=False, indent=2)
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(payload + "\n", encoding="utf-8")
    print(payload)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
