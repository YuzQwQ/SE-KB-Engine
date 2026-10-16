from __future__ import annotations

import argparse
import json
import tomllib
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parent.parent


def generate(lock_path: Path) -> dict[str, Any]:
    lock = tomllib.loads(lock_path.read_text(encoding="utf-8"))
    components = [
        {
            "type": "library",
            "name": package["name"],
            "version": package["version"],
            "purl": f"pkg:pypi/{package['name']}@{package['version']}",
        }
        for package in lock.get("package", [])
        if package.get("name") and package.get("version")
    ]
    return {
        "bomFormat": "CycloneDX",
        "specVersion": "1.5",
        "version": 1,
        "metadata": {"component": {"type": "application", "name": "mcp-client", "version": "0.1.0"}},
        "components": sorted(components, key=lambda item: (item["name"], item["version"])),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate an offline SBOM from the authoritative uv lock")
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    payload = generate(PROJECT_ROOT / "uv.lock")
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"wrote {len(payload['components'])} SBOM components")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
