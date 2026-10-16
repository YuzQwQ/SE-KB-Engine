from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from se_kb_app.artifacts.migration import ArtifactMigrator


def main() -> int:
    parser = argparse.ArgumentParser(description="Copy-only versioned artifact migration")
    parser.add_argument("source", type=Path)
    parser.add_argument("target", type=Path)
    parser.add_argument(
        "--execute",
        action="store_true",
        help="Write to the new target. Omit for the safe read-only dry run.",
    )
    args = parser.parse_args()
    report = ArtifactMigrator().migrate(args.source, args.target, dry_run=not args.execute)
    print(json.dumps(report.to_dict(), ensure_ascii=False, indent=2))
    return 1 if report.preflight_errors else 0


if __name__ == "__main__":
    raise SystemExit(main())
