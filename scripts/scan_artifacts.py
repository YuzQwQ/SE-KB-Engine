from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from se_kb_app.artifacts.scanner import IntegrityScanner


def main() -> int:
    parser = argparse.ArgumentParser(description="Read-only artifact integrity scanner")
    parser.add_argument("root", type=Path)
    parser.add_argument("--json", action="store_true", dest="as_json")
    args = parser.parse_args()
    report = IntegrityScanner().scan(args.root)
    print(json.dumps(report.to_dict(), ensure_ascii=False, indent=2) if args.as_json else report.to_text())
    return 0 if report.valid else 1


if __name__ == "__main__":
    raise SystemExit(main())
