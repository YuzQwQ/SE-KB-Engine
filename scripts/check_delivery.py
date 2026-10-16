from __future__ import annotations

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent


def checks(root: Path) -> list[str]:
    failures: list[str] = []
    dockerfile = (root / "deploy" / "Dockerfile").read_text(encoding="utf-8")
    compose = (root / "deploy" / "docker-compose.yml").read_text(encoding="utf-8")
    nginx = (root / "deploy" / "nginx.conf").read_text(encoding="utf-8")
    required_docker = (" AS builder", " AS runtime", "--require-hashes", "USER 10001:10001", "HEALTHCHECK", "STOPSIGNAL SIGTERM")
    for token in required_docker:
        if token not in dockerfile:
            failures.append(f"Dockerfile missing {token}")
    for forbidden in ("COPY .env", "../.env:/app/.env", "latest"):
        if forbidden in dockerfile or forbidden in compose:
            failures.append(f"container configuration contains forbidden token {forbidden}")
    for token in ("read_only: true", "cap_drop: [ALL]", "no-new-privileges", "pids_limit", "max-size"):
        if token not in compose:
            failures.append(f"Compose missing {token}")
    for token in ("client_max_body_size", "proxy_read_timeout", "X-Content-Type-Options", "X-Forwarded-For $remote_addr"):
        if token not in nginx:
            failures.append(f"Nginx missing {token}")
    for workflow in ("ci.yml", "external-suites.yml", "supply-chain.yml"):
        if not (root / ".github" / "workflows" / workflow).is_file():
            failures.append(f"missing workflow {workflow}")
    container_exercise = root / "scripts" / "exercise_container_release.py"
    if not container_exercise.is_file():
        failures.append("missing container upgrade/rollback exercise")
    else:
        exercise = container_exercise.read_text(encoding="utf-8")
        for token in ("--project-name", '"down"', '"--volumes"', "exercise-old", "exercise-new", "read_only_root"):
            if token not in exercise:
                failures.append(f"container exercise missing {token}")
    external_suite = (root / ".github" / "workflows" / "external-suites.yml").read_text(encoding="utf-8")
    if "scripts/exercise_container_release.py" not in external_suite:
        failures.append("external container suite does not run release exercise")
    return failures


def main() -> int:
    failures = checks(PROJECT_ROOT)
    if failures:
        print("delivery checks failed: " + "; ".join(failures), file=sys.stderr)
        return 1
    print("delivery configuration checks passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
