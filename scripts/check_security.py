#!/usr/bin/env python
"""Deterministic offline secret and service-boundary static checks."""

from __future__ import annotations

import re
import sys
from dataclasses import dataclass
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
SOURCE_ROOTS = ("api", "web", "service_boundary", "utils", "server.py")
SECRET_PATTERNS = {
    "private key": re.compile(r"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----"),
    "OpenAI-style token": re.compile(r"\bsk-[A-Za-z0-9_-]{20,}\b"),
    "AWS access key": re.compile(r"\bAKIA[0-9A-Z]{16}\b"),
}
UNSAFE_PATTERNS = {
    "Flask debug enabled": re.compile(r"\bdebug\s*=\s*True\b"),
    "unrestricted Flask CORS": re.compile(r"\bCORS\(app\)"),
    "client-visible exception": re.compile(
        r"(?:jsonify|return)[^\n]{0,160}str\((?:e|err|error|exc|exception)\)"
    ),
}


@dataclass(frozen=True)
class Finding:
    path: Path
    line: int
    rule: str


def source_files(root: Path) -> list[Path]:
    files: list[Path] = []
    for item in SOURCE_ROOTS:
        target = root / item
        if target.is_file():
            files.append(target)
        elif target.is_dir():
            files.extend(target.rglob("*.py"))
            files.extend(target.rglob("*.js"))
    return sorted(set(files))


def scan(root: Path = PROJECT_ROOT) -> list[Finding]:
    findings: list[Finding] = []
    for path in source_files(root):
        text = path.read_text(encoding="utf-8")
        for line_number, line in enumerate(text.splitlines(), 1):
            for rule, pattern in {**SECRET_PATTERNS, **UNSAFE_PATTERNS}.items():
                if pattern.search(line):
                    findings.append(Finding(path.relative_to(root), line_number, rule))
    return findings


def main() -> int:
    findings = scan()
    if findings:
        print("offline security scan failed:")
        for finding in findings:
            print(f"  {finding.path}:{finding.line}: {finding.rule}")
        return 1
    print(f"offline security scan passed ({len(source_files(PROJECT_ROOT))} source files)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
